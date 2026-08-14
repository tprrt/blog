==========================================================================
Sixteen Offsets, Two Patterns: Debugging GBA's Ordered-Dither Translucency
==========================================================================

:date: 2026-08-13 11:00
:tags: gba, rendering, dithering, embedded, retro, gamedev, article
:category: gamedev
:slug: gba-dither-offset-separation
:authors: tperrot
:summary: A per-object dithering offset that looked obviously correct
    collapsed sixteen possible values down to two on real hardware. The
    fix that followed shipped, then turned out to have a second, subtler
    version of the exact same bug — and the thing that finally solved it
    was building three competing designs and testing them, not reasoning
    about them harder.
:lang: en
:status: published

Introduction
============

The two previous GBA articles on this blog — one on `cycle-level
optimization <gba-performance-article_>`_, one on the `no-heap ECS
<static-ecs-article_>`_ underneath it — were both about working around
hardware that has no float unit and no polygon fill. This one is about a
narrower, older constraint on the same hardware: the GBA's Mode 4
framebuffer is 8bpp indexed, and its palette is a single, unbuffered,
256-entry table with no double-buffering and no VBlank gating on writes.
Reassigning a palette slot recolors every pixel already on screen using
that slot, immediately, mid-frame if the timing is unlucky.

That constraint alone rules out the obvious approach — blend per pixel,
allocate the blended color a palette slot on the fly — but even without
it, real blending wouldn't be affordable here. `framer-engine`_'s GBA
backend rasterizes 3D faces in software, on a 16.78MHz ARM7TDMI with no
hardware alpha unit anywhere in this path: the `earlier article on cycle-
level optimization <gba-performance-article_>`_ on this blog spent its
entire length shaving individual cycles off this same rasterizer's inner
loop. Blending would mean computing a source/destination color mix and
resolving it back to a palette index, for every covered pixel of every
translucent face, every frame — real per-pixel work on hardware that
has none of it to spare. Dithering sidesteps the cost entirely: the
per-pixel decision is a single threshold compare against a precomputed
matrix, no blend math and no palette search, so `framer-engine`_ answers
both constraints the same way plenty of retro-hardware renderers have —
translucent 3D faces aren't blended, they're dithered, drawn to roughly
the fraction of screen cells their alpha implies, using a fixed Bayer
matrix, so the *density* of drawn pixels approximates the alpha instead
of the color itself needing to change.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

That part worked the first time. What didn't work — twice, in two
different ways, both only visible on real hardware — was making more
than one overlapping translucent object dither *differently enough* from
its neighbors to stay visible. This article is about both bugs, why the
second one is a quieter version of the first one, and why the fix that
finally stuck came from building three ROMs and looking at them, not from
finding a smarter formula.

The setup: one matrix, one offset per object
=================================================

The dithering itself is a small, pure function. Given a matrix of
threshold values and a per-object "level" (roughly, alpha out of 16), a
pixel draws if the matrix value at that screen coordinate is below the
level:

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

That's enough for one translucent object. It isn't enough for two.
``examples/translucent_cubes`` puts three overlapping cubes — red,
green, blue — at the same alpha, drawn back to front. With no per-object
variation, every one of them tests the *same* screen cells against the
*same* level, which means they all draw to the exact same pixels — and
since they're drawn back to front, the nearest one simply overwrites the
farther ones wherever they overlap, instead of the three visually
blending. Each object needs its own dithering *phase*: something that
makes its own draw-set genuinely different from its neighbors', while
each individual object still draws the right fraction of pixels.

Bug 1: shifting the coordinate collapses sixteen phases into two
======================================================================

The obvious way to give each object a phase is to shift the sampled
coordinate before indexing the matrix — object *i* looks up
``BAYER[(y + py) & 3][(x + px) & 3]`` instead of ``BAYER[y & 3][x & 3]``,
for some per-object ``(px, py)``. Sixteen possible ``(px, py)`` pairs, one
matrix, sixteen apparently different phases. It shipped, passed its own
review, and looked right in the emulator during initial testing.

It did not look right in front of the user's own screenshots. With three
overlapping equal-alpha cubes, the middle one — green, sandwiched between
red and blue in draw order — was almost entirely invisible everywhere it
overlapped blue.

.. figure:: {static}/static/images/gba-dither-offset-separation/bug-green-invisible.png
   :alt: examples/translucent_cubes running in mGBA with the coordinate-shift bug — only red and a dark, almost-black region are visible, no green or blue
   :align: center

   ``examples/translucent_cubes`` at the commit that shipped the
   coordinate-shift phase — green and blue have collapsed into the same
   draw-set as another object and vanished.

Direct enumeration of all sixteen shifts against the 4x4 matrix at the
alpha level in question found the cause immediately: only **two**
distinct draw-sets exist among all sixteen coordinate shifts, not
sixteen. The 4x4 Bayer matrix has its own translational symmetry — every
shift is equivalent, cell-for-cell, to some other shift of the same
*parity* of ``(px + py)``. Two objects landing in the same parity class
draw to identical cells, and whichever is nearer in the back-to-front
order simply erases the other. Three objects, two available parity
classes: one collision was mathematically guaranteed, not a rare edge
case.

The fix: rotate the compared value, not the sampled coordinate
====================================================================

The working version doesn't touch the coordinate at all. It rotates the
*value read out of the matrix* by a per-object offset, before comparing
it against the level:

.. code-block:: c

    static inline bool dither_should_draw(int x, int y, int level,
                                           int offset)
    {
        return (int)((DITHER_BAYER_4X4[y & 3][x & 3] + offset) & 15) <
               level;
    }

The difference isn't cosmetic. ``DITHER_BAYER_4X4`` is a bijection —
every one of its sixteen cells holds a distinct value from 0 to 15. "Which
cells have ``(value + offset) mod 16 < level``" selects a
``level``-sized *contiguous arc* of that value range, and as ``offset``
sweeps 0 to 15, the arc's starting point sweeps every residue exactly
once. Sixteen offsets, sixteen provably distinct draw-sets, at every
level — not empirically distinct for the one alpha value that happened
to get tested, but distinct by construction, for the same reason a
Caesar cipher with sixteen different shift amounts produces sixteen
different ciphertexts of the same plaintext. This shipped, the green cube
reappeared, and the next report from real hardware was different in
kind: not invisible, just rougher-looking than the other two.

.. figure:: {static}/static/images/gba-dither-offset-separation/fixed-rough-4x4.png
   :alt: examples/translucent_cubes running in mGBA after the value-rotation fix — all three cubes visible, but the third one's dither pattern looks visibly rougher than the other two
   :align: center

   The same demo after the value-rotation fix — all three cubes are
   visible now, but the thinnest sliver (drawn last, forced onto a
   worse offset) already reads rougher than its neighbors.

Bug 2: only two offsets out of sixteen are actually smooth
================================================================

"Rougher" turned out to be exact, not impressionistic. At the alpha
level ``examples/translucent_cubes`` uses, offset 0 produces a perfect
alternating checkerboard:

.. code-block:: text

    offset=0                     offset=1
    #.#.#.#.                     #.#.#.#.
    .#.#.#.#                     .#.#.#.#
    #.#.#.#.                     #.#.#.#.
    .#.#.#.#                     .#.#.#.#

Only one other offset (8, exactly half the matrix's sixteen values away)
produces the *other* perfect checkerboard, disjoint from offset 0's.
Every offset in between is a near-miss: the same pattern with a handful
of cells flipped, visibly less regular the farther the offset sits from
0 or 8. Three overlapping objects need three distinct offsets to stay
correctly visible — that part was already fixed — but with only two
"perfect" offsets available in a 16-value matrix, the third object is
mathematically forced onto a visibly irregular one. Not a bug in the
value-rotation fix; a structural property of a matrix this small
combined with needing three simultaneously-distinct patterns.

A bigger matrix buys a finer gradient, not an exemption
=============================================================

Growing the matrix to 8x8 (64 distinct values instead of 16) doesn't
remove the "only two perfect offsets" property — it can't; the argument
above doesn't care about matrix size. What it buys is a much finer
*gradient* around those two perfect points, so a third offset near
either one looks close to perfect instead of visibly broken. The
external contract stayed untouched: callers still pass a level from 0
to 16, unchanged, with the comparison internally rescaled by a factor of
4 to land on the 8x8 matrix's 0-63 range:

.. code-block:: c

    static inline bool dither_should_draw(int x, int y, int level,
                                           int offset)
    {
        return (int)((DITHER_BAYER_8X8[y & 7][x & 7] + offset) & 63) <
               level * 4;
    }

This shipped as a real improvement — the third cube went from
"noticeably wrong" to "close to right." It was also, it turned out, not
actually fixing the thing that mattered.

The bug the roughness metric couldn't see
==============================================

The offsets fed to each object weren't picked arbitrarily; they came from
a 64-entry table, ranked by how close each individual offset's own
pattern was to a perfect checkerboard — offset 0 first, offset 32
(the 8x8 matrix's other perfect point) second, then the next-closest
offsets after that. For three simultaneously-visible objects, that table
handed out ``0, 32, 1``.

Offset 1 is, individually, an excellent choice — its own pattern is
almost perfectly checkerboarded, one flipped cell out of sixty-four. The
ranking wasn't wrong about that. What it never asked is a different
question: how much does offset 1's draw-set *overlap* offset 0's? The
answer is 31 of 32 drawn cells, identical. The third object was, once
again, drawing to almost exactly the same pixels as the first one — the
original bug, wearing a much better disguise, because "individually
smooth" and "well separated from your neighbors" turned out to be two
different properties the same ranking had been quietly conflating.

Testing three sequences instead of guessing
================================================

Fixing the separation problem analytically ran straight into a genuine
trade-off, not a formula. Offsets chosen purely to *maximize* separation
from each other — evenly spread around the matrix's 64-value range —
land on values like 16 and 48, and those render as perfectly regular
vertical or horizontal stripes instead of checkerboard noise:

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

The stripe pattern shares only 16 of 32 cells with its neighbors instead
of 31 — a real, large improvement by the numbers — but axis-aligned
stripes are a textbook example of a dither pattern that's *more*
noticeable than diagonal checkerboard noise, not less, on real display
hardware. Whether that trade-off actually looks better than the original
near-miss checkerboard isn't something more computation could answer.

So the answer came from building three complete 64-entry offset
sequences — the original roughness-ranked table, a separation-maximizing
one (a bit-reversal permutation, also known as a Van der Corput
sequence: entry *i* is the 6-bit binary reversal of *i*, which
guarantees every prefix of the sequence is evenly spread around the
offset range), and a capped-overlap middle ground — compiling all three
into real ``translucent_cubes.gba`` ROMs, and testing them in mGBA. The
separation-maximizing sequence won, stripes and all.

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

   The same demo with the bit-reversal sequence — three distinct,
   evenly-separated offsets, no object drawing to nearly the same
   cells as another.

Verifying a change with nothing to count
=============================================

The GBA performance article on this blog leaned on ``cycle_probe.py`` for
every claim — a deterministic cycle count, diffed between builds. None of
that applies here: this is a pure output-correctness question, not a
performance one, and the actual measurable claims are combinatorial
rather than empirical. Every mechanism change in this story — the
value-rotation fix's sixteen-provably-distinct-draw-sets claim, the 8x8
matrix's exact-count-at-every-level-and-offset property, the bit-reversal
sequence's even-prefix-spread property — was verified by direct
construction in Python before being written as C: enumerate every
offset, every level, every pair, and check the property holds for all
of them, not just the one case that happened to get tested by hand.
Beyond that: the full desktop test suite, a GBA cross-compile, and a
headless mGBA run of ``examples/translucent_cubes`` on every change, plus
— for the final offset-sequence choice specifically — actually looking
at the rendered result, which is the only step in this whole chain that
caught the thing the math couldn't.

Where this goes next
=========================

The bit-reversal sequence is still one fixed, precomputed table, shared
across every scene — it optimizes pairwise separation for *a* sequence
of offsets, not jointly for whichever specific set of objects happens to
be simultaneously overlapping in a given frame. For the realistic case
this backend actually renders — a small, fixed handful of translucent
objects — that's enough. A scene with many more simultaneously-visible
translucent objects than any current example has would eventually
exhaust the sequence's best-separated entries and reach ones no better
than the original bug. Jointly optimizing offset assignment across the
actual in-use set, per frame, is the natural next piece if that ever
stops being hypothetical — and, going by how this story went twice
already, probably has its own hardware surprise waiting inside it.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
