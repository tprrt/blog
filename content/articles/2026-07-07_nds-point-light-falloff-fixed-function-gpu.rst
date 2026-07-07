=============================================================================
Only Parallel Light Sources Are Supported: Faking Point Lights on the DS GPU
=============================================================================

:date: 2026-07-07 21:14
:modified: 2026-07-23 16:52
:tags: nds, gpu, lighting, embedded, retro, gamedev, article
:category: gamedev
:slug: nds-point-light-falloff-fixed-function-gpu
:authors: tperrot
:summary: The Nintendo DS's fixed-function GPU only supports directional
    lights. Two bugs, one hardware surprise from GBATEK, and a way to get
    per-object point-light falloff out of hardware that has no concept of
    one, without leaving the hardware-accelerated path.
:lang: en
:status: published

Introduction
============

The previous two articles, on `cycle-level optimization
<gba-performance-article_>`_ and the `no-heap ECS <static-ecs-article_>`_
underneath it, were about the Game Boy Advance: an FPU-less CPU with no polygon
fill, where every trick avoids soft-float calls and VRAM writes. The Nintendo
DS backend in `framer-engine`_ is the opposite kind of target. It has a
fixed-function 3D GPU with hardware transform, lighting and rasterization.
That should make lighting the easy part, but the constraint only moves from
"the CPU can't do float math" to "the GPU can't do what you ask and renders
something else instead, without telling you."

This article covers a rendering bug, a hardware surprise from GBATEK, and a fix
that gets closer to point-light falloff without leaving the GPU's lighting
hardware for a software fallback.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

The hardware constraint
=================================================

Every light in framer-engine (directional, point or spot) is the same
``struct light`` component, and every backend (GBA's software rasterizer,
desktop OpenGL/Vulkan/software, and this one) is expected to shade point lights
with distance falloff: brighter when closer, fading to nothing at the light's
range. The DS's hardware lighting docs rule that out. libnds's ``glLight()``:

.. code-block:: text

    void glLight(int id, rgb color, v10 x, v10 y, v10 z)
    Only parallel light sources are supported on the DS

There are four hardware light slots, each a color and a direction vector, with
no position, range or falloff term. The GPU computes per-vertex Lambertian
shading (``N·L``) against those four directions in fixed-function hardware at
no CPU cost per triangle, which is excellent for a directional light. A point
light can only be an approximation: pick a direction, accept that the lighting
unit does not know about distance, and improve the approximation where
possible. The alternative is per-vertex shading on the ARM946E-S, which would
throw away the reason to use the GPU's fixed-function path.

Bug 1: an ambient floor that was zero on purpose
====================================================

Before the point-light work, the hardware 3D path had a simpler problem.
``GL_AMBIENT``, the DS material property for the color of a face catching no
light, was set to black as soon as any ``Light`` entity existed:

.. code-block:: c

    /* what shipped, briefly */
    glMaterialf(GL_AMBIENT, RGB15(0, 0, 0));

``glLight()`` lights a face only if its normal faces *toward* one of the four
active directions. Any other face gets no diffuse contribution, and with
``GL_AMBIENT`` at black, no ambient either, so every face pointing away from all
active lights rendered flat black. The fix looked simple: sum the color of every
ambient and directional light each frame and feed that into ``GL_AMBIENT``
instead of a hardcoded zero:

.. code-block:: c

    s_ambient_r += gl->r;
    s_ambient_g += gl->g;
    s_ambient_b += gl->b;
    /* ...clamped to 1.0 after the loop, then: */
    glMaterialf(GL_AMBIENT,
        RGB15((int)(r * s_ambient_r * 31.0f), /* ...g, b... */));

It rendered correctly with one active light and not with two.

The hardware surprise: ambient is summed once per active light
====================================================================

Adding a second point light turned every previously correct face white:
blown-out, clipped white, on geometry that had looked right a commit earlier.

The cause is in GBATEK's description of the DS polygon lighting equation, and
nothing in libnds's ``glMaterialf()`` doc comment mentions it. The hardware
does not compute ``MaterialAmbient`` once and add it to the result. It computes
``MaterialAmbient × LightColor`` *for every active light* and sums those.
Diffuse and specular should work that way, since that is how colored lights
combine. Ambient is conceptually the floor when nothing lights the face and
should not scale with the number of lights, but the DS does not make that
distinction. Set ``GL_AMBIENT`` to the floor you want, and with three active
lights the hardware adds three times that to every face.

The first fix was to divide by the number of active lights before setting
``GL_AMBIENT``, so the hardware's sum would reconstruct roughly the intended
value:

.. code-block:: c

    /* looked right, wasn't */
    float ambient_scale = 1.0f / (float)s_num_lights;

This fixed the overexposure with two point lights. It also made a sphere lit by
one dim ambient light and two much brighter point lights far too dark, because
a flat ``1/N`` cannot know the three lights are not equally bright. It divides
a lone dim ambient contribution by as much as it divides two unrelated point
lights. A cube's few flat faces looked fine anyway, since whichever face caught
a point light's direction was bright from diffuse. A sphere's curved surface,
mostly facing none of the three directions, was left with almost only the
over-divided ambient term and rendered close to black again, from a different
arithmetic mistake.

The actual fix reconstructs the target ambient exactly. Track the per-channel
sum of every active light's color, not just the count, and divide by that:

.. code-block:: c

    /* MaterialAmbient * sum(LightColor) == target once hardware sums it
     * back, regardless of how many lights are active or how bright any
     * one of them is. */
    float ambient_scale_r = 1.0f / fmaxf(s_light_color_sum_r, 0.05f);
    glMaterialf(GL_AMBIENT,
        RGB15((int)(r * amb_r * ambient_scale_r * 31.0f), /* ...g, b... */));

The hardware computes ``MaterialAmbient × sum(LightColor)``, so setting
``MaterialAmbient = target / sum(LightColor)`` makes its sum land on ``target``
for any number of lights of any brightness. The ``fmaxf(..., 0.05f)`` floor
covers an edge case: if every active light has an exact ``0`` in one color
channel (a pure green light has no red or blue), that channel's sum is zero and
no ``MaterialAmbient`` can make the hardware produce a nonzero result from a
color that has none. The floor does not fix that case, since the hardware
cannot recover an ambient floor for a channel no light contributes to. It only
keeps the reconstruction from returning ``inf`` and corrupting the result.

RGB555 and "bright enough"
=============================================

With the arithmetic fixed, faces pointing away from every light were no longer
wrong, but still indistinguishable from unlit black in a screenshot. RGB555 has
5 bits per channel, 32 steps. A first ambient floor of 0.18 on a 0.8-albedo
material gives roughly ``0.8 * 0.18 * 31 ≈ 4/31``: nonzero, but lost to display
gamma and contrast. Raising the floor to 0.45 gives roughly ``11/31``, about
35%, enough for a person to see that the math is right. Getting the equation
right and getting the number right were two separate bugs.

Per-object falloff, without leaving hardware lighting
================================================================

With the ambient floor behaving, the remaining problem was the one in the
introduction. The point light's direction was computed once per *frame*, from
the world *origin*, not per object:

.. code-block:: c

    /* once per frame, not once per object */
    float lx = gl->x, ly = gl->y, lz = gl->z; /* the light's position */
    /* ...normalize (lx, ly, lz) as a direction from the origin... */
    glLight(s_num_lights, hw_color, dx, dy, dz);

Every object, wherever it sat relative to the light, saw the same direction and
brightness with no falloff, so a point light behaved like a directional one.
That is worse than the hardware's real limit requires. The DS cannot do
per-pixel falloff, or per-vertex falloff within one object, but it can use a
different, correct direction and brightness for each object if something
recomputes them per object.

So the ``glLight()`` upload moves from once per frame to once per object, right
before that object's triangles submit, with direction and falloff computed from
*that object's* world position:

.. code-block:: c

    static void nds_upload_lights_for_object(const float pos[3])
    {
        for (int i = 0; i < s_num_lights; i++) {
            /* ...ambient/directional lights reuse the once-per-frame
             * direction/color computed earlier -- no position to react
             * to, so recomputing per object would be pure waste... */
            float lx = gl->x - pos[0], ly = gl->y - pos[1], lz = gl->z - pos[2];
            float d2 = lx * lx + ly * ly + lz * lz;
            float atten = 1.0f - d2 * gl->inv_range2; /* same falloff every backend uses */
            /* ...clamp atten to [0, 1], normalize (lx, ly, lz), scale color by atten... */
            glLight(i, hw_color, dx, dy, dz);
        }
    }

An object near the light renders bright, one near the edge of its range dim,
and one outside the range gets nothing. This is per-object point-light falloff
through the same hardware ``N·L`` calculation as before. Triangle count, vertex
count and rasterization work do not change; only the values written to two
hardware registers that were already written once per object.

It is not free. A point light's direction needs a square root to normalize, now
once per (point light, object) pair instead of once per frame. But it uses the
same fixed-point ``sqrtf32``/``divf32`` primitives as the per-frame version, on
a scene with a handful of lights and objects: a few more fixed-point
operations, no new soft-float cost, no extra vertex to transform or pixel to
fill. Against the cost of submitting an object's geometry it does not register.

Two smaller wins from the same pass
====================================================

Neither changes a triangle.

``GL_ANTIALIAS`` was enabled at startup and doing half its job. The DS blends
an edge under antialiasing only where the polygon ID changes across it, and
every object defaulted to ID 0, so edge smoothing applied only where an
object's silhouette met the background. Two overlapping objects with the same
ID got a hard edge between them. Giving each object its own ID (an index mod
63, since ``glClearPolyID(63)`` reserves 63 for the backdrop) applies the
blending between objects too. It is a different bitmask OR'd into a
``glPolyFmt()`` call that already happens once per object.

The built-in sphere/cone mesh was generated at 12 sectors × 6 stacks (120
triangles), sized for a target this GPU is not. A comment in the code gives the
DS's per-frame budget as "on the order of a couple thousand polygons". A
360-triangle sphere at 20×10 is a rounding error against that and visibly
rounder, and triangle count was never this target's constraint.

Update: the tessellation win had a hidden cost
====================================================

The rounder sphere had a cost this article missed at the time.
``examples/lighting`` ran at exactly 30 fps on NDS timing (melonDS) instead of
60, and the cause traced back to this pass.

``nds_submit_tri()``, which issues each triangle's vertices, also recomputed
every triangle's ``GL_AMBIENT``/``GL_DIFFUSE`` material state, including the
ambient-reconstruction division from the sections above. For a single-color
object that is waste: the material state is identical across its triangles and
needs setting once per object. A 12×6 (120-triangle) sphere issued 120
redundant ``glMaterialf()`` pairs into the GX FIFO every frame even before this
article's change; the 20×10 sphere (360 triangles) issued 360. With the
lighting example's four active lights, each re-triggering the reconstruction on
every call, frame time went just past one VBlank period.

``swiWaitForVBlank()`` does not degrade gracefully. It waits for the *next*
VBlank interrupt after the frame's work completes, so a frame either makes a
VBlank or waits for the one after. Missing one by any margin, even a fraction
of a scanline of GX FIFO backlog, halves the frame rate: 60 fps to exactly 30,
not 59 or 58. The tessellation bump caused no gradual slowdown. It sat under
the deadline until it crossed it.

The fix leaves tessellation, lighting and the ambient math unchanged. It
changes *when* the material state is written: once per object (or once per
face, for the rare object whose faces have different colors) immediately
before its triangles submit, not with every triangle. The same
``GL_AMBIENT``/``GL_DIFFUSE`` values reach the GPU and nothing drawn changes;
the identical FIFO command is issued fewer times.

The GBA backend is unaffected. Its software rasterizer computes each face's
final color in ``gba_lit_color_face()`` and has no separate material state to
reissue.

Confirmed on melonDS timing: back to a solid 60 fps. The shape of the bug is
the one this article keeps hitting: the GPU does what it is asked at whatever
cost that carries, and two reasonable changes (a rounder sphere, per-object
point-light falloff) compounded into a cost neither would have caused alone.

Verifying a change with nothing to count
============================================

The GBA articles used ``cycle_probe.py``, a deterministic emulator cycle
counter diffed between frames. It does not apply here: this work runs on the
GPU's fixed-function pipeline, not the ARM9's cycles, and there is almost no
CPU-side cost to isolate with a breakpoint. Verification was the build and test
suite (native, GBA and NDS cross builds, all passing unchanged throughout),
plus looking at the frame in melonDS to confirm that the sphere in
``examples/lighting`` is shaded by two differently colored, differently
positioned lights instead of one flat approximation.

Where this goes next
========================

The DS GPU has capabilities this backend does not use: hardware texture
sampling from VRAM, a specular shininess table, per-vertex fog. None are CPU
cost questions; they are GPU features sitting idle. Diffuse texturing is next,
as the highest-value use of unused hardware. If the ambient bug is a guide, it
will hide its own GBATEK surprise.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
