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
    the ECS entirely. The redesign that replaced it went on to expose
    three unrelated bugs, one per rendering backend, none of which had
    anything to do with bullets.
:lang: en
:status: published

Introduction
============

The `previous article on this blog <static-ecs-article_>`_ was about the
static, no-heap Entity Component System `framer-engine`_ runs on GBA and
NDS: a fixed table of component slots and a fixed table of entities,
sized to fit in a machine with no ``malloc()``. That fixed sizing has a
consequence the article didn't need to dwell on at the time: with today's
component set, the table has room for 64 real entities. A caravan-style
vertical shoot-'em-up, the first playable milestone this engine is
building toward, wants several hundred bullets on screen during a dense
pattern. Neither number moves to meet the other — the entity table isn't
growing to fit a bullet count, and a bullet pattern isn't capping itself
at 64 shots to fit the table.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

The tension is old and the usual answer is old too: don't make every
bullet an entity. What took two attempts wasn't the bullet simulation
itself — a flat array of structs, advanced by one system, is not a hard
problem — it was deciding how that array gets drawn without quietly
opening a second, ECS-shaped hole in the renderer. The first answer
shipped, worked, and was wrong in a way no test had a reason to catch.
The second answer was smaller, matched a pattern the engine already had,
and went on to surface three real bugs across three different rendering
backends, none of which were about bullets at all.

The first answer: a queue that isn't an entity
====================================================

The obvious shape for "hundreds of short-lived things, updated every
frame, drawn every frame, never touched individually by name" is a
per-frame queue: a flat array of draw commands (position, sprite, frame),
reset at the start of each frame, appended to by whatever wants something
drawn, and consumed once by the renderer at the end of it. A bullet pool
fits that shape exactly — push one entry per live bullet, once, after the
physics step — and it required nothing new from the ECS at all, since
nothing about it touched an entity, a component, or a query.

That was also exactly the problem. Every other thing this engine draws —
a sprite, a tilemap, a HUD label — is an entity carrying a component, and
every renderer's draw phase is systems iterating queries. A queue fed
directly by application code and drained directly by the renderer is a
second path with none of that: it isn't visible to the entity-inspection
API a previous milestone added, it isn't something a capability query
knows exists, and it isn't something any of the debugging tooling built
around "the ECS is the whole scene" has any way to see. It worked, in the
narrow sense that bullets appeared on screen in the right place moving
at the right speed. It didn't survive being looked at as architecture:
elements without an entity, bypassing the engine's own core model,
aren't a smaller version of the real design — they're a different
design that happens to render the same pixels.

The second answer: an entity that stands for many
=======================================================

`framer-engine`_ already had a component that solves this exact
class of problem, for a different feature: a ``Tilemap`` is one entity
whose component points at a grid the owner keeps, and the renderer draws
the whole grid from that one entity every frame. Nothing about "many
drawn things, one piece of external memory, one component pointing at
it" is specific to tiles. The rewrite generalizes that shape and gives it
a name — ``SpriteBatch`` — and the bullet pool becomes one more caller
of it instead of a bespoke path of its own:

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

A ``framer_bullet`` places its own ``struct framer_batch_sprite`` as its
first field, so the bullet pool's own storage array *is* the
``SpriteBatch``'s element array — no copy, no second buffer kept in sync.
``framer_bullet_pool_entity_create()`` gives the pool's one entity both a
``BulletPool`` component, stepped every frame by a physics system, and a
``SpriteBatch`` component built from the same array, drawn every frame by
the renderer. Every renderer's draw phase still only ever does one thing:
iterate a query and draw what it finds. Hundreds of bullets stay out of
the 64-slot entity table; nothing draws that isn't reachable from an
entity.

That much is a straightforward generalization of an existing pattern, and
it's also where the interesting bugs started, because a component that
every renderer backend has to independently learn to draw is a component
that gives every renderer backend its own chance to get it wrong.

Bug 1 (Vulkan): a guard that was checking the wrong component
====================================================================

Every renderer backend's sprite system is imported once per world, and
every one of them has to answer the same small design question: how do
you know "once" has already happened? The naive answer, comparing the
stored world pointer against the one you were just called with, breaks
the moment a *different* world gets allocated at the *same* address —
which is exactly what every test in this codebase does, tearing a world
down and creating a fresh one for the next case. The existing convention
across this codebase's renderer imports is therefore to also check that
some component the import function itself registers is actually present
on the world in front of you, not just that the pointer matches.

The version of this check written for ``SpriteBatch`` picked the wrong
component to check:

.. code-block:: c

    /* Wrong: Sprite is registered by the renderer's own import, before
     * this function ever runs -- it says nothing about whether THIS
     * function has run on this particular world. */
    if (s_world == world && FRAMER_COMPONENT_IS_REGISTERED(world, Sprite))
        return;

On a fresh world reusing a previous world's address, ``Sprite`` is
already registered — by the caller, earlier in the same
``framer_sprite_system_import()`` — before this guard is ever reached.
The check reports "already set up" on the very first call, every time,
and the function returns without ever registering ``SpriteBatch`` or its
draw system. Sprites drew fine; batches never did.

This one didn't need staring at code to find — it failed exactly where a
test already existed to catch it. The new pixel-readback test for
``SpriteBatch`` (draw an element, read the pixel back, expect it filled)
passed against the software and OpenGL backends and failed against
Vulkan specifically, because Vulkan's test suite happened to run a batch
test on a world whose address a prior test had already used. Fixing the
guard to check the component this function actually registers —

.. code-block:: c

    if (s_world == world && FRAMER_COMPONENT_IS_REGISTERED(world, SpriteBatch))
        return;

— was a one-line change once the failing test pointed at exactly which
world-reuse case was wrong. The same wrong-component shape was checked
for, by inspection, in the OpenGL and software backends before either
one had actually failed a test; both had the identical guard, both got
the identical fix, and both were then verified rather than assumed
fixed.

Bug 2 (OpenGL): reading back a write that hasn't happened yet
====================================================================

The OpenGL backend's default shaders are compiled lazily, the first time
anything asks for one, and cached in the world's own ``Shader``
singleton component so the next thousand callers don't recompile
anything:

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

This is correct exactly as long as a component write, from the caller's
point of view, takes effect immediately. It doesn't, unconditionally: a
write issued from inside a running system is staged and only merged once
every system scheduled for that step has finished, so a *second* system
in the same step can already see it, but the *same* call that just made
the write cannot read it back synchronously. That's an ordinary property
of this ECS, not a bug in it — every other caller of
``framer_shader_get_default()`` had always been either the very first
mesh or sprite draw of an existing scene, where something upstream
(loading a level, spawning a player) had already asked for a shader on
some earlier frame, so the singleton already existed by the time this
function's fast path ran.

The ``SpriteBatch`` draw system is the first thing in a brand-new scene
that has *nothing* upstream of it — no mesh, no plain sprite entity, just
a bullet pool's one entity. On that scene's very first frame, its render
system is the very first caller of ``framer_shader_get_default()`` ever,
from inside a system, in a world where nothing has asked before. The
write lands; the read-back in the same call finds nothing; the function
returns 0; that frame renders every batch element with no shader bound at
all. The fix doesn't touch the ECS's timing at all, because there's
nothing wrong with it — it stops asking the world to hand back something
it was just told, seconds from now, to go store:

.. code-block:: c

    struct shader created = {.sprite_shader = sprite, /* ... */};

    framer_component_set(world, FRAMER_ID(Shader), FRAMER_ID(Shader), &created);
    return shader_of_type(&created, type);

Bug 3 (all three desktop backends): drawn correctly, in the wrong order
=====================================================================================

The first two bugs were both "nothing drew." The third one was quieter:
every bullet drew, at the right position, the right size, the right
texture — and the entity that fired them disappeared behind its own
bullets the moment enough of them piled up at its position.

``SpriteBatch`` and the ordinary per-entity ``Sprite`` draw are two
separate systems in the same ECS phase, and nothing had ever said which
one goes first. On GBA and NDS this was never a question worth asking,
because the hardware answers it structurally: OAM sprites carry an
explicit priority value, and entity sprites are deliberately drawn at a
higher priority than batch elements, so an entity is in front of a batch
by construction, regardless of which system happened to run first that
frame. Sampling the actual OAM contents through mGBA's debug stub, mid-run,
confirms it — the emitter (the round blue sprite at the center) sits
visibly in front of the spiral of bullets it just fired:

.. figure:: {static}/static/images/one-entity-many-bullets-sprite-batch-ecs/gba-oam-emitter-in-front.png
   :alt: The bullets example running under mGBA, OAM contents captured over its debug stub -- a blue emitter sprite is clearly visible on top of a spiral of orange bullet sprites radiating from it
   :align: center

   The bullets example's spiral pattern, OAM contents read directly off a
   running GBA — the emitter draws in front of every bullet it fires, by
   hardware priority, regardless of draw order.

The three desktop backends (OpenGL, Vulkan, software) have no equivalent
hardware guarantee — draw order *is* the only ordering mechanism they
have — and the two systems simply registered in whatever order their
import code happened to call them, which put ``SpriteBatch`` after the
entity sprite system. Sampling actual framebuffer pixels at the emitter's
screen position, once every fifty frames of a real Vulkan run, shows
exactly the moment it stops working: the emitter's own blue for hundreds
of frames, then — once the bullet pool has enough live bullets to reach
that exact pixel — the pixel starts reading back as whatever bullet is
currently passing through it instead:

.. code-block:: text

    frame  350: 2850c8 5a96ff 5a96ff 5a96ff 2850c8   (emitter blue)
    frame  750: 2850c8 5a96ff 5a96ff 5a96ff 2850c8   (emitter blue)
    frame  800: c81e28 ff7828 ffdc50 ff7828 c81e28   (bullet red/orange)
    frame 1200: c81e28 ffdc50 fffff0 ff7828 c81e28   (bullet, still)

The fix is the same one line of intent, spelled out explicitly instead of
left to registration order, on every desktop backend:

.. code-block:: c

    static const struct framer_system_dep batch_deps[] = {
        {.before = "sprite_render_system", .after = NULL}};

    framer_system_register(world, "sprite_batch_render_system",
                            FRAMER_PHASE_ON_UPDATE,
                            sprite_batch_render_system, bq, batch_deps, 1);

A new renderer test pins this down the same way the fix does — a red
entity sprite and a white batch element occupying the same pixels, one
assertion that the pixel reads back red — so the ordering is now a
property the test suite checks rather than an accident of import order.

Verification: one bug per backend, so one check per backend
==================================================================

Nothing about the design change itself is backend-specific, so the actual
proof that the redesign works had to be, backend by backend, rather than
inferred from any one of them: the desktop pixel-readback tests
(software, OpenGL, Vulkan) each got their own pass through the same three
scenes, ``examples/bullets`` was cross-compiled for both GBA and NDS and
the resulting ROM's OAM contents were sampled through mGBA's debug stub —
the same technique the `previous dithering article <dither-article_>`_
used to catch its own hardware-only bug — and every GBA example ROM in
the tree was booted headlessly to confirm the pooled component-storage
change underneath all of this (a separate, smaller fix the redesign also
needed, since one more component pushed the fixed-stride storage layout
past EWRAM) didn't regress startup on anything else.

One number came out the same on every target it was checked on, which
wasn't the point of the exercise but is a reassuring sign the redesign is
actually target-neutral: with the pool's rotating spiral pattern running
continuously, the live bullet count settles in roughly the high 90s on
GBA, OpenGL and Vulkan alike, all three converging on the same rough
capacity for the same pattern despite three completely different drawing
paths underneath.

Where this goes next
=========================

``FRAMER_STATIC_MAX_COMPONENTS`` (40) and ``FRAMER_STATIC_MAX_ENTITIES``
(104, leaving 64 for actual game use) both grew slightly to make room for
the new component without pushing the pooled storage past EWRAM on GBA —
a two-line configuration change today, in a codebase where each of those
numbers has moved before and will again. The bullet-pool roadmap item
itself narrows to what's left once "draws correctly, everywhere" is no
longer the open question: measuring and documenting the actual per-target
bullet ceiling, rather than the two capacity constants
(``examples/bullets`` currently uses 128 on GBA/NDS, 1024 on desktop)
picked ahead of having real numbers to size them against.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
.. _dither-article: https://tprrt.tupi.fr/gba-dither-offset-separation.html
