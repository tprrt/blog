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
    correct made it worse before the one that helped; cycle counts from a
    debugger told them apart.
:lang: en
:status: published

Introduction
============

The `earlier article on cycle-level GBA optimization <gba-performance-article_>`_
covered the software 3D rasterizer, where two "obviously correct" changes
measured as regressions once link-time optimization's inlining was counted.
Here the same thing happens in the text renderer, with two more wrong turns
that have nothing to do with LTO.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

Two `framer-engine`_ examples with a lot of on-screen text ran far below
the 60 Hz target, both idle, nothing moving, no input needed to reproduce:
``input_tester`` (76 of a 96-slot text sprite budget active) at roughly
18 FPS, and ``wordle``, a word cloud of rotated labels, at roughly 14.5.
``phase_probe.py``, the gdbstub cycle-bracketing script used in earlier
articles, put about 69% of a frame's cost inside one function,
``gba_text_render_system``. Which part of it?

Finding where the cost lives
=============================

The function processes a handful of text entities, each with one or more
lines, each line made of several hardware sprites (one GBA OAM entry per
glyph group). Three plausible places for the cost to hide: the glyph
layout math, the screen-space projection that turns a world position into
a pixel coordinate, or the OAM attribute writes themselves, once per
glyph and so the most frequent of the three.

``arm-none-eabi-objdump -dS`` ruled out the OAM writes: they are inlined
integer stores with no library calls. The projection math was different:
``cx``/``cy`` (an entity's anchor in screen space) and ``py_base``/``px``
(where each line starts) were float, and the ARM7TDMI has no FPU, so every
subtract, add, multiply, ``floorf()`` and float-to-int conversion goes
through a software float routine.

Static inspection shows that a call exists, not how often it runs. Two
breakpoints measured that: one at the function's entry, one at the first line
of the innermost per-sprite loop body. The delta between consecutive hits of the second breakpoint is one
sprite's own cost when it stays on the same line as the sprite before it,
and the same delta plus a line's or entity's own setup when it doesn't.
In a steady frame of ``input_tester``, a same-line sprite-to-sprite step
cost about 515 cycles. A step that also crossed into a new line or a new
entity cost 7400 to 17000, roughly fifteen times as much. Those transitions are
rarer than sprites but frequent enough to dominate a frame. The per-entity and
per-line projection math was the cost, not the per-sprite work.

Attempt 1: fixed-point that rounded the wrong way
==================================================

The engine's software 3D pipeline already uses ``fix_t``, a Q12 fixed-point
type, where one hardware multiply (``fix_mul``) replaces a chain of soft-float
calls. Reusing it for text looked like the obvious fix: convert the camera
position, ortho extent, scale and entity position to ``fix_t`` and project in
integer math.

It looked right in every example. Before trusting that, I wrote a host-side
sweep test comparing the fixed-point result with the float one across a grid
of realistic camera, ortho, scale and position values. 16 of 192 combinations
disagreed, every one by exactly one, in the same direction:

.. code-block:: text

    mismatch: cam=0.0 ortho=5.0 scale=28.8 pos=0.0 expected=144 actual=143
    mismatch: cam=0.0 ortho=5.0 scale=28.8 pos=2.5 expected=72  actual=71

The existing ``fix_from_float()`` helper (shared with the 3D rasterizer,
which depends on its exact behavior) truncates toward zero. Four
conversions chained together — camera, ortho extent, scale, position —
each truncate a little short, and on values that land exactly on an
integer in float math, the accumulated shortfall floors to one below the
right answer. Text at 144.0 pixels would have shifted by a pixel on specific
camera positions, with no visible sign.

Attempt 2: the float path that measured slower
==============================================

Instead of fixing the rounding, I kept everything in float and replaced
``(int)floorf(x)`` with a hand-rolled version. ``objdump`` showed the
``floorf()`` body at 74 instructions, handling NaN, infinity and subnormals
that bounded screen-space input never produces. A truncate-then-adjust
version is exact for any finite value and looks much cheaper:

.. code-block:: c

    static inline int gba_fast_floor(float x)
    {
        int i = (int)x;
        return (float)i > x ? i - 1 : i;
    }

It is exact, verified like the first attempt, and shorter. ``cycle_probe.py``
disagreed: the steady-state average on ``input_tester`` went from 727556 to
748028 cycles/frame, a ~2.8% *regression*. The original ``(int)floorf(x)`` is
two soft-float calls (``floorf``, then the float-to-int conversion). The
replacement is three (truncate, convert back to float, compare), and each call
pays its own call/return/Thumb-interworking overhead. ``floorf()``'s large
body is cheaper than one extra call.

What actually worked
=====================

Fixed-point, with the rounding fixed: a local ``gba_fix_from_float_rounded()``
that rounds to nearest. The shared ``fix_from_float()`` stays untouched because
the 3D rasterizer depends on its truncation. The sweep test now passes,
including the exact-integer cases and the narrowest float margin around an
integer boundary.

The second change mattered as much: every frame-constant term (camera
position, ortho extent, screen-space scale) is converted to ``fix_t`` once per
call, not once per entity. Only the entity's own position is converted per
entity. ``fix_mul`` is one hardware multiply, and flooring a ``fix_t`` to a
pixel coordinate is an arithmetic right shift, with no library call.

A rotated text entity still needs a float ``cx``/``cy`` for the sprite-rotation
math. Computing it from scratch next to the fixed-point version made a rotated
entity pay for both, which was slower than before for that case;
``cycle_probe.py`` on ``wordle``'s word cloud confirmed it. Deriving the float
value from the ``fix_t`` one (one int-to-float conversion and a multiply by a
constant) halved that overhead. A rotated entity still computes both.

Checking it
===========

Cycle counts do not show correctness, and a projection rewrite can be off by
one pixel without looking wrong. The check is the `flicker article's
<flicker-article_>`_ OAM sampling, made byte-exact: connect to the emulator's
GDB stub, let a few frames pass so startup settles, read the 1 KB of hardware
sprite memory, and compare it with the same read from the unmodified ROM.

.. code-block:: text

    IDENTICAL: 1024 bytes of OAM match exactly

This holds for both ``input_tester`` (unrotated text) and ``wordle``
(rotated): all 128 sprite entries have the same position, tile, palette bank
and affine flags in both ROMs.

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

``input_tester`` is the representative case: a HUD-style scene with static,
unrotated labels. ``wordle``'s word cloud is a rotation showcase and the one
case where the change gives a little back. Closing that gap would need two code
paths, fixed-point when nothing is rotated and float when something is. I did
not add them: more branching in a dense function, for a demo scene rather than
the 18 FPS HUD case.

What is left
============

~3.5% is not the fix for an 18 FPS scene. The per-entity layout call and
``framer_color_bank_acquire()`` were never bracketed like the projection math,
and either may hold more cost. Next step: the same two-breakpoint measurement
on them.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
.. _flicker-article: https://tprrt.tupi.fr/dropping-sprites-on-purpose-flicker-rotation.html
