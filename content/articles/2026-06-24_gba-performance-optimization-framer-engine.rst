===============================================================
Squeezing Cycles: Optimizing a Software 3D Renderer for the GBA
===============================================================

:date: 2026-06-24 22:12
:modified: 2026-06-24 22:12
:tags: gba, performance, optimization, embedded, retro, gamedev, fixed-point, article
:category: gamedev
:slug: gba-performance-optimization-framer-engine
:authors: tperrot
:summary: Real techniques, real cycle counts, and a couple of "obviously
    correct" optimizations that backfired, from porting a software 3D
    renderer to the Game Boy Advance's FPU-less ARM7TDMI in framer-engine.
:lang: en
:status: published

Introduction
============

`framer-engine`_ is a small cross-platform ECS game engine I've been
building, with backends ranging from desktop OpenGL/Vulkan down to bare
software rendering on 8/16-bit consoles. The Game Boy Advance backend
renders actual textured/shaded 3D meshes — cubes, cones, spheres — through
a CPU-only software rasterizer, on a 16.78MHz ARM7TDMI with **no FPU and
no hardware polygon fill**. Every float operation is a soft-float library
call, every divide is a library call, and every pixel is a CPU
read-modify-write into VRAM.

.. figure:: {static}/static/images/gba-performance/simple_cube.png
   :alt: examples/simple_cube running in mGBA — a single shaded, rotating cube
   :align: center

   ``examples/simple_cube``, captured straight from mGBA — the demo this
   article's ``simple_cube`` numbers are measured on.

This article is about what it actually takes to make that fast — not in
theory, but measured. Every number below comes from
``scripts/debug/gba/cycle_probe.py``, a small script that sets a
breakpoint on the engine's vblank-wait function inside headless `mGBA`_
and reads the emulator's cycle counter on every hit. mGBA's CPU emulation
is deterministic: the same ROM run with the same inputs produces
bit-identical cycle counts every time, which means an optimization claim
isn't "it looked smoother" — it's "frame N now costs X fewer cycles, every
single run." I discard the first ~100 frames as warm-up (caches, branch
predictor-equivalent effects, lazy first-frame setup) and average the
steady-state window after that.

That discipline matters more than any individual trick below, because
twice during this work an optimization that was obviously, mathematically
correct measured as a **regression**. More on that at the end.

The hardware constraint that drives everything
===============================================

The GBA's display is locked to the LCD's scanout rate. A frame takes
exactly 280896 cycles of the system clock to *display*, whether or not
your CPU work fits inside it — if you go over, you just drop to displaying
every other frame (or worse), the displayed frame rate quantizing to
``59.73 / n`` for whatever integer multiple of that budget your frame
actually costs. There's no "GPU" to defer to and no way to partially
miss the deadline gracefully. The entire optimization exercise is: get
the CPU-side frame cost under (or as close as possible to) 280896 cycles.

Every technique below exists because of two specific limits:

1. **No FPU.** Any ``float``/``double`` arithmetic — multiply, divide,
   ``sqrtf()``, ``sinf()``/``cosf()``/``tanf()`` — compiles to a call into
   ARM's soft-float runtime. That's not "slower than native float," it's
   "a function call plus a software algorithm" for every single operation.
2. **No hardware rasterizer.** Mode 4's bitmap layers are just VRAM you
   write to with the CPU. Every triangle the software renderer fills is
   pixels the ARM7TDMI itself has to compute and store, one at a time.

Technique 1: fixed-point math instead of float
================================================

The most foundational change is also the simplest to state: the hot path
(per-vertex transform, per-pixel rasterization) uses Q12 fixed-point
integers instead of float, via a small ``fix_t`` type
(``src/backends/renderer/common/sw3d_fixed.h``):

.. code-block:: c

    typedef int32_t fix_t;

    #define FIX_SHIFT 12
    #define FIX_ONE   (1 << FIX_SHIFT)   /* 4096 == 1.0 */

    static inline fix_t fix_mul(fix_t a, fix_t b)
    {
        return (fix_t)(((int64_t)a * (int64_t)b) >> FIX_SHIFT);
    }

``fix_mul``'s ``int64_t`` intermediate looks like it should be expensive,
but on ARM it lowers to a single hardware ``SMULL`` (signed multiply,
64-bit result) instruction — no library call, no precision tricks, just
the right type for the CPU's native multiply. Compare that to a
``float * float``, which on this target is a soft-float call doing
mantissa/exponent bookkeeping in software.

Division is the one place fixed-point still hurts, because there's no
hardware divider on the ARM7TDMI either way — fixed-point divide still
costs a library call (``__aeabi_idivmod`` et al.), just an integer one
instead of a float one. The perspective-divide hot path exploits a
narrower fact about *that specific* division to cut its cost further:

.. code-block:: c

    /* fix_div()'s general implementation widens to a 64-bit intermediate to
     * stay correct for arbitrary numerators, but the perspective divide's
     * numerator is always FIX_ONE, so FIX_ONE << FIX_SHIFT never exceeds
     * 32 bits. */
    static inline fix_t fix_reciprocal(fix_t b)
    {
        return (fix_t)(((int32_t)FIX_ONE << FIX_SHIFT) / b);
    }

That one change — replacing the general 64-bit ``fix_div()`` with a
32-bit-only reciprocal for the one call site where the numerator is known
to always be ``FIX_ONE`` — measured a ~50,000 cycle/frame saving on
``examples/spinning_shapes``, just from giving the divide routine a
narrower, cheaper problem to solve.

Technique 2: a LUT instead of sinf()/cosf()
=============================================

``framer_transform_get_matrix()`` (the shared, cross-platform transform
code) builds rotation matrices via cglm's ``glm_rotate_{x,y,z}()``, which
call ``cosf()``/``sinf()``. On desktop that's a couple of FPU
instructions; on the GBA it's a soft-float libm round trip, once per
axis, per object, per frame.

.. figure:: {static}/static/images/gba-performance/spinning_shapes.png
   :alt: examples/spinning_shapes running in mGBA — a cube, octahedron, and cone rotating on all three axes
   :align: center

   ``examples/spinning_shapes``, captured from mGBA — three objects
   rotating on all three axes every frame, the demo behind every
   ``spinning_shapes`` number in this article.

The GBA backend instead carries its own 256-entry sine table
(``sw3d_raster.c``), reading cosine from the same table at a quarter-turn
offset, with linear interpolation between samples:

.. code-block:: c

    static const fix_t gba_sin_lut[256] = { /* ... */ };

    static void gba_fast_sincosf(fix_t angle_turns_256, fix_t *s, fix_t *c)
    {
        int idx = angle_turns_256 & 0xff;
        int cidx = (idx + 64) & 0xff; /* cos(x) == sin(x + tau/4) */

        *s = gba_sin_lut[idx];
        *c = gba_sin_lut[cidx];
    }

256 entries means ~1.4° between samples — far finer than visible on a
240x160 screen, so the linear interpolation error never shows up as
visible jitter. Swapping this in for the float sin/cos chain, measured
A/B (``git stash`` + identical build/measure commands) on
``spinning_shapes`` (which rotates 3 objects on all 3 axes every frame):
**1,294,320 → 1,234,341 cycles/frame, a ~4.6% reduction**, from removing
one class of soft-float call entirely.

A follow-up went further: rather than building the rotation matrix the
way cglm does — up to three separate generic 4x4 matrix multiplies, one
per nonzero Euler axis, each a 64-multiply-add matmul even though most
entries of a pure-axis rotation matrix are 0 or 1 — the combined
``Rz·Ry·Rx`` product's 9 nonzero 3x3 entries are expanded by hand from the
three angles' sin/cos (still sourced from the LUT above) and folded into
the output with a single ``glm_mat4_mul`` instead of up to three:

.. code-block:: c

    /* out = Rz * Ry * Rx, 9 nonzero entries expanded by hand instead of
     * three generic 4x4 matmuls. */
    out[0][0] = cy * cz;
    out[0][1] = cy * sz;
    out[0][2] = -sy;
    out[1][0] = sx * sy * cz - cx * sz;
    out[1][1] = sx * sy * sz + cx * cz;
    out[1][2] = sx * cy;
    out[2][0] = cx * sy * cz + sx * sz;
    out[2][1] = cx * sy * sz - sx * cz;
    out[2][2] = cx * cy;

This was verified against the original three-matmul path via NumPy
differential testing across all 8 zero/nonzero axis combinations plus
thousands of random angle triples (max absolute error ~1e-16) before it
ever touched the renderer. Measured gain: only **1,309,080 → 1,306,224
cycles/frame, ~0.22%** — much smaller than the raw operation count
suggests, because the compiler's optimizer already folds away most of the
original chain's zero/one multiplies once each ``Rz``/``Ry``/``Rx`` factor
starts from an identity-seeded matrix. The lesson here isn't "this
technique didn't matter" — it's that hand-expanding math only pays for
itself once you've checked what the compiler was already doing for you.
A second, branch-free variant that skipped the matrix multiply
altogether (translation column copy + per-column scale) was also tried
and measured *worse* in every iteration than this simpler one-matmul
version — discarded in favor of what actually measures faster.

Technique 3: Quake III's fast inverse square root
===================================================

Triangle shading needs each surviving triangle's world-space normal,
normalized — once per shaded triangle, per frame, in the single hottest
loop of the renderer. cglm's ``glm_vec3_normalize()`` calls ``sqrtf()``
and then divides by it: two soft-float library calls per triangle.

The fix is the famous bit-hack:

.. code-block:: c

    static float sw3d_fast_inv_sqrt(float number)
    {
        union { float f; uint32_t i; } conv = { .f = number };

        conv.i = 0x5f3759df - (conv.i >> 1);
        conv.f *= 1.5f - (0.5f * number * conv.f * conv.f); /* one Newton-Raphson step */
        return conv.f;
    }

One magic-constant bit-shift gets a rough inverse-square-root estimate
straight from the float's IEEE bit pattern (no sqrt call at all), and one
Newton-Raphson correction step sharpens it to be visually indistinguishable
from the real thing for lighting purposes. Replacing both the sqrt *and*
the divide with this one function, used at every site in the GBA backend
that previously called ``glm_vec3_normalize()`` (face-normal lighting in
the renderer, and the rasterizer's own triangle-normal centroid
computation), removes two soft-float calls per triangle for one cheap
integer/float hybrid op.

Technique 4: an ECS dispatch early-out
========================================

Not every win is renderer-specific. ``framer_world_progress()``, the ECS
scheduler's per-frame loop, walked every registered system's full entity
range every frame — including systems whose query needs a component type
that **no entity in the scene has ever had**. ``simple_cube`` registers
collider/velocity/rigidbody systems unconditionally on every platform
(component import is unconditional, regardless of whether the scene
actually uses them), so most of those systems were scanning entities every
frame only to match zero of them, every single time.

The fix tracks a sticky OR of every component bit ever set across the
world's lifetime, and skips a system's scan entirely — O(1), no entity
walk at all — whenever its query's required mask includes a bit outside
that set, which can provably never match:

.. code-block:: c

    /* s_any_mask: sticky OR of every component bit ever set across the
     * world's lifetime. A query whose mask requires a bit outside this set
     * can never match any entity — skip the per-entity scan entirely. */
    if ((q->mask & world->s_any_mask) != q->mask)
        continue;

This is the single largest win found across the whole project:
``simple_cube``: **308650 → 288629 cycles/frame**; ``spinning_shapes``:
**757806 → 744701 cycles/frame** (both steady-state averages over frames
101-150). A scheduler-level fix, not a renderer trick, but it followed
from the exact same discipline: measure where the cycles actually go,
don't assume.

Technique 5: making divides Bresenham-shaped
==============================================

The scanline rasterizer (``sw3d_fill_triangle()``/``sw3d_fill_quad()``)
originally tested every pixel inside each triangle's bounding box against
all three edge functions to decide if it was inside. The replacement
computes each row's ``[lo, hi]`` x-span directly per edge, incrementally,
which is exactly Bresenham's line algorithm applied to "x as a function of
y" along a triangle edge:

.. code-block:: c

    /* Incrementally tracks bound(y) = floor((b0 + (y - y0) * d) / a) for a
     * fixed positive `a`, one row at a time, with zero divisions after
     * init. The GBA's ARM7TDMI has no hardware divider, so trading one
     * division per edge (at init) for what used to be a same-sign test on
     * every bounding-box pixel is the whole point. */
    struct row_bound {
        long val, step, rem, err, a;
    };

This turns "one division-equivalent test per candidate pixel" into "one
division per triangle edge, plus an integer add per row" — a meaningful
shape change on hardware with no hardware divider at all.

It also produced one of the more unusual micro-optimizations in the
codebase. The one division this scheme still needs per edge
(``floordiv_pos()``) is built on ``a / b`` and ``a % b`` in C, which GCC
is *supposed* to fuse into a single ``__aeabi_idivmod`` call when both are
needed. Disassembly showed that fusion happening on one branch
(``a > 0``) but not the other (``a < 0``, which negates both operands
first) — an extra, redundant ``__aeabi_idiv`` call alongside the
``__aeabi_idivmod`` for the *same* division, confirmed to be a GCC
codegen quirk specific to that branch (restructuring the C source
produced byte-identical codegen either way, so it wasn't fixable from the
C side). The actual fix is to call the library function directly and
unpack its packed 64-bit ``r0:r1`` quotient/remainder result by hand,
removing the compiler's latitude to make the wrong call-fusion choice at
all:

.. code-block:: c

    extern long long __aeabi_idivmod(long numerator, long denominator);

    static long floordiv_pos(long a, long b)
    {
        long long qr = __aeabi_idivmod(a, b);
        long q = (long)(uint32_t)qr;
        long r = (long)(qr >> 32);

        if (r != 0 && a < 0)
            q--; /* C truncates toward zero; floor() needs a -1 correction */
        return q;
    }

Saved roughly 25,000-30,000 cycles/frame on ``spinning_shapes`` — for
removing one redundant library call the compiler was inserting on its
own, on one branch only, for no reason a compiler flag could fix.

Technique 6: let the hardware scale a smaller image
=====================================================

The GBA has no hardware polygon fill, full stop — every pixel the
rasterizer covers is a CPU read-modify-write into VRAM, which is the hard
floor under every other optimization in this list: at some point you've
removed every avoidable division and float op, and you're still bound by
"how many pixels does the CPU have to touch."

The way around that floor isn't a CPU optimization at all: Mode 4's BG2
background layer supports affine transforms even though it's a flat
bitmap — the same trick behind GBA titles that faked SNES Mode-7-style
scaling. The renderer draws only a 120x80 corner of the framebuffer (a
quarter the pixels of the real 240x160 screen) and lets BG2's affine
matrix stretch that corner across the full screen at scanout time, for
free, in hardware:

.. code-block:: c

    #if GBA_RENDER_SCALE == 1
    static inline void gba_clear_buffer(vu16 *base) { /* full-res clear */ }
    #else
    static inline void gba_clear_buffer(vu16 *base)
    {
        /* only clear the GBA_RENDER_WIDTH x GBA_RENDER_HEIGHT corner that's
         * actually sampled by BG2's affine matrix — the rest of the page is
         * never displayed, so clearing it is wasted work. */
    }
    #endif

On ``spinning_shapes`` this dropped steady-state cost from ~1.55M to
~1.28M cycles/frame — roughly **10.8fps → 13.1fps, a ~17% reduction** —
at the cost of visibly blockier 2x-nearest-neighbor-scaled edges. It's
opt-in (``-Dgba_half_res``) rather than default, because unlike every
other technique here it's a genuine, visible quality trade-off rather
than a free win — worth calling out, since this whole article is
otherwise about *zero*-visual-cost changes.

The measurement discipline that makes any of this credible
=============================================================

None of the numbers above are estimates. ``scripts/debug/gba/cycle_probe.py``
drives headless mGBA, sets a breakpoint on the engine's vblank-wait call
(the one point every frame reliably passes through exactly once), and
reads the emulator's own cycle counter on every hit. Because mGBA's CPU
core is a deterministic interpreter/JIT — not a real, jittery piece of
silicon — the same ROM, same breakpoint, same number of warm-up frames
discarded, produces **bit-identical cycle counts on every run**. That
turns "did this help?" from a vibes question into a yes/no one: rebuild,
re-run the probe, diff the number.

That discipline is also what caught the two times this project tried an
"obviously correct" optimization that wasn't.

War story 1: caching screen-space half-extents that never change
====================================================================

The camera's screen-space half-width/half-height, once converted to
fixed-point, don't change frame to frame unless the camera's projection
changes — so hoisting that fixed-point conversion out of the per-vertex
projection loop and caching it looked like a pure, free win: same
values, computed once instead of once per vertex.

It measured as a regression.

The likely cause, confirmed by inspecting the generated assembly rather
than guessing: this project builds with link-time optimization
(LTO) and ``-Doptimization=3`` across the board, and LTO's inlining
heuristics are sensitive to function and loop *size* in ways that aren't
intuitive from the C source. Adding a cache check (even a cheap one) to
an already-hot, already-inlined loop changed the cost/benefit math the
inliner used elsewhere in the same translation unit, and the net effect
of *removing unrelated, more valuable inlining* outweighed the
arithmetic actually saved. The "obviously correct" loop-invariant hoist
was correct about the math and wrong about the measured outcome.

War story 2: skipping integration work for a zero velocity
==============================================================

The same pattern showed up again, independently, in
``velocity_integration_system()``. Most entities in ``simple_cube`` have
a ``Velocity`` component that's exactly zero every frame — adding a
zero-vector early-out before the ``glm_vec3_scale``/``glm_vec3_add`` calls
is mathematically a no-op (scaling and adding a zero vector changes
nothing), so it looked like free cycles for every entity that wasn't
actually moving:

.. code-block:: c

    /* tempting, and wrong on this build */
    if (glm_vec3_isvalid(v->linear) && glm_vec3_norm2(v->linear) == 0.0f &&
        glm_vec3_norm2(v->angular) == 0.0f)
            continue;

Measured: **+112 cycles/frame on simple_cube, +312 on spinning_shapes.**
A regression, on a change with no behavior difference whatsoever. Same
root cause as the screen-extent cache: the early-out added code size and
a branch to a hot loop, LTO's inlining decisions shifted in response, and
whatever inlining was lost elsewhere cost more than the skip saved. It
was reverted in the same session it was tried, per the same rule that
caught it: measure before keeping, no exceptions for changes that "can't
possibly" make things worse.

The takeaway isn't "don't trust loop-invariant hoisting" or "don't trust
early-outs" — both are completely standard, usually-correct techniques.
It's that once a build is leaning on LTO and aggressive optimization
levels to do a lot of the heavy lifting, the compiler's own decisions
become part of the system you're optimizing, and they don't always move
in the direction your mental model of the code predicts. The only way to
know is the same ``cycle_probe.py`` round-trip used for every win in this
article: change one thing, measure, keep it only if the number actually
goes down.

Where this leaves things
==========================

After all of the above, ``examples/simple_cube`` sits at 288074
cycles/frame — 16777216 / 288074, the same ratio ``cycle_probe.py``
itself reports for every measurement in this article — works out to
**~58.24fps**, against a true-60fps budget of 280896 cycles (~59.73fps).
That's about 2.5% over budget, down from a starting point of roughly
7-8% over before this round of work. ``spinning_shapes`` — three fully
shaded objects rotating on all three axes every frame, a heavier scene
by design — sits at 741378 cycles/frame, **~22.63fps**. Both are ceilings
for these specific demo scenes on real, cycle-accurate emulation, not
estimates: add more triangles or lights to either scene and the
frame cost (and fps) moves accordingly. Closing the rest of that gap on
``simple_cube`` would mean moving into riskier
territory: caching ECS query results across frames (not just the
existence-of-any-entity check from Technique 4), or pre-converting mesh
vertex data to fixed-point ahead of time instead of per-vertex at raster
time — the latter complicated by the fact that the same mesh struct is
also populated through framer-engine's public, float-only custom-mesh
API, so caching it would mean either changing that API or building a
runtime cache-on-first-use scheme. Both are real options, just bigger
ones than "swap a divide for a multiply" — a good place to stop for now
and pick back up deliberately, rather than rush into more soft-float
removal for diminishing, harder-to-verify returns.

What's next
==============

The GBA backend was the first proof that framer-engine's "real ECS, real
3D, software-rendered, no FPU" approach actually holds up on constrained
hardware. The next targets are mainly a step up in capability rather than
a step down: 32-bit-era consoles like the PlayStation 1, and handhelds
with genuine 3D hardware acceleration — PSP, Nintendo DS, and 3DS. That
side of the plan is mostly for fun: getting framer-engine to a point
where it's genuinely pleasant to build small demos and little indie games
on real retro hardware, GBA included.

But at least one of those targets — most likely the PSP, the one with the
most conventional FPU-plus-GPU setup of the group — is also there for a
different reason. Every technique in this article exists *because* the
GBA has no FPU and no hardware rasterizer; on a platform that has both,
none of those specific tricks apply, and the interesting question flips
from "how do I avoid the hardware's weaknesses" to "how far can the
engine and the hardware actually go together, pushed deliberately to
their limits, with the GPU and FPU doing what they're meant to do."
That's a different kind of optimization work — closer to traditional
real-time-3D budgeting (draw calls, vertex throughput, fill rate) than
to soft-float avoidance — and it needs the same measurement discipline as
everything above, just pointed at a different bottleneck. Whether the
specific tricks in this article carry over at all won't be clear until
that work actually starts; future articles will cover whatever turns out
to be that generation's equivalent surprise.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _mGBA: https://mgba.io
