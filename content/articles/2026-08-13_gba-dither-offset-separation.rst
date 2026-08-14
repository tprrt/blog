==========================================================================
Sixteen Offsets, Two Patterns: Debugging GBA's Ordered-Dither Translucency
==========================================================================

:date: 2026-08-13 11:00
:tags: gba, rendering, dithering, embedded, retro, gamedev, article
:category: gamedev
:slug: gba-dither-offset-separation
:authors: tperrot
:summary: A per-object dithering offset that looked correct collapsed
    sixteen possible values down to two on real hardware. The fix shipped,
    then turned out to have a subtler version of the same bug. What solved
    it was building three competing designs and testing them.
:lang: en
:status: published

Introduction
============

The two previous GBA articles, on `cycle-level optimization
<gba-performance-article_>`_ and the `no-heap ECS <static-ecs-article_>`_
underneath it, were about working around hardware with no float unit and no
polygon fill. This one is about an older constraint on the same hardware: the
GBA's Mode 4 framebuffer is 8bpp indexed, and its palette is a single
unbuffered 256-entry table with no double-buffering and no VBlank gating on
writes. Reassigning a palette slot recolors every pixel already on screen that
uses it, immediately, mid-frame if the timing is unlucky.

That rules out blending per pixel and allocating the result a palette slot on
the fly. Blending would also be too slow. `framer-engine`_'s GBA backend
rasterizes 3D faces in software on a 16.78 MHz ARM7TDMI with no hardware alpha
unit, and the `earlier optimization article <gba-performance-article_>`_ spent
its length shaving cycles off this rasterizer's inner loop. Blending means
mixing source and destination colors and resolving the result to a palette
index for every covered pixel of every translucent face, every frame.
Dithering avoids that: the per-pixel decision is one threshold compare against
a precomputed matrix, with no blend math and no palette search. Translucent
faces are drawn to roughly the fraction of screen cells their alpha implies,
using a fixed Bayer matrix, so the *density* of drawn pixels approximates the
alpha.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

That part worked the first time. What failed, twice and in two different ways,
both visible only on real hardware, was making overlapping translucent objects
dither differently enough from each other to stay visible. The second bug is a
quieter version of the first, and the fix that stuck came from building three
ROMs and looking at them, not from a smarter formula.

The setup: one matrix, one offset per object
=================================================

The dithering is a small pure function. Given a matrix of thresholds and a
per-object level (roughly alpha out of 16), a pixel draws if the matrix value
at its screen coordinate is below the level:

.. code-block:: c

    static const unsigned char DITHER_BAYER_4X4[4][4] = {
        {0,  8,  2, 10},
        {12, 4, 14,  6},
        {3, 11,  1,  9},
        {15, 7, 13,  5},
    };

    static inline bool dither_should_draw(int x, int y, int level)
    {
        return DITHER_BAYER_4X4[y & 3][x & 3] < level;
    }

That is enough for one translucent object, not for two.
``examples/translucent_cubes`` draws three overlapping cubes (red, green, blue)
at the same alpha, back to front. With no per-object variation they test the
same screen cells against the same level, so they draw to the same pixels, and
the nearest cube overwrites the farther ones where they overlap instead of
blending with them. Each object needs its own dithering *phase*: a draw-set
that differs from its neighbors' while still covering the right fraction of
pixels.

Bug 1: shifting the coordinate collapses sixteen phases into two
======================================================================

The obvious way to give each object a phase is to shift the sampled coordinate
before indexing the matrix: object *i* looks up
``BAYER[(y + py) & 3][(x + px) & 3]`` for some per-object ``(px, py)``. That
gives sixteen ``(px, py)`` pairs and, apparently, sixteen phases. It passed
review and looked right in the emulator.

It did not look right in the screenshots from hardware. With three overlapping equal-alpha
cubes, the middle one, green, was almost invisible wherever it overlapped blue.

.. figure:: {static}/static/images/gba-dither-offset-separation/bug-green-invisible.png
   :alt: examples/translucent_cubes running in mGBA with the coordinate-shift bug — only red and a dark, almost-black region are visible, no green or blue
   :align: center

   ``examples/translucent_cubes`` at the commit that shipped the
   coordinate-shift phase. Green and blue have collapsed into the same
   draw-set as another object and vanished.

Enumerating all sixteen shifts against the 4x4 matrix at that alpha level
showed the cause: only **two** distinct draw-sets exist among the sixteen
shifts. The 4x4 Bayer matrix has translational symmetry, so every shift is
equivalent, cell for cell, to another shift with the same parity of
``(px + py)``. Two objects in the same parity class draw to identical cells,
and the nearer one erases the other. Three objects and two parity classes
guarantee a collision.

The fix: rotate the compared value, not the sampled coordinate
====================================================================

The working version leaves the coordinate alone and rotates the *value read
from the matrix* by a per-object offset before comparing it with the level:

.. code-block:: c

    static inline bool dither_should_draw(int x, int y, int level,
                                           int offset)
    {
        return (int)((DITHER_BAYER_4X4[y & 3][x & 3] + offset) & 15) <
               level;
    }

``DITHER_BAYER_4X4`` is a bijection: its sixteen cells hold the values 0 to 15
once each. The cells with ``(value + offset) mod 16 < level`` form a
``level``-sized contiguous arc of that range, and as ``offset`` goes from 0 to
15 the arc's start visits every residue once. Sixteen offsets give sixteen
distinct draw-sets at every level, by construction and not just for the alpha I
tested, as sixteen Caesar shifts give sixteen distinct ciphertexts. This
shipped and the green cube reappeared. The next report from hardware was
different: not invisible, but rougher than the other two.

.. figure:: {static}/static/images/gba-dither-offset-separation/fixed-rough-4x4.png
   :alt: examples/translucent_cubes running in mGBA after the value-rotation fix — all three cubes visible, but the third one's dither pattern looks visibly rougher than the other two
   :align: center

   The demo after the value-rotation fix. All three cubes are visible, but the
   thinnest sliver, drawn last and forced onto a worse offset, already reads
   rougher than its neighbors.

Bug 2: only two offsets out of sixteen are smooth
================================================================

"Rougher" was exact. At the alpha level ``examples/translucent_cubes`` uses,
offset 0 produces a perfect alternating checkerboard:

.. code-block:: text

    offset=0                     offset=1
    #.#.#.#.                     #.#.#.#.
    .#.#.#.#                     .#.#.#.#
    #.#.#.#.                     #.#.#.#.
    .#.#.#.#                     .#.#.#.#

Only one other offset (8, half the matrix's sixteen values away) produces the
*other* perfect checkerboard, disjoint from offset 0's. Every offset in between
is the same pattern with a few cells flipped, less regular the farther it sits
from 0 or 8. Three overlapping objects need three distinct offsets, which the
previous fix gave, but with only two perfect offsets in a 16-value matrix the
third object is forced onto an irregular one. That is a structural property of
a small matrix, not a bug in the value rotation.

A bigger matrix buys a finer gradient, not an exemption
=============================================================

An 8x8 matrix (64 distinct values) does not remove the "only two perfect
offsets" property; the argument above does not depend on matrix size. It gives
a much finer gradient around the two perfect points, so a third offset near
either one looks close to perfect. The caller contract is unchanged: levels
still run from 0 to 16, and the comparison is rescaled by 4 to match the 8x8
matrix's 0-63 range:

.. code-block:: c

    static inline bool dither_should_draw(int x, int y, int level,
                                           int offset)
    {
        return (int)((DITHER_BAYER_8X8[y & 7][x & 7] + offset) & 63) <
               level * 4;
    }

The third cube went from "noticeably wrong" to "close to right". That still did
not fix the problem that mattered.

The bug the roughness metric couldn't see
==============================================

The offsets came from a 64-entry table ranked by how close each offset's own
pattern is to a perfect checkerboard: offset 0 first, offset 32 (the 8x8
matrix's other perfect point) second, then the next closest. For three visible
objects the table handed out ``0, 32, 1``.

Offset 1 is individually an excellent choice: one flipped cell out of
sixty-four. The ranking never asked how much offset 1's draw-set *overlaps*
offset 0's. The answer is 31 of 32 drawn cells identical. The third object was
again drawing to almost the same pixels as the first, which is the original bug
in a better disguise: "individually smooth" and "well separated from
neighbors" are different properties, and the ranking had conflated them.

Testing three sequences instead of guessing
================================================

Fixing the separation analytically hit a trade-off. Offsets chosen only to
maximize separation, spread evenly over the 64-value range, land on values like
16 and 48, which render as regular vertical or horizontal stripes instead of
checkerboard noise:

.. code-block:: text

    offset=1 (roughness-ranked)      offset=16 (separation-first)
    #.#.#.#.                         #.#.#.#.
    .#.#.#.#                         #.#.#.#.
    #.#.#.#.                         #.#.#.#.
    .#.#.#.#                         #.#.#.#.
    #.#.#.#.                         #.#.#.#.
    .#.#.#.#                         #.#.#.#.
    #.#.#.#.                         #.#.#.#.
    #..#.#.#                         #.#.#.#.

The stripe pattern shares 16 of 32 cells with its neighbors instead of 31, a
large improvement by the numbers. But axis-aligned stripes are a textbook case
of a dither that is *more* noticeable than diagonal checkerboard noise. More
computation could not say whether that trade looks better than the near-miss
checkerboard.

So I built three complete 64-entry offset sequences: the original
roughness-ranked table; a separation-maximizing one, a bit-reversal permutation
(a Van der Corput sequence, where entry *i* is the 6-bit binary reversal of *i*
and every prefix is evenly spread over the offset range); and a capped-overlap
middle ground. I compiled each into a ``translucent_cubes.gba`` ROM and ran
them in mGBA. The separation-maximizing sequence won, stripes included.

.. code-block:: c

    static const unsigned char GBA_DITHER_OFFSET_SEQUENCE[64] = {
        0,  32, 16, 48, 8,  40, 24, 56, 4,  36, 20, 52, 12, 44, 28, 60,
        2,  34, 18, 50, 10, 42, 26, 58, 6,  38, 22, 54, 14, 46, 30, 62,
        1,  33, 17, 49, 9,  41, 25, 57, 5,  37, 21, 53, 13, 45, 29, 61,
        3,  35, 19, 51, 11, 43, 27, 59, 7,  39, 23, 55, 15, 47, 31, 63,
    };

.. figure:: {static}/static/images/gba-dither-offset-separation/final-smooth-8x8-bitrev.png
   :alt: examples/translucent_cubes running in mGBA with the bit-reversal offset sequence — all three cubes visible, dither density looking even across all three
   :align: center

   The demo with the bit-reversal sequence: three distinct, evenly separated
   offsets, with no object drawing to nearly the same cells as another.

Verifying a change with nothing to count
=============================================

The GBA performance article relied on ``cycle_probe.py``, a deterministic cycle
count diffed between builds. It does not apply here: this is an output
correctness question, and the claims are combinatorial. I checked each of them
by construction in Python before writing the C: the sixteen distinct draw-sets
of the value rotation, the exact pixel count at every level and offset of the
8x8 matrix, and the even prefix spread of the bit-reversal sequence. Each check
enumerated every offset, level and pair. Every change also got the full desktop
test suite, a GBA cross-compile and a headless mGBA run of
``examples/translucent_cubes``. For the final sequence choice I looked at the
rendered result, the only step that caught what the math could not.

Where this goes next
=========================

The bit-reversal sequence is one fixed table shared across every scene. It
optimizes pairwise separation along the sequence, not for the specific set of
objects overlapping in a given frame. For a small, fixed handful of translucent
objects that is enough. A scene with many more would exhaust the best-separated
entries and reach ones no better than the original bug. Assigning offsets
jointly across the objects in use each frame is the next step if that happens.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
