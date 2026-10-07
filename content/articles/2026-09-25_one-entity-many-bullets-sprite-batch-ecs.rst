==========================================================================
One Entity, Many Bullets: Fitting a Projectile Pool Into the ECS
==========================================================================

:date: 2026-09-25 21:40
:tags: ecs, rendering, vulkan, opengl, gba, nds, embedded, retro, gamedev, c, article
:category: gamedev
:slug: one-entity-many-bullets-sprite-batch-ecs
:authors: tperrot
:summary: A shoot-'em-up's bullet pool doesn't fit the ECS's entity budget,
    and the first fix that shipped solved that by quietly stepping outside
    the ECS entirely. The redesign that replaced it exposed three
    unrelated bugs, one per rendering backend, none about bullets.
:lang: en
:status: published

Introduction
============

The `previous article <static-ecs-article_>`_ described the static, no-heap
Entity Component System `framer-engine`_ runs on GBA and NDS: fixed tables of
component slots and entities, sized for a machine with no ``malloc()``. With
today's component set the table has room for 64 real entities. A caravan-style
vertical shoot-'em-up, the engine's first playable milestone, wants several
hundred bullets on screen in a dense pattern. The entity table cannot grow to
fit that, and the pattern cannot cap itself at 64 shots.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

The usual answer is not to make every bullet an entity. The simulation, a flat
array of structs advanced by one system, was easy. Drawing that array without
opening a second path in the renderer took two attempts. The first shipped,
worked, and was wrong in a way no test would catch. The second was smaller,
matched a pattern the engine already had, and surfaced three bugs across three
rendering backends, none about bullets.

The first answer: a queue that isn't an entity
====================================================

Hundreds of short-lived things, updated and drawn every frame and never
addressed individually, suggest a per-frame queue: a flat array of draw
commands (position, sprite, frame), reset each frame, appended to by whatever
wants something drawn and consumed once by the renderer. A bullet pool fits
exactly, pushing one entry per live bullet after the physics step, and needs
nothing from the ECS: no entity, component or query.

That was the problem. Everything else the engine draws (a sprite, a tilemap, a
HUD label) is an entity with a component, and every renderer's draw phase is
systems iterating queries. A queue fed by application code and drained by the
renderer is a second path. The entity-inspection API cannot see it, capability
queries do not know it exists, and the debugging tools built on "the ECS is the
whole scene" miss it. Bullets appeared in the right place at the right speed,
but elements without an entity bypass the engine's core model. It is a
different design that happens to render the same pixels.

The second answer: an entity that stands for many
=======================================================

`framer-engine`_ already had a component for this class of problem: a
``Tilemap`` is one entity whose component points at a grid the owner keeps,
and the renderer draws the whole grid from that entity. Nothing in "many drawn
things, one external memory, one component pointing at it" is specific to
tiles. The rewrite generalizes it as ``SpriteBatch``, and the bullet pool
becomes one more caller instead of a bespoke path:

.. code-block:: c

    struct framer_batch_sprite {
        int32_t x, y;       /* center, world units, fixed point */
        uint32_t texture;
        uint8_t frame;
        uint16_t size;       /* drawn size, world units, fixed point */
    };

    struct sprite_batch {
        const void *first;   /* owner's element array */
        const uint16_t *count; /* owner's live-element count */
        uint16_t stride;      /* bytes between elements */
    };

A ``framer_bullet`` has its own ``struct framer_batch_sprite`` as its first
field, so the pool's storage array *is* the ``SpriteBatch`` element array, with
no copy and no second buffer to keep in sync.
``framer_bullet_pool_entity_create()`` gives the pool's one entity a
``BulletPool`` component, stepped each frame by a physics system, and a
``SpriteBatch`` component built from the same array, drawn each frame by the
renderer. Every draw phase still iterates a query and draws what it finds.
The bullets stay out of the 64-slot entity table, and everything drawn is
reachable from an entity.

Every renderer backend has to learn to draw the new component independently,
which gave each one a chance to get it wrong.

Bug 1 (Vulkan): a guard that was checking the wrong component
====================================================================

Each backend's sprite system is imported once per world, so it needs a guard
against importing twice. Comparing the stored world pointer with the current
one breaks when a *different* world is allocated at the *same* address, which
every test here does by tearing a world down and creating a fresh one. The
convention in the renderer imports is to also check that a component the
import function itself registers is present on the world.

The check written for ``SpriteBatch`` tested the wrong component:

.. code-block:: c

    /* Wrong: Sprite is registered by the renderer's own import, before
     * this function ever runs -- it says nothing about whether THIS
     * function has run on this particular world. */
    if (s_world == world && FRAMER_COMPONENT_IS_REGISTERED(world, Sprite))
        return;

On a fresh world reusing a previous world's address, ``Sprite`` is already
registered by the caller, earlier in the same
``framer_sprite_system_import()``, before the guard runs. The check reports
"already set up" on the first call and the function returns without
registering ``SpriteBatch`` or its draw system. Sprites drew; batches never
did.

A test caught it. The new pixel-readback test for ``SpriteBatch`` (draw an
element, read the pixel back, expect it filled) passed on the software and
OpenGL backends and failed on Vulkan, whose suite happened to run a batch test
on a world at an address a prior test had used. The fix checks the component
this function registers:

.. code-block:: c

    if (s_world == world && FRAMER_COMPONENT_IS_REGISTERED(world, SpriteBatch))
        return;

The OpenGL and software backends had the identical guard, found by
inspection before either failed a test. Both got the same fix and were
verified.

Bug 2 (OpenGL): reading back a write that hasn't happened yet
====================================================================

The OpenGL backend compiles its default shaders lazily, on first request, and
caches them in the world's ``Shader`` singleton component:

.. code-block:: c

    const struct shader *shaders = FRAMER_GET(world, FRAMER_ID(Shader), Shader);
    if (!shaders) {
        unsigned int sprite = framer_shader_create(...);
        /* ... compile the other three default shaders ... */

        FRAMER_SET(world, FRAMER_ID(Shader), Shader, .sprite_shader = sprite, /* ... */);
        shaders = FRAMER_GET(world, FRAMER_ID(Shader), Shader);
        if (!shaders)
            return 0;
    }

    switch (type) {
    case SHADER_TYPE_SPRITE: return shaders->sprite_shader;
    /* ... */
    }

This assumes a component write takes effect immediately. It does not: a write
issued inside a running system is staged and merged once every system in that
step has finished. A second system in the same step can see it, but the call
that made the write cannot read it back. That is an ordinary property of this
ECS. Every other caller of ``framer_shader_get_default()`` came after something
upstream (loading a level, spawning a player) had already asked for a shader on
an earlier frame, so the singleton existed.

The ``SpriteBatch`` draw system is the first thing in a new scene with nothing
upstream: no mesh, no plain sprite, just a bullet pool's entity. On the first
frame its render system is the first caller of ``framer_shader_get_default()``.
The write lands, the read-back in the same call finds nothing, the function
returns 0, and that frame renders every batch element with no shader bound.
The ECS timing is fine; the fix stops reading back what was just staged:

.. code-block:: c

    struct shader created = {.sprite_shader = sprite, /* ... */};

    framer_component_set(world, FRAMER_ID(Shader), FRAMER_ID(Shader), &created);
    return shader_of_type(&created, type);

Bug 3 (all three desktop backends): drawn correctly, in the wrong order
=====================================================================================

The first two bugs were "nothing drew". In the third, every bullet drew at the
right position, size and texture, but the entity that fired them disappeared
behind its own bullets once enough piled up at its position.

``SpriteBatch`` and the per-entity ``Sprite`` draw are separate systems in the
same ECS phase, and nothing said which goes first. On GBA and NDS the hardware
settles it: OAM sprites carry a priority, and entity sprites are drawn at a
higher priority than batch elements, so an entity is in front of a batch
whatever the system order. Sampling the OAM through mGBA's debug stub mid-run
confirms it: the emitter (the round blue sprite at the center) sits in front of
the spiral it fired:

.. figure:: {static}/static/images/one-entity-many-bullets-sprite-batch-ecs/gba-oam-emitter-in-front.png
   :alt: The bullets example running under mGBA, OAM contents captured over its debug stub -- a blue emitter sprite is clearly visible on top of a spiral of orange bullet sprites radiating from it
   :align: center

   The bullets example's spiral pattern, OAM contents read directly off a
   running GBA — the emitter draws in front of every bullet it fires, by
   hardware priority, regardless of draw order.

The three desktop backends (OpenGL, Vulkan, software) have no such guarantee:
draw order is their only ordering mechanism, and the two systems registered in
whatever order the import code called them, which put ``SpriteBatch`` after the
entity sprite system. Sampling framebuffer pixels at the emitter's position
every fifty frames of a Vulkan run shows the failure: the emitter's blue for
hundreds of frames, then, once enough live bullets reach that pixel, whatever
bullet is passing through it:

.. code-block:: text

    frame  350: 2850c8 5a96ff 5a96ff 5a96ff 2850c8   (emitter blue)
    frame  750: 2850c8 5a96ff 5a96ff 5a96ff 2850c8   (emitter blue)
    frame  800: c81e28 ff7828 ffdc50 ff7828 c81e28   (bullet red/orange)
    frame 1200: c81e28 ffdc50 fffff0 ff7828 c81e28   (bullet, still)

The fix declares the order explicitly instead of relying on registration
order, on every desktop backend:

.. code-block:: c

    static const struct framer_system_dep batch_deps[] = {
        {.before = "sprite_render_system", .after = NULL}};

    framer_system_register(world, "sprite_batch_render_system",
                            FRAMER_PHASE_ON_UPDATE,
                            sprite_batch_render_system, bq, batch_deps, 1);

A new renderer test pins it down: a red entity sprite and a white batch
element on the same pixels, asserting the pixel reads back red.

Verification: one bug per backend, so one check per backend
==================================================================

The design is not backend-specific, but each backend had its own bug, so each
was checked separately. The desktop pixel-readback tests (software, OpenGL,
Vulkan) ran the same three scenes. ``examples/bullets`` was cross-compiled for
GBA and NDS and its OAM sampled through mGBA's debug stub, the technique the
`dithering article <dither-article_>`_ used to catch a hardware-only bug. Every
GBA example ROM was booted headlessly to check that a related fix did not
regress startup: one more component pushed the fixed-stride storage layout past
EWRAM, so component storage is now pooled.

One result was the same everywhere I checked: with the spiral pattern running
continuously, the live bullet count settles in the high 90s on GBA, OpenGL and
Vulkan alike.

Where this goes next
=========================

``FRAMER_STATIC_MAX_COMPONENTS`` (40) and ``FRAMER_STATIC_MAX_ENTITIES`` (104,
leaving 64 for game use) both grew slightly to fit the new component without
pushing the pooled storage past EWRAM on GBA. What remains for the bullet pool
is measuring and documenting the per-target bullet ceiling. The capacity
constants (``examples/bullets`` uses 128 on GBA/NDS, 1024 on desktop) were
picked before there were numbers to size them against.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
.. _dither-article: https://tprrt.tupi.fr/gba-dither-offset-separation.html
