==========================================================================
Floored Twice: Chasing a Soft-Float Tax in GBA Text Rendering
==========================================================================

:date: 2026-10-15 22:50
:tags: gba, performance, optimization, embedded, retro, gamedev, fixed-point, c, article
:category: gamedev
:slug: floored-twice-gba-text-soft-float
:authors: tperrot
:summary: A GBA example with a lot of on-screen text ran at 18 FPS, idle,
    no input needed. The cost turned out to be screen-space projection
    math running through the ARM7TDMI's software float library once per
    text entity and once per line. Two fixes that looked obviously
    correct made it worse before the one that actually helped, and a
    debugger told the difference each time, not intuition.
:lang: en
:status: published

Introduction
============

The `earlier article on cycle-level GBA optimization <gba-performance-article_>`_
covered the software 3D rasterizer: two "obviously correct" changes that
measured as regressions once link-time optimization's own inlining
decisions got factored in. This article is the same lesson applied to a
completely different part of the renderer — the one that draws text — and
it took two more wrong turns to get there, for reasons that had nothing to
do with LTO this time.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

Two `framer-engine`_ examples with a lot of on-screen text ran far below
the 60 Hz target, both idle, nothing moving, no input needed to reproduce:
``input_tester`` (76 of a 96-slot text sprite budget active) at roughly
18 FPS, and ``wordle``, a word cloud of rotated labels, at roughly 14.5.
``phase_probe.py``, the gdbstub cycle-bracketing script this blog has used
before, had already put about 69% of a frame's cost inside one function,
``gba_text_render_system``. The question this article answers is which
part of that function, and what fixing it actually took.

Finding where the cost lives
=============================

The function processes a handful of text entities, each with one or more
lines, each line made of several hardware sprites (one GBA OAM entry per
glyph group). Three plausible places for the cost to hide: the glyph
layout math, the screen-space projection that turns a world position into
a pixel coordinate, or the OAM attribute writes themselves, once per
glyph and so the most frequent of the three.

A quick static pass with ``arm-none-eabi-objdump -dS`` ruled the OAM
writes out early — they're fully inlined integer stores, no library calls
at all. The projection math was a different story: ``cx``/``cy`` (an
entity's anchor in screen space) and ``py_base``/``px`` (where each line
starts) were float, and the ARM7TDMI has no FPU, so every subtract, add,
multiply and the two ``floorf()``/float-to-int calls on top of them go
through software float library routines.

Static inspection only tells you a call exists, not how often the
hardware actually takes it. Two breakpoints settled that: one at the
function's entry, one at the first line of the innermost per-sprite loop
body. The delta between consecutive hits of the second breakpoint is one
sprite's own cost when it stays on the same line as the sprite before it,
and the same delta plus a line's or entity's own setup when it doesn't.
In a steady frame of ``input_tester``, a same-line sprite-to-sprite step
cost about 515 cycles. A step that also crossed into a new line or a new
entity cost 7400 to 17000 — roughly fifteen times as much, for a
transition that happens far less often than every sprite does, but still
often enough across a frame to dominate. The per-entity/per-line
projection math was the cost, not the per-sprite work multiplied by a
large sprite count.

War story 1: fixed-point that rounded the wrong way
======================================================

The ARM7TDMI projection code the engine already runs for its software 3D
pipeline uses ``fix_t``, a Q12 fixed-point type — one hardware multiply
(``fix_mul``) instead of a chain of soft-float calls. Reusing it for text
looked like the obvious fix: convert the camera position, the ortho
extent, the scale and the entity's own position to ``fix_t`` and do the
whole projection in integer math.

It passed every example I ran it against, by eye. Before trusting that, I
wrote a host-side sweep test comparing the fixed-point result against the
plain float one across a grid of realistic camera/ortho/scale/position
combinations — the same discipline the `article on sprite flicker
<flicker-article_>`_ used an emulator sampler for, just on the host this
time, because the thing being checked was arithmetic, not hardware state.
16 of 192 combinations disagreed, and
every one disagreed by exactly one, in the same direction:

.. code-block:: text

    mismatch: cam=0.0 ortho=5.0 scale=28.8 pos=0.0 expected=144 actual=143
    mismatch: cam=0.0 ortho=5.0 scale=28.8 pos=2.5 expected=72  actual=71

The existing ``fix_from_float()`` helper (shared with the 3D rasterizer,
which depends on its exact behavior) truncates toward zero. Four
conversions chained together — camera, ortho extent, scale, position —
each truncate a little short, and on values that land exactly on an
integer in true float math, the accumulated shortfall is enough to floor
to one below the real answer. 144.0 pixels of text would have shifted up
by a pixel, silently, on specific camera positions. The test caught it
before a single frame of it ran on an emulator, let alone hardware.

War story 2: the float path that measured slower
====================================================

Rather than fix the rounding, I tried avoiding fixed-point arithmetic
altogether: keep everything in float, but replace ``(int)floorf(x)`` with
a hand-rolled equivalent that skips ``floorf()``'s general body.
``objdump`` showed that body at 74 instructions — handling NaN, infinity
and subnormals this call site's bounded screen-space input never
produces. A truncate-then-adjust version is exact for any finite value
and looks a lot cheaper:

.. code-block:: c

    static inline int gba_fast_floor(float x)
    {
        int i = (int)x;
        return (float)i > x ? i - 1 : i;
    }

Exact, verified the same way as the first attempt, and obviously less
code. ``cycle_probe.py`` said otherwise: the steady-state average on
``input_tester`` went from 727556 to 748028 cycles/frame, a ~2.8%
*regression*. The original ``(int)floorf(x)`` is two soft-float library
calls (``floorf`` itself, then the float-to-int conversion on its
result). The replacement is three (truncate, convert back to float to
compare, compare) — one more, and each one pays its own fixed
call/return/Thumb-interworking overhead on top of whatever its body
actually does. ``floorf()``'s large body turned out to be cheaper than
the fast version's extra dispatch. A smaller instruction count on paper
said nothing about the measured cost.

What actually worked
=====================

Fixed-point, with the rounding fixed rather than abandoned: a local
``gba_fix_from_float_rounded()`` (not a change to the shared, truncating
``fix_from_float()``, since the 3D rasterizer depends on that one's exact
behavior) that rounds to nearest instead of truncating. The sweep test
that caught the first attempt now passes, including the exact-integer
cases it failed before and the narrowest possible margin around an
integer boundary a float can represent.

The second change mattered as much as the rounding fix: every
frame-constant term — camera position, ortho extent, the screen-space
scale — gets converted to ``fix_t`` once per function call, not once per
entity. Only the entity's own position still needs converting per entity.
Downstream, ``fix_mul`` is a single hardware multiply, and flooring a
``fix_t`` back to a pixel coordinate is a plain arithmetic right shift —
no library call at all, unlike either of the two float attempts above.

One more wrinkle: a rotated text entity still needs a plain float
``cx``/``cy`` for the sprite-rotation math downstream, which takes float
arguments. Computing that from scratch, alongside the new fixed-point
version every entity now also computes, meant a rotated entity paid for
both — net worse than before the change for exactly that case, confirmed
by re-running ``cycle_probe.py`` against ``wordle``'s word cloud, the one
example here with heavily rotated text. Deriving the float version from
the already-computed ``fix_t`` one instead (one int-to-float conversion
and a multiply by a compile-time constant, rather than the full
subtract/add/multiply chain again) cut that overhead roughly in half.
Not to zero — a rotated entity still computes both representations, just
a cheaper version of the second one.

Checking it
===========

Cycle counts say a change is faster. They say nothing about whether it's
still correct, and a screen-space projection rewrite is exactly the kind
of change that can be wrong by one pixel and still look fine in a casual
glance at an emulator window. The check was the same shape as the
`flicker article's <flicker-article_>`_ OAM sampling, but byte-exact
instead of statistical: connect to the emulator's GDB stub, let a handful
of frames pass so
startup settles, read the full 1 KB of hardware sprite memory, and
compare it against the same read from the unmodified ROM.

.. code-block:: text

    IDENTICAL: 1024 bytes of OAM match exactly

...for both ``input_tester`` (plain, unrotated text, the common case)
and ``wordle`` (the rotated one). All 128 hardware sprite entries, same
position, same tile, same palette bank, same affine flags, in both ROMs.
The fixed-point rewrite changes how the pixel coordinate gets computed; it
is not allowed to change what the coordinate is.

The numbers
===========

Steady-state averages, ``cycle_probe.py`` against ``framer_gba_wait_vblank``:

.. list-table::
   :header-rows: 1

   * - Example
     - Before
     - After
     - Change
   * - ``input_tester`` (unrotated text)
     - ~684800 cycles/frame
     - ~660650 cycles/frame
     - ~3.5% faster
   * - ``wordle`` (rotated word cloud)
     - ~810400 cycles/frame
     - ~814470 cycles/frame
     - ~0.5% slower

``input_tester`` is the representative case: a HUD-style scene with
static, unrotated labels, which is what most of a game's own on-screen
text actually looks like. ``wordle``'s word cloud is a rotation showcase,
not representative of that, and it is the one case where this change
gives a little back. Closing that gap too would mean two separate code
paths — fixed-point only when nothing is rotated, float only when it is —
instead of one computed and the other derived from it. I didn't take it:
more branching in an already-dense function, for a demo scene rather than
the 18 FPS HUD/UI case this work was for.

What is left
============

~3.5% is real and it is not the fix for an 18 FPS scene. The per-entity
layout call and ``framer_color_bank_acquire()`` were never bracketed the
way the projection math was, and either could be sitting on cost of its
own. The method that found this one generalizes directly: two
breakpoints, a steady frame, and the delta between them — not a guess
about which function looks expensive.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
.. _flicker-article: https://tprrt.tupi.fr/dropping-sprites-on-purpose-flicker-rotation.html
