=============================================================================
Only Parallel Light Sources Are Supported: Faking Point Lights on the DS GPU
=============================================================================

:date: 2026-07-07 21:14
:modified: 2026-07-07 21:14
:tags: nds, gpu, lighting, embedded, retro, gamedev, article
:category: gamedev
:slug: nds-point-light-falloff-fixed-function-gpu
:authors: tperrot
:summary: The Nintendo DS's fixed-function GPU only supports directional
    lights, full stop. Two real bugs, one hardware surprise straight out
    of GBATEK, and a way to get real per-object point-light falloff out
    of hardware that has no concept of one, without ever leaving the
    hardware-accelerated path.
:lang: en
:status: published

Introduction
============

The previous two articles on this blog — one on `cycle-level
optimization <gba-performance-article_>`_, one on the `no-heap ECS
<static-ecs-article_>`_ underneath it — were both about the Game Boy
Advance: an FPU-less CPU with no hardware polygon fill at all, where
every trick is about avoiding soft-float calls and touching as few VRAM
bytes as possible. The Nintendo DS backend in `framer-engine`_
is the opposite kind of retro target — it has a real fixed-function 3D
GPU, with hardware transform, lighting, and rasterization. That sounds
like it should make lighting the *easy* part. It doesn't. It just moves
the constraint from "the CPU can't do float math" to "the GPU can't do
the thing you're asking it to do, and it won't tell you that — it'll just
render something else instead."

This article is about chasing exactly that down: a real rendering bug, a
real hardware surprise straight out of GBATEK, and a fix that gets
meaningfully closer to real point-light falloff without ever abandoning
the GPU's own lighting hardware for a software fallback.

The hardware constraint that drives everything
=================================================

Every light in framer-engine — directional, point, or spot — is the same
``struct light`` component, and every backend (GBA's software rasterizer,
desktop OpenGL/Vulkan/software, and this one) is expected to shade point
lights with real distance falloff: the closer an object is, the brighter
it gets, fading to nothing at the light's configured range. The DS's own
hardware lighting docs rule that out before any code gets written.
libnds's ``glLight()``:

.. code-block:: text

    void glLight(int id, rgb color, v10 x, v10 y, v10 z)
    Only parallel light sources are supported on the DS

Four hardware light slots, each one a color and a direction vector — no
position, no range, no falloff term anywhere in the API. The DS's GPU
computes real per-vertex Lambertian shading (``N·L``) against those four
directions entirely in fixed-function hardware, at zero CPU cost per
triangle — genuinely excellent, for a directional light. A point light,
on this hardware, can only ever be an approximation: pick a direction,
accept that "distance" isn't a thing the lighting unit knows about, and
find whatever ways are still available to make that approximation better
without leaving hardware lighting behind entirely for a per-vertex
CPU-side shading pass (which the DS's ARM946E-S can do, but which throws
away the entire reason to use the GPU's fixed-function path in the first
place).

Bug 1: an ambient floor that was zero on purpose
====================================================

Before any of the point-light work, the hardware 3D path had a simpler
problem: ``GL_AMBIENT`` — the DS's material property for "the color when
a face isn't catching any light at all" — was set to black,
unconditionally, the instant any ``Light`` entity existed in the scene:

.. code-block:: c

    /* what shipped, briefly */
    glMaterialf(GL_AMBIENT, RGB15(0, 0, 0));

``glLight()`` only lights a face whose normal faces *toward* one of the
four active directions — anything else gets zero contribution from
diffuse, and with ``GL_AMBIENT`` pinned to black, zero contribution from
ambient too. The result: any face pointing away from every active light
rendered as pure, flat black, on hardware that was otherwise correctly
shading everything facing the right way. The fix looked simple —
accumulate every ambient/directional light's color into a running sum
each frame, and feed *that* into ``GL_AMBIENT`` instead of a hardcoded
zero:

.. code-block:: c

    s_ambient_r += gl->r;
    s_ambient_g += gl->g;
    s_ambient_b += gl->b;
    /* ...clamped to 1.0 after the loop, then: */
    glMaterialf(GL_AMBIENT,
        RGB15((int)(r * s_ambient_r * 31.0f), /* ...g, b... */));

It rendered correctly with exactly one active light. It did not render
correctly with two.

The hardware surprise: ambient is summed once per active light
====================================================================

Adding a second point light to the scene — the natural next step, since
the whole point of this work was to support more than one — turned every
previously-correctly-shaded face white. Not brighter: blown-out,
clipped-to-white white, on geometry that had looked exactly right a
commit earlier.

The cause is in GBATEK's own description of the DS's polygon lighting
equation, easy to miss because nothing in libnds's ``glMaterialf()`` doc
comment mentions it: the hardware doesn't compute ``MaterialAmbient``
once and add it to the final result. It computes ``MaterialAmbient ×
LightColor``, separately, *for every currently active light*, and sums
those. Diffuse and specular are supposed to work that way — that's how
multiple colored lights are meant to combine — but ambient, conceptually,
is "the floor when nothing is lighting this face," and nothing about that
concept should scale with how many lights happen to be turned on. The DS
hardware doesn't make that distinction. Set ``GL_AMBIENT`` to the value
you actually want as a floor, and with three active lights, the hardware
hands you back three times that, added into every face's final color.

The first attempted fix was the obvious one: divide by the number of
active lights before setting ``GL_AMBIENT``, so the hardware's own
summation would reconstruct roughly the intended value.

.. code-block:: c

    /* looked right, wasn't */
    float ambient_scale = 1.0f / (float)s_num_lights;

This fixed the two-point-light overexposure. It also made a sphere lit by
one dim ambient light and two much brighter colored point lights render
far too dark — because a flat ``1/N`` correction has no way to know that
those three active lights aren't equally bright. It divides down a lone
dim ambient contribution by exactly as much as it divides down two point
lights that have nothing to do with the ambient floor at all. A cube's
few flat faces happened to look fine anyway (whichever face caught a
point light's direction was still bright from diffuse); a sphere's curved
surface — mostly *not* facing any of the three light directions — was
left with almost nothing but that over-divided ambient term, and rendered
close to black again, just from a different arithmetic mistake than
bug 1.

The actual fix reconstructs the target ambient *exactly*, not
approximately: track the real per-channel sum of every active light's own
color (not just the count of lights), and divide by that instead.

.. code-block:: c

    /* MaterialAmbient * sum(LightColor) == target once hardware sums it
     * back, regardless of how many lights are active or how bright any
     * one of them is. */
    float ambient_scale_r = 1.0f / fmaxf(s_light_color_sum_r, 0.05f);
    glMaterialf(GL_AMBIENT,
        RGB15((int)(r * amb_r * ambient_scale_r * 31.0f), /* ...g, b... */));

Since ``MaterialAmbient × sum(LightColor)`` is exactly what the hardware
computes internally, setting ``MaterialAmbient = target / sum(LightColor)``
makes the hardware's own summation land back on ``target`` — no matter
how many lights are active or how differently bright each one is. The
``fmaxf(..., 0.05f)`` floor matters for a real edge case this reasoning
otherwise misses entirely: if every active light has an exact ``0`` in
one color channel (a pure-hue light, easy to reach — a pure green point
light has no red or blue component at all), the sum for that channel is
genuinely zero, and no ``MaterialAmbient`` value can make hardware
produce a nonzero result by multiplying against a color that has none.
Flooring the divisor doesn't fully fix that case — the DS hardware
mathematically cannot recover a floor for a channel no active light
contributes to — but it keeps the reconstruction from returning ``inf``
and cascading into garbage the moment a scene reaches for a light whose
color isn't already a happy accident of "has something in every channel."

RGB555 has an opinion about how bright "bright enough" is
=============================================================

With the arithmetic fixed, faces pointing away from every light were no
longer *wrong* — just still visually indistinguishable from unlit black
in a real screenshot. RGB555 gives each channel 5 bits, 32 steps; a first
ambient floor of 0.18 on a 0.8-albedo material works out to roughly
``0.8 * 0.18 * 31 ≈ 4/31`` — technically nonzero, comfortably lost to
ordinary display gamma and contrast. Raising the floor to 0.45 reaches
roughly ``11/31``, about 35%: the difference between "the math is
correct" and "a person looking at the screen can tell the math is
correct." Getting the equation right and getting the number right turned
out to be two separate bugs, not one.

Real per-object falloff, without leaving hardware lighting
================================================================

With the ambient floor actually behaving, the remaining problem was the
one this article opened with: point lights, as hardware directional
lights, weren't just "no falloff" in the abstract — the direction itself
was computed once per *frame*, not per object, from the world *origin*:

.. code-block:: c

    /* once per frame, not once per object */
    float lx = gl->x, ly = gl->y, lz = gl->z; /* the light's position */
    /* ...normalize (lx, ly, lz) as a direction from the origin... */
    glLight(s_num_lights, hw_color, dx, dy, dz);

Every object in the scene, regardless of where it actually sat relative
to that light, saw the identical direction and the identical brightness,
with no falloff at all. A "point" light behaved exactly like a directional one
from every single object's point of view — which is a stronger
regression than the hardware's own real limitation demands. The DS
genuinely cannot do per-*pixel* or per-*vertex-across-one-object* falloff
for a point light; it can absolutely do a different, *correct* direction
and brightness for each separate object, if something recomputes those
per object instead of once for the whole frame.

That's the fix: move the ``glLight()`` upload from once-per-frame to
once-per-object, called right before that object's own triangles submit,
computing real direction and falloff from *that object's* actual world
position:

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

An object near the light now renders bright; an object near the edge of
its range renders dim; an object outside the range entirely gets nothing
from it — a real approximation of point-light falloff, per object,
running through the exact same hardware ``N·L`` diffuse calculation the
GPU always did. Nothing about the triangle count, vertex count, or
rasterization work changes even slightly — this only changes the
*values* written into two hardware registers that were already being
written once per object either way.

It isn't free in the sense of costing literally zero CPU cycles — a
point light's direction still needs a square root to normalize, and that
now happens once per (point light, object) pair instead of once per
frame. But it's the same fixed-point ``sqrtf32``/``divf32`` primitives
this code already used for the once-per-frame version, on a scene with a
handful of lights and a handful of objects — a few extra fixed-point
operations, not a new soft-float cost, and not one more vertex for the
GPU to transform or one more pixel for it to fill. Against the cost of
submitting an object's actual geometry at all, it doesn't move the
needle, which is the only sense of "free" that was ever on the table for
a change like this.

Two smaller wins that came out of the same pass
====================================================

Two more things fell out of looking this closely at the hardware
lighting path, neither one changing a single triangle:

``GL_ANTIALIAS`` was already enabled at startup, and doing about half of
its job. The DS only blends an edge under antialiasing where the polygon
ID changes across it — and every object in the scene defaulted to the
same ID (0), so hardware edge smoothing only ever applied where an
object's silhouette met the background. Two overlapping objects, sharing
the same ID, got a hard edge between them regardless. Assigning each
object its own ID (an index mod 63, since ``glClearPolyID(63)`` reserves
63 for the backdrop) makes that blending apply between objects too — a
different bitmask, OR'd into a ``glPolyFmt()`` call that already happens
once per object, at the same cost as before.

And the built-in sphere/cone mesh, generated at 12 sectors × 6 stacks
(120 triangles), was sized for a target this GPU isn't. That segment
count lives in a comment noting the DS's real per-frame budget is "on the
order of a couple thousand polygons" — a 360-triangle sphere at 20×10 is
still a rounding error against that, and visibly rounder on screen, for a
target whose real constraint was never triangle count in the first
place.

Verifying a change with nothing to count
============================================

The GBA articles on this blog leaned on ``cycle_probe.py`` for every
claim — a deterministic emulator's own cycle counter, diffed between
frames, turning "did this help" into a yes/no number. None of that
tooling applies here, and that's not an oversight: this whole article is
about work that happens on the GPU's fixed-function pipeline, not the
ARM9's own cycles. There's no CPU-side cost to isolate with a breakpoint,
because there almost isn't one — the actual verification for this kind
of change is the build and test suite (native, GBA, and NDS cross builds,
all passing unchanged throughout), plus looking at the actual rendered
frame in melonDS to confirm the sphere in ``examples/lighting`` is now
visibly shaded by two differently-colored, differently-positioned lights
instead of one flat approximation. Different kind of hardware, different
kind of proof.

Where this goes next
========================

The DS's fixed-function GPU has real capabilities this backend still
doesn't touch at all: hardware texture sampling from VRAM, a specular
shininess table, per-vertex fog. None of those are CPU-cost questions —
they're GPU features sitting unused, the same shape of opportunity this
article's point-light work turned out to be. The natural next piece,
given how this one went, is real diffuse texturing: the highest-value use
of hardware this backend doesn't ask anything of yet, and — if the
pattern from the ambient bug repeats — probably has its own GBATEK
surprise waiting to be found the same way this one was, by trying the
obvious thing first and actually looking at what came out the other end.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
