===============================================================
Squeezing Cycles: Optimizing a Software 3D Renderer for the GBA
===============================================================

:date: 2026-06-24 22:12
:modified: 2026-07-07 20:53
:tags: gba, performance, optimization, embedded, retro, gamedev, fixed-point, article
:category: gamedev
:slug: gba-performance-optimization-framer-engine
:authors: tperrot
:summary: Techniques, cycle counts, and a few "obviously correct"
    optimizations that backfired, from porting a software 3D renderer to the
    Game Boy Advance's FPU-less ARM7TDMI in framer-engine.
:lang: en
:status: published

Introduction
============

`framer-engine`_ is a small cross-platform ECS game engine I am building, with
backends from desktop OpenGL/Vulkan down to bare software rendering on 8/16-bit
consoles. The Game Boy Advance backend renders textured and shaded 3D meshes
(cubes, cones, spheres) through a CPU-only software rasterizer on a 16.78MHz
ARM7TDMI with **no FPU and no hardware polygon fill**. Every float operation
and every divide is a library call, and every pixel is a CPU read-modify-write
into VRAM.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

.. figure:: {static}/static/images/gba-performance/simple_cube.png
   :alt: examples/simple_cube running in mGBA — a single shaded, rotating cube
   :align: center

   ``examples/simple_cube``, captured from mGBA. The ``simple_cube`` numbers
   below are measured on this demo.

Every number below comes from ``scripts/debug/gba/cycle_probe.py``, a script
that sets a breakpoint on the engine's vblank-wait function inside headless
`mGBA`_ and reads the emulator's cycle counter on every hit. mGBA's CPU
emulation is deterministic: the same ROM with the same inputs gives
bit-identical cycle counts every time, so a claim is "frame N now costs X fewer
cycles", not "it looked smoother". I discard the first ~100 frames as warm-up
(caches, lazy first-frame setup) and average the steady-state window after
that.

That discipline matters more than any single trick below, because twice an
optimization that was obviously correct measured as a **regression**. Those
are at the end.

The hardware constraint
===============================================

The GBA display is locked to the LCD's scanout rate. A frame takes 280896
system clock cycles to *display* whether or not your CPU work fits in it. If it
does not, you display every other frame or worse, and the frame rate quantizes
to ``59.73 / n`` for whatever integer multiple of the budget a frame costs.
There is no GPU to defer to and no graceful way to miss the deadline. The goal
is a CPU-side frame cost under, or close to, 280896 cycles.

Two limits drive every technique:

1. **No FPU.** Any ``float``/``double`` multiply, divide, ``sqrtf()``,
   ``sinf()``/``cosf()``/``tanf()`` compiles to a call into ARM's soft-float
   runtime: a function call plus a software algorithm per operation.
2. **No hardware rasterizer.** Mode 4's bitmap layers are VRAM written by the
   CPU. Every pixel a triangle covers is computed and stored by the ARM7TDMI.

Technique 1: fixed-point math instead of float
================================================

The most basic change: the hot path (per-vertex transform, per-pixel
rasterization) uses Q12 fixed-point integers through a small ``fix_t`` type
(``src/backends/renderer/common/sw3d_fixed.h``):

.. code-block:: c

    typedef int32_t fix_t;

    #define FIX_SHIFT 12
    #define FIX_ONE   (1 << FIX_SHIFT)   /* 4096 == 1.0 */

    static inline fix_t fix_mul(fix_t a, fix_t b)
    {
        return (fix_t)(((int64_t)a * (int64_t)b) >> FIX_SHIFT);
    }

The ``int64_t`` intermediate looks expensive, but on ARM it lowers to a single
hardware ``SMULL`` (signed multiply, 64-bit result), with no library call. A
``float * float`` on this target is a soft-float call doing mantissa and
exponent bookkeeping in software.

Division still hurts, because the ARM7TDMI has no hardware divider either way:
a fixed-point divide costs an integer library call (``__aeabi_idivmod`` and
friends) instead of a float one. The perspective divide exploits a property of
that specific division to cut the cost:

.. code-block:: c

    /* fix_div()'s general implementation widens to a 64-bit intermediate to
     * stay correct for arbitrary numerators, but the perspective divide's
     * numerator is always FIX_ONE, so FIX_ONE << FIX_SHIFT never exceeds
     * 32 bits. */
    static inline fix_t fix_reciprocal(fix_t b)
    {
        return (fix_t)(((int32_t)FIX_ONE << FIX_SHIFT) / b);
    }

Replacing the general 64-bit ``fix_div()`` with this 32-bit reciprocal at the
one call site whose numerator is always ``FIX_ONE`` saved ~50,000 cycles/frame
on ``examples/spinning_shapes``.

Technique 2: a LUT instead of sinf()/cosf()
=============================================

``framer_transform_get_matrix()``, the shared cross-platform transform code,
builds rotation matrices with cglm's ``glm_rotate_{x,y,z}()``, which call
``cosf()``/``sinf()``. On desktop that is a couple of FPU instructions. On the
GBA it is a soft-float libm round trip per axis, per object, per frame.

.. figure:: {static}/static/images/gba-performance/spinning_shapes.png
   :alt: examples/spinning_shapes running in mGBA — a cube, octahedron, and cone rotating on all three axes
   :align: center

   ``examples/spinning_shapes``, captured from mGBA: three objects rotating on
   all three axes every frame. Every ``spinning_shapes`` number here comes from
   this demo.

The GBA backend carries its own 256-entry sine table (``sw3d_raster.c``),
reads cosine from the same table at a quarter-turn offset, and interpolates
linearly between samples:

.. code-block:: c

    static const fix_t gba_sin_lut[256] = { /* ... */ };

    static void gba_fast_sincosf(fix_t angle_turns_256, fix_t *s, fix_t *c)
    {
        int idx = angle_turns_256 & 0xff;
        int cidx = (idx + 64) & 0xff; /* cos(x) == sin(x + tau/4) */

        *s = gba_sin_lut[idx];
        *c = gba_sin_lut[cidx];
    }

256 entries is ~1.4° between samples, far finer than a 240x160 screen shows, so
the interpolation error never appears as jitter. Swapping it in for the float
sin/cos chain, measured A/B (``git stash`` plus identical build and measure
commands) on ``spinning_shapes`` (3 objects rotating on all 3 axes every
frame): **1,294,320 → 1,234,341 cycles/frame, ~4.6% less**, from removing one
class of soft-float call.

A follow-up went further. cglm builds the rotation matrix with up to three
generic 4x4 matrix multiplies, one per nonzero Euler axis, each a 64
multiply-add matmul although most entries of a pure-axis rotation matrix are 0
or 1. Instead, the 9 nonzero 3x3 entries of the combined ``Rz·Ry·Rx`` product
are expanded by hand from the three angles' sin/cos (still from the LUT) and
folded into the output with one ``glm_mat4_mul``:

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

I verified it against the three-matmul path with NumPy differential tests over
all 8 zero/nonzero axis combinations and thousands of random angle triples (max
absolute error ~1e-16) before it touched the renderer. The gain was only
**1,309,080 → 1,306,224 cycles/frame, ~0.22%**, far less than the operation
count suggests, because the optimizer already folds away most of the zero and
one multiplies when each ``Rz``/``Ry``/``Rx`` factor starts from an
identity-seeded matrix. Hand-expanding math only pays once you have checked
what the compiler already does. A branch-free variant that skipped the matrix
multiply altogether (translation column copy plus per-column scale) measured
*worse* in every iteration than this one-matmul version, and I discarded it.

Technique 3: Quake III's fast inverse square root
===================================================

Triangle shading needs each surviving triangle's world-space normal,
normalized, once per shaded triangle per frame, in the renderer's hottest loop.
cglm's ``glm_vec3_normalize()`` calls ``sqrtf()`` and divides by the result:
two soft-float calls per triangle.

The fix is the well-known bit-hack:

.. code-block:: c

    static float sw3d_fast_inv_sqrt(float number)
    {
        union { float f; uint32_t i; } conv = { .f = number };

        conv.i = 0x5f3759df - (conv.i >> 1);
        conv.f *= 1.5f - (0.5f * number * conv.f * conv.f); /* one Newton-Raphson step */
        return conv.f;
    }

A magic-constant shift gives a rough inverse square root straight from the
float's IEEE bit pattern, with no sqrt call, and one Newton-Raphson step
sharpens it until it is visually indistinguishable for lighting. It replaces
both the sqrt and the divide at every site in the GBA backend that called
``glm_vec3_normalize()`` (face-normal lighting in the renderer and the
rasterizer's triangle-normal centroid computation), removing two soft-float
calls per triangle.

Technique 4: an ECS dispatch early-out
========================================

Not every win is in the renderer. ``framer_world_progress()``, the ECS
scheduler's per-frame loop, walked every registered system's full entity range
every frame, including systems whose query needs a component type that **no
entity in the scene has ever had**. ``simple_cube`` registers
collider/velocity/rigidbody systems on every platform (component import is
unconditional), so most systems scanned entities every frame to match none.

The fix tracks a sticky OR of every component bit ever set in the world and
skips a system's scan entirely, in O(1) with no entity walk, when its query's
required mask includes a bit outside that set, since it can never match:

.. code-block:: c

    /* s_any_mask: sticky OR of every component bit ever set across the
     * world's lifetime. A query whose mask requires a bit outside this set
     * can never match any entity — skip the per-entity scan entirely. */
    if ((q->mask & world->s_any_mask) != q->mask)
        continue;

This is the largest single win in the project: ``simple_cube`` **308650 →
288629 cycles/frame**, ``spinning_shapes`` **757806 → 744701 cycles/frame**
(steady-state averages over frames 101-150). It is a scheduler fix, not a
renderer trick, found the same way: measure where the cycles go.

Technique 5: making divides Bresenham-shaped
==============================================

The scanline rasterizer (``sw3d_fill_triangle()``/``sw3d_fill_quad()``)
originally tested every pixel in each triangle's bounding box against all three
edge functions. The replacement computes each row's ``[lo, hi]`` x-span per
edge, incrementally. That is Bresenham's line algorithm applied to "x as a
function of y" along a triangle edge:

.. code-block:: c

    /* Incrementally tracks bound(y) = floor((b0 + (y - y0) * d) / a) for a
     * fixed positive `a`, one row at a time, with zero divisions after
     * init. The GBA's ARM7TDMI has no hardware divider, so trading one
     * division per edge (at init) for what used to be a same-sign test on
     * every bounding-box pixel is the whole point. */
    struct row_bound {
        long val, step, rem, err, a;
    };

"One division-equivalent test per candidate pixel" becomes "one division per
triangle edge plus an integer add per row", a large change on a CPU with no
divider.

It also produced an unusual micro-optimization. The one division still needed
per edge (``floordiv_pos()``) is built on ``a / b`` and ``a % b`` in C, which
GCC should fuse into a single ``__aeabi_idivmod`` call. Disassembly showed the
fusion on one branch (``a > 0``) but not the other (``a < 0``, which negates
both operands first): a redundant ``__aeabi_idiv`` next to the
``__aeabi_idivmod`` for the *same* division. Restructuring the C source gave
byte-identical codegen, so I could not fix it from the C side. The fix is to
call the library function directly and unpack its packed 64-bit ``r0:r1``
quotient/remainder by hand, so the compiler cannot make the wrong fusion
choice:

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

This saved roughly 25,000-30,000 cycles/frame on ``spinning_shapes``, by
removing one redundant library call on one branch that no compiler flag could
remove.

Technique 6: let the hardware scale a smaller image
=====================================================

The GBA has no hardware polygon fill, so every covered pixel is a CPU
read-modify-write into VRAM. That is the floor under every other optimization
here: once every avoidable divide and float operation is gone, you are still
bound by how many pixels the CPU touches.

The way around it is not a CPU optimization. Mode 4's BG2 layer supports affine
transforms even though it is a flat bitmap, the trick behind GBA games that
faked SNES Mode 7 scaling. The renderer draws only a 120x80 corner of the
framebuffer (a quarter of the 240x160 screen's pixels) and BG2's affine matrix
stretches it across the screen at scanout, in hardware, at no CPU cost:

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

On ``spinning_shapes`` this took the steady-state cost from ~1.55M to ~1.28M
cycles/frame, roughly **10.8fps → 13.1fps, ~17% less**, at the price of
visibly blockier 2x nearest-neighbor edges. It is opt-in (``-Dgba_half_res``),
because unlike every other technique here it is a visible quality trade, not a
free win.

How the measurements work
=============================================================

None of the numbers above are estimates. ``scripts/debug/gba/cycle_probe.py``
drives headless mGBA, breaks on the engine's vblank-wait call (the one point
every frame passes through exactly once), and reads the emulator's cycle
counter on every hit. mGBA's CPU core is deterministic, unlike real silicon, so
the same ROM, breakpoint and warm-up discard give **bit-identical cycle counts
on every run**. "Did this help?" becomes a yes/no question: rebuild, re-run the
probe, diff the number.

That is also what caught the two optimizations that were obviously correct and
were not.

Failed attempt 1: caching screen-space half-extents that never change
=====================================================================

The camera's screen-space half-width and half-height, once converted to
fixed-point, do not change from frame to frame unless the projection changes.
Hoisting the conversion out of the per-vertex projection loop and caching it
looked like a free win: same values, computed once instead of once per vertex.

It measured as a regression.

The likely cause, from inspecting the generated assembly: the project builds
with link-time optimization (LTO) and ``-Doptimization=3``, and LTO's inlining
heuristics are sensitive to function and loop *size* in ways the C source does
not show. A cache check, even a cheap one, in an already-hot inlined loop
changed the cost/benefit the inliner used elsewhere in the same translation
unit, and the loss of more valuable inlining outweighed the arithmetic saved.
The hoist was right about the math and wrong about the measured outcome.

Failed attempt 2: skipping integration work for a zero velocity
===============================================================

The same thing happened independently in ``velocity_integration_system()``.
Most entities in ``simple_cube`` have a ``Velocity`` that is exactly zero every
frame. A zero-vector early-out before the ``glm_vec3_scale``/``glm_vec3_add``
calls is mathematically a no-op, so it looked like free cycles for every
entity that was not moving:

.. code-block:: c

    /* tempting, and wrong on this build */
    if (glm_vec3_isvalid(v->linear) && glm_vec3_norm2(v->linear) == 0.0f &&
        glm_vec3_norm2(v->angular) == 0.0f)
            continue;

Measured: **+112 cycles/frame on simple_cube, +312 on spinning_shapes**, a
regression from a change with no behavior difference. Same root cause: the
early-out added code size and a branch to a hot loop, LTO's inlining shifted,
and the inlining lost elsewhere cost more than the skip saved. I reverted it in
the same session.

The takeaway is not that loop-invariant hoisting or early-outs are untrustworthy;
both are standard and usually right. Once a build relies on LTO and aggressive
optimization levels, the compiler's decisions are part of the system you are
optimizing, and they do not always move the way your model of the code
predicts. The only check is the one used for every win here: change one thing,
measure, keep it only if the number goes down.

Failed attempt 3: quantizing colors in the wrong number system
==============================================================

The GBA backend's shaded sprites and triangles go through
``gba_palette_index()``, a linear scan (up to 256 entries, with a nearest-color
distance calculation once full) that maps a computed RGB555 value onto
``BG_PALETTE``, since Mode 4 is 8bpp paletted. A one-entry cache handles two
*consecutive* calls requesting the same value. But continuous per-frame
lighting (``examples/lighting``, added since this article's original
techniques, orbits two colored point lights around a static sphere and cube)
makes each shaded triangle request a slightly different value almost every
frame. That defeats the cache and saturates the palette within seconds.

The obvious fix was to round each lit color channel to a coarser step, 16
buckets instead of RGB555's 32, before the palette lookup. A gradually changing
light then collapses onto fewer, more repeated values: more cache hits and a
palette that stays truer to intent for longer. The first implementation worked
in float space, where the lit color already was a ``float``:

.. code-block:: c

    /* looked free, measured otherwise */
    static inline float gba_quantize_channel(float v)
    {
        const float steps = 16.0f;
        return (float)(int)(v * steps + 0.5f) * (1.0f / steps);
    }

Measured with ``cycle_probe.py`` on the same orbiting-lights demo, 150 frames,
steady-state average over frames 101-150: **646528 cycles/frame with no
quantization versus 658869 with it, a ~1.9% regression**.

This is still the FPU-less ARM7TDMI. ``v * steps + 0.5f``, the cast and
``* (1.0f / steps)`` are three more soft-float calls on each of the three
channels, for every shaded triangle every frame, which cost more than the
palette-scan time saved. An optimization aimed at this hardware's constraint
had ignored that constraint.

The fix rounds in integer space, using a value the code already computes.
``f_to_5bit()``, the existing float→RGB555-channel helper, produces a clamped
0-31 integer, and masking off its low bit gives the same 16 buckets for one
``AND``:

.. code-block:: c

    static inline u16 f_to_5bit_quantized(float v)
    {
        return (u16)(f_to_5bit(v) & ~1u);
    }

Same demo, same measurement: **642455 cycles/frame**, a modest **~0.63%
improvement** over the no-quantization baseline. The idea was sound; it had to
be expressed in a number system this CPU handles cheaply.

Where this leaves things
==========================

``examples/simple_cube`` now sits at 288074 cycles/frame. 16777216 / 288074,
the same ratio ``cycle_probe.py`` reports for every measurement here, gives
**~58.24fps**, against a 60fps budget of 280896 cycles (~59.73fps). That is
about 2.5% over budget, down from roughly 7-8% before this round of work.
``spinning_shapes``, three shaded objects rotating on all three axes, a heavier
scene by design, sits at 741378 cycles/frame, **~22.63fps**. These are
ceilings for these demo scenes on cycle-accurate emulation, not estimates; more
triangles or lights move the frame cost accordingly.

Closing the rest of the gap on ``simple_cube`` means riskier changes: caching
ECS query results across frames (beyond the existence check from Technique 4),
or pre-converting mesh vertex data to fixed-point ahead of time instead of
per-vertex at raster time. The latter is complicated because the same mesh
struct is also filled through the engine's public float-only custom-mesh API,
so caching would mean changing that API or building a cache-on-first-use
scheme. Both are bigger than "swap a divide for a multiply", and I am stopping
here rather than chasing harder-to-verify returns from more soft-float removal.

What's next
==============

The GBA backend was the first test of whether framer-engine's approach (an ECS
with 3D, software-rendered, no FPU) holds up on constrained hardware. The next
targets step up in capability: 32-bit-era consoles like the PlayStation 1, and
handhelds with 3D acceleration (PSP, Nintendo DS, 3DS). The goal is an engine
that is pleasant for small demos and indie games on real retro hardware, GBA
included.

At least one of them, probably the PSP with its conventional FPU-plus-GPU
setup, is there for another reason. Every technique here exists because the GBA
has no FPU and no hardware rasterizer. On a platform with both, those tricks do
not apply, and the question becomes how far the engine and hardware go
together. That work is closer to traditional real-time 3D budgeting (draw
calls, vertex throughput, fill rate) than to soft-float avoidance, and needs
the same measurement discipline aimed at a different bottleneck. Whether any of
these tricks carry over is for later articles.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _mGBA: https://mgba.io
