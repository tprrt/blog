==========================================================================
One Confession, One Alibi: Closing Out the GBA Text Performance Hunt
==========================================================================

:date: 2026-11-04 18:40
:tags: gba, performance, optimization, embedded, retro, gamedev, debugging, c, article
:category: gamedev
:slug: one-confession-one-alibi-gba-text-performance
:authors: tperrot
:summary: The previous GBA text-rendering investigation ended with two
    suspects unmeasured: a palette-bank lookup and a layout function the
    compiler had inlined away. The first spent cycles on soft-float calls it
    did not need. The second was cheap, and measuring it meant finding the
    one address that ten unrolled loop exits share.
:lang: en
:status: published

Introduction
============

The `previous article <floored-twice-article_>`_ fixed the dominant cost in
``gba_text_render_system``, screen-space projection math running through the
ARM7TDMI's software float library, and left two functions unmeasured:
``framer_color_bank_acquire()``, and the per-line layout call that decides
how many hardware sprites a string needs. Both run once per text line at the
same place in the loop.

One had a soft-float cost. The other is a handful of integer instructions
that only looked suspicious because the compiler had inlined it out of
sight.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

The confession: ``framer_color_bank_acquire()``
==================================================

GBA sprites index into one of 16 hardware palette banks.
``framer_color_bank_acquire()`` picks the bank for a tint color: reuse an
exact match, reuse the least-recently-used bank if the color is close enough,
or claim a free one. It runs once per text line.

The matching loop compares each bank's stored color with the incoming one:

.. code-block:: c

    static bool color_matches(const struct bank_slot *slot, const vec4 color)
    {
        const float eps = 0.004f;

        return fabsf(slot->r - color[0]) < eps &&
               fabsf(slot->g - color[1]) < eps &&
               fabsf(slot->b - color[2]) < eps;
    }

That is three subtractions, three ``fabsf()`` calls and three comparisons per
bank, and on an FPU-less ARM7TDMI each is a soft-float library call. Two
breakpoints, at the function's entry and at the epilogue every return path
converges to, measured it on ``examples/input_tester`` in mGBA: about 3300
cycles in the common case, an exact match on the first bank. That is roughly
a third of the 7400-17000 cycle per-entity gap the previous article measured.

The hardware write path already converts each float channel to its 5-bit
value with ``rgb555.h``'s ``f_to_5bit()`` before it reaches ``OBJ_PALETTE``.
Doing that conversion before the comparison turns it into three integer
equality checks:

.. code-block:: c

    static bool color_matches(const struct bank_slot *slot, const uint8_t q5[3])
    {
        return slot->q5[0] == q5[0] && slot->q5[1] == q5[1] &&
               slot->q5[2] == q5[2];
    }

Each bank's quantized value is computed once, when the bank's color is
assigned, and the incoming color is quantized once per call, not once per
bank. The stored float color is unchanged. Same breakpoints, same scene:
about 1100 cycles, a third of before.

This does change the matching rule. The old test matched colors within 0.004
of each other; the new one matches colors that land in the same 5-bit step,
about 0.032 wide. Two colors 0.002 apart on either side of a step boundary no
longer share a bank, and two colors 0.02 apart inside one step now do. Since
the hardware cannot display the difference within a step, sharing a bank
there is correct, and the scenes checked below are unaffected.

The alibi: the layout call
=============================

Under ``-O3`` and LTO, ``framer_oam_layout_string()`` has no symbol left: it is
inlined into ``gba_text_render_system``, like the sub-functions the previous
article had to find with ``arm-none-eabi-objdump -dS``. The source:

.. code-block:: c

    remaining = char_count;
    offset = 0;
    i = 0;
    while (remaining > 0 && i < FRAMER_OAM_MAX_SPRITES_PER_TEXT) {
        int n = remaining < 4 ? remaining : 4;
        /* ... fill out one sprite-group descriptor ... */
        offset += n;
        remaining -= n;
        i++;
    }

Integer arithmetic, at most ten iterations
(``FRAMER_OAM_MAX_SPRITES_PER_TEXT``), no float. It looked cheap, but the
previous article's two "obvious" fixes that measured as regressions are
reason enough to measure it.

The disassembly showed the compiler had fully unrolled the loop into ten
early exits, one per possible iteration count, all jumping to the same
post-layout address. A breakpoint there fires exactly once per call, whichever
exit the line takes, so it works as well as a symbol.

With a second breakpoint at the loop entry, ``phase_probe.py`` in mGBA
recorded 40 hits in steady state. The first call took about 176 cycles, and
every later one 114-128, averaging about 119. The spread follows the source:
a label needing one more four-character sprite group costs a few more cycles.

For scale: the projection math cost 7400-17000 cycles per transition,
``framer_color_bank_acquire()`` 3300 before its fix, layout 119.
``input_tester`` draws 19 or 20 lines per frame at its 76-of-96 OAM budget, so
the whole layout pass costs roughly 2300-2500 cycles against a 660650-684800
cycle frame, about a third of one percent. There is nothing to fix.

Checking it
=============

Only the color-bank change touched code. The check is the usual byte-for-byte
comparison: connect to the emulator's GDB stub, let a few frames settle, read
palette and sprite memory, and diff against the same read from the unfixed
ROM. All 128 sprite entries and the full 256-color palette came back
identical. Two new host-side tests pin the new boundary: two colors in the
same 5-bit step share a bank, two colors straddling a step do not.
``games/caravan``, the heaviest user of this code, also cross-compiles cleanly
for NDS.

What's left
=============

Both functions are now measured: one fixed, one left alone. With the
projection rewrite and the color-bank quantization, ``input_tester`` is faster
than two articles ago, but nowhere near 60 Hz from 18 FPS. Every function the
investigation suspected has been measured, so the remaining cost needs a
different kind of change.

.. _floored-twice-article: https://tprrt.tupi.fr/floored-twice-gba-text-soft-float.html
