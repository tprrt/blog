==========================================================================
One Confession, One Alibi: Closing Out the GBA Text Performance Hunt
==========================================================================

:date: 2026-11-04 18:40
:tags: gba, performance, optimization, embedded, retro, gamedev, debugging, c, article
:category: gamedev
:slug: one-confession-one-alibi-gba-text-performance
:authors: tperrot
:summary: The previous GBA text-rendering investigation ended with two
    suspects still unmeasured: a palette-bank lookup and a layout
    function the compiler had inlined past the point of having its own
    symbol. One of them was costing real cycles to a soft-float call
    that didn't need to happen. The other had an alibi, and proving it
    took finding the one address ten unrolled loop exits all agree on.
:lang: en
:status: published

Introduction
============

The `previous article <floored-twice-article_>`_ fixed the dominant cost in
``gba_text_render_system`` -- screen-space projection math running through
the ARM7TDMI's software float library -- and ended with two names still on
the list: ``framer_color_bank_acquire()``, and the per-line layout call
that decides how many hardware sprites a string of text needs. Neither had
been bracketed with a debugger yet. Both calls sit at the same place in the
loop, once per text line, so they were always going to get measured
together eventually.

They did not turn out the same way. One had a real soft-float tax, caught
by the same ``fabsf()``-per-comparison pattern the projection math already
had. The other turned out to be a handful of integer instructions wearing
a scary reputation -- "fully inlined, no surviving symbol" -- that had
nothing to do with how expensive it actually was.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

The confession: ``framer_color_bank_acquire()``
==================================================

GBA sprites don't get an arbitrary color; they're indexed into one of 16
hardware palette banks, and ``framer_color_bank_acquire()`` is what decides
which bank a given tint color lands in -- reuse an exact match, reuse the
least-recently-used bank if the color is close enough, or claim a free one.
It runs once per text line, right where the projection math used to live.

Reading it was unremarkable: a loop over the bank table, comparing each
bank's stored color against the incoming one.

.. code-block:: c

    static bool color_matches(const struct bank_slot *slot, const vec4 color)
    {
        const float eps = 0.004f;

        return fabsf(slot->r - color[0]) < eps &&
               fabsf(slot->g - color[1]) < eps &&
               fabsf(slot->b - color[2]) < eps;
    }

Three ``fabsf()`` calls and three subtractions, per bank, per call. The
ARM7TDMI has no FPU, so every one of those is a real soft-float library
call, not an instruction. Two breakpoints -- the function's entry and the
single epilogue every return path converges to -- bracketed it directly
against ``examples/input_tester``'s real hardware emulation: about 3300
cycles for the common case, an exact match found on the first bank
checked. Roughly a third of the entire per-entity gap the previous article
measured at 7400-17000 cycles.

The fix doesn't touch what gets written to hardware, only what the
comparison itself looks at. GBA color already has to go through
``rgb555.h``'s ``f_to_5bit()`` on its way to real ``OBJ_PALETTE`` memory --
truncating each float channel to its exact 5-bit hardware value. Doing that
truncation once, ahead of the comparison, turns three ``fabsf()`` calls
into three integer equality checks:

.. code-block:: c

    static bool color_matches(const struct bank_slot *slot, const uint8_t q5[3])
    {
        return slot->q5[0] == q5[0] && slot->q5[1] == q5[1] &&
               slot->q5[2] == q5[2];
    }

Each bank's own quantized value is computed once, when that bank's color is
actually assigned -- not recomputed on every comparison -- and the
incoming color is quantized once per call, not once per bank scanned. The
stored float color stays exactly what it was; only the matching logic
moved to integers. Same bracket, same scene, after the fix: about 1100
cycles. A third of the original, and a real one this time, not a rounding
error in a 40-hit average.

The alibi: the layout call
=============================

The layout call was the harder one to even put a breakpoint on. Under
``-O3`` plus LTO, ``framer_oam_layout_string()`` has no symbol of its own
left -- it's inlined straight into ``gba_text_render_system``, the same
fate that swallowed every other sub-function the previous article had to
work around with ``arm-none-eabi-objdump -dS``. The source itself didn't
look alarming:

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

Pure integer arithmetic, at most ten iterations (``FRAMER_OAM_MAX_SPRITES_
PER_TEXT``), no float anywhere. The honest answer could only come from
measuring it, the same rule the previous article's own two wrong "obvious"
fixes already proved the hard way.

Disassembling ``gba_text_render_system`` and reading it against the source
showed why there was no symbol to break on: the compiler had fully
unrolled the loop into ten early-exit points, one per possible iteration
count, each jumping to the code that runs once layout is done. All ten
converge on the exact same address -- one shared post-layout continuation,
regardless of which exit a given line's character count actually takes.
That address is as good as a symbol: a single breakpoint there fires
exactly once per call, no matter how many of the ten exits a real line
goes through.

A second breakpoint at the loop's own entry, and ``phase_probe.py`` against
real mGBA emulation did the rest: 40 hits, steady state. First call about
176 cycles -- a cold branch predictor, most likely -- settling to 114-128
on every call after, averaging around 119. The spread tracks exactly what
the source predicts: a label needing one more four-character sprite group
than another costs a few more cycles, nothing structural.

For scale: the per-entity projection math this whole investigation started
with cost 7400-17000 cycles per transition. ``framer_color_bank_acquire()``
cost 3300 before its fix. Layout costs 119. Summed across every line
``input_tester`` draws in a frame -- about 19 or 20 of them, at that
scene's own 76-of-96 OAM budget -- the whole layout pass costs roughly
2300-2500 cycles, against a frame that was already running 660650-684800
cycles before anything in this article touched it. Roughly a third of one
percent.

No fix follows, because there's nothing there to fix. The function looked
cheap from the source and it was.

Checking it
=============

Only one of these two findings changed any code, so only one needed the
full byte-for-byte check: connect to the emulator's GDB stub, let a few
frames settle, read the hardware's palette and sprite memory, and diff it
against the same read from the unfixed ROM. All 128 sprite entries and the
full 256-color bank came back identical -- the quantization only moved
where the comparison happens, never what the comparison decides or what
reaches the hardware palette. Two new host-side tests pin the boundary
the quantization itself introduces: two colors inside the same 5-bit
step share a bank, two colors straddling that step don't.
``games/caravan``, the heaviest real consumer of this file, cross-
compiles clean for NDS too.

The layout finding needed no such check, because nothing moved. The whole
point of measuring it was to decide whether touching it was worth the
risk at all, and the answer was no before any diff existed to verify.

What's left
=============

Both names on the previous article's list are now accounted for: one
confirmed and fixed, one confirmed and left alone. Between the projection
math rewrite and the color-bank quantization, ``input_tester`` is faster
than it was two articles ago, but neither change gets a scene running at
18 FPS anywhere near 60 Hz on its own -- that was never the claim. What
this closes is narrower and more useful: every function this
investigation named as a plausible suspect has now actually been measured,
not assumed. Whatever gets ``gba_text_render_system`` the rest of the way
there will have to be a different kind of change, not one more cycle
hiding in a function nobody's looked at yet.

.. _floored-twice-article: https://tprrt.tupi.fr/floored-twice-gba-text-soft-float.html
