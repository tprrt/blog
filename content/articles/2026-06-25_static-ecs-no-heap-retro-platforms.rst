=====================================================================
A Static Micro-ECS for the Game Boy Advance
=====================================================================

:date: 2026-06-25 23:30
:modified: 2026-06-25 23:30
:tags: gba, ecs, embedded, retro, gamedev, c, article
:category: gamedev
:slug: static-ecs-no-heap-retro-platforms
:authors: tperrot
:summary: How framer-engine's Entity Component System works on hardware
    with no operating system, no virtual memory and no malloc(), and two
    bugs the design caught before they shipped.
:lang: en
:status: published

Introduction
============

The `previous article <gba-performance-article_>`_ was about squeezing cycles
out of framer-engine's GBA renderer. This one covers what has to be settled
before that work is possible: how to run an Entity Component System, the
pattern the engine is built around, on a console with 32KB of fast RAM, 256KB
of slow RAM, no operating system and no usable ``malloc()``.

`framer-engine`_ answers with a second, much smaller ECS implementation behind
the same interface as the desktop one. Component definitions, systems and
queries are identical between a PC build and a GBA build. Only one file
differs: which ``world.c`` is linked.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

Two ECS backends, one interface
=================================

The default backend is `Flecs`_, a full-featured ECS used for desktop and
handheld targets with a real OS (PSP, 3DS, Switch, PC). It provides archetypes,
queries, observers and relationships, and all of that bookkeeping assumes a
heap that grows and shrinks as entities and component types come and go. The
GBA has 32KB of IWRAM and 256KB of EWRAM, both fixed-size and fully accounted
for from boot, with no MMU and no OS to page anything in. There is no heap.

A second full-featured ECS sized to that budget would be a lot to maintain for
a problem that does not need it. GBA-class scenes hold a handful of objects
(`examples/simple_cube` uses one mesh and a camera, `examples/spinning_shapes`
three), not thousands, and the component types are fixed at compile time.
``src/ecs/static/world.c``, about 550 lines of plain C, is sized to that
instead of to Flecs:

.. code-block:: c

    /* Entities */
    static bool s_alive[FRAMER_STATIC_MAX_ENTITIES];
    static uint64_t s_comp_mask[FRAMER_STATIC_MAX_ENTITIES];

    /* Component data store: row = component slot, column = entity slot.
     * Each entity slot is FRAMER_STATIC_MAX_COMPONENT_SIZE bytes wide. */
    static uint8_t s_store[FRAMER_STATIC_MAX_COMPONENTS]
                           [FRAMER_STATIC_MAX_ENTITIES *
                            FRAMER_STATIC_MAX_COMPONENT_SIZE];

Every array is a fixed-size global sized by compile-time constants. Nothing in
this file can fail by running out of memory unpredictably. It can only run out
of *array slots*, a number known before the program starts.

Both backends sit behind the same ``include/framer/ecs.h``: ``framer_world_t``,
``framer_component_register()``, ``framer_query_create()``,
``framer_system_register()`` and the ``FRAMER_GET``/``FRAMER_SET``/
``FRAMER_FIELD`` macros. A component defined with
``FRAMER_COMPONENT_DEFINE(Velocity)`` and a system registered with
``framer_system_register()`` compile and run unchanged on either. A single Meson
option selects the backend, ``-Decs=flecs`` or ``-Decs=static``. GBA's cross
file pins it to ``static`` because Flecs needs an OS, and the build refuses to
configure otherwise.

Entities are array slots
========================================

An entity here is a 1-based index into those parallel arrays.
``framer_entity_create()`` claims the lowest dead slot, first-fit:

.. code-block:: c

    framer_entity_t framer_entity_create(framer_world_t *world)
    {
        int i;

        for (i = 0; i < FRAMER_STATIC_MAX_ENTITIES; i++) {
            if (!s_alive[i]) {
                s_alive[i] = true;
                s_comp_mask[i] = 0;
                if (i + 1 > s_entity_high)
                    s_entity_high = i + 1;
                return EID(i);
            }
        }
        return 0; /* pool exhausted */
    }

That is the whole allocator. There is no free list and no fragmentation, since
every slot has the same size and a compile-time address. The price is
deliberate: destroying entity 5 and creating a new one immediately returns ID
5 for a different logical entity, and there is no generation counter to tell
them apart. For a handful of objects that mostly live for a whole level, that
is acceptable. ``test_entity_slot_recycled_first_fit`` pins it down so it
stays a known property.

Components: a bitmask and a flat array
=========================================

Each entity slot carries one ``uint64_t`` bitmask with one bit per registered
component type. ``framer_component_set()`` is a ``memcpy`` into a fixed-stride
row of ``s_store`` plus a bit set:

.. code-block:: c

    void framer_component_set(framer_world_t *world, framer_entity_t e,
                              framer_id_t id, const void *data)
    {
        int ei = EIDX(e);
        int ci = cidx(id);
        /* ...bounds and liveness checks elided... */
        memcpy(&s_store[ci][ei * FRAMER_STATIC_MAX_COMPONENT_SIZE], data,
               s_comp[ci].size);
        s_comp_mask[ei] |= ((uint64_t)1u << ci);
        s_any_mask |= ((uint64_t)1u << ci);
    }

A query is a precomputed mask built from the component ids it asks for, and
matching an entity is one ``AND`` and one comparison
(``(s_comp_mask[ei] & mask) == mask``). The ``uint64_t`` is also the ceiling on
distinct component *types* in a world: 64. That is plenty for a retro scene,
and it stops anyone building something Flecs-shaped on top.

A silent NULL deref vs. a loud abort()
====================================================

The most important property of this backend is what happens when a limit is
hit. ``framer_component_register()`` originally returned 0 when a component
was too big or the registry was full, like the rest of the API. A 0 component
id then does damage downstream: ``framer_query_create()`` skips it when
building the mask, and the system that registered the query calls
``FRAMER_FIELD()`` on a field that was dropped, dereferencing NULL on its next
matching entity. This happened on a real GBA build: a ``Text`` component of 288
bytes against a 64-byte cap, and 17 component types against a cap of 12. The
crash was a NULL-pointer SIGSEGV inside a render system, two layers away from
the mistake, not "your component is too big".

The fix removes the silent path:

.. code-block:: c

    if (size > FRAMER_STATIC_MAX_COMPONENT_SIZE) {
        fprintf(stderr,
            "framer_component_register: \"%s\" is %lu bytes, "
            "exceeding FRAMER_STATIC_MAX_COMPONENT_SIZE (%d)\n",
            name ? name : "?", (unsigned long)size,
            (int)FRAMER_STATIC_MAX_COMPONENT_SIZE);
        abort();
    }

It uses ``abort()`` instead of ``assert()`` or a GCC/Clang builtin because this
backend also has to compile under cc65 and SDCC for 8-bit targets, and C89
``abort()`` is the one failure primitive guaranteed everywhere. The tests check
the contract, not just the arithmetic: ``test_ecs_static_limits.c`` forks a
child, registers one component past the limit, and asserts the child died of
``SIGABRT``. That proves the fail-loud path fires.

On a backend made of fixed-size arrays, every hard limit is a wall. The choice
is hitting it with a clear message at the offending call, or with a corrupted
query and a crash three calls away. This backend fails loudly wherever a hard
cap exists.

Sizing the pools, and a second silent-failure bug
====================================================

Each target's ``meson.build`` picks ``FRAMER_STATIC_MAX_COMPONENTS``,
``FRAMER_STATIC_MAX_ENTITIES`` and ``FRAMER_STATIC_MAX_COMPONENT_SIZE`` for
that platform. No universal default fits, because the engine registers its full
set of core components (``Transform``, ``Velocity``, ``Sprite``, ``Light``,
``Text``, ``Camera`` and so on, 19 today) regardless of what an example uses:

.. code-block:: text

    # Embedded (system == 'none'):
    -DFRAMER_STATIC_MAX_COMPONENTS=19
    -DFRAMER_STATIC_MAX_ENTITIES=96
    -DFRAMER_STATIC_MAX_COMPONENT_SIZE=64

``MAX_ENTITIES=96`` has its own bug behind it. Each *registered component type*,
not each entity created, reserves one sentinel slot from the same entity pool,
so the entities available to a scene are ``MAX_ENTITIES`` minus the number of
component types. At ``MAX_ENTITIES=64`` and 19 components that left 45 usable
slots, enough for `examples/simple_cube` but one short of
`examples/input_tester`'s 48 (47 on-screen panel entities plus a camera). The
failure was silent again: ``framer_entity_create()`` returned 0 once the pool
filled, and the caller wanting one more entity for a gamepad-axis label never
got it. The text did not appear and nothing in the logs said why. Raising the
cap to 96 (77 free after the 19 sentinels) fixed it. On GBA that costs about
544 bytes of IWRAM (three per-entity arrays scale with the cap), which I
checked against the build's free IWRAM margin before landing. On a 32KB budget
you measure.

As in the performance article, ``arm-none-eabi-size -A`` on a current GBA build
shows where this backend's memory goes. The flat component store
(19 × 96 × 64 bytes ≈ 114KB) goes in EWRAM's ``.sbss`` section: too big for
IWRAM, and zero-initialized by the startup code at no ROM cost:

.. code-block:: c

    #ifdef GBA
    #define _FRAMER_STORE_ATTR __attribute__((section(".sbss")))
    #else
    #define _FRAMER_STORE_ATTR
    #endif

    static uint8_t _FRAMER_STORE_ATTR
        s_store[FRAMER_STATIC_MAX_COMPONENTS]
               [FRAMER_STATIC_MAX_ENTITIES * FRAMER_STATIC_MAX_COMPONENT_SIZE];

Everything else (alive flags, masks, the per-frame iterator's entity list) is
small enough for IWRAM, the GBA's fast 32KB memory, where the CPU wants its
hot data. On the current ``examples/simple_cube`` build that is roughly 19.5KB
of 32KB used. That leaves room for a component or two, and the number needs
rechecking whenever the component count grows, as the 96-entity change did.

The scan loop
========================

``framer_world_progress()`` walks every registered system in phase order and,
for each, scans entity slots up to the high-water mark (``s_entity_high``, one
past the highest slot any entity or component sentinel has occupied) looking
for bitmask matches. The sticky ``s_any_mask`` check skips the scan entirely
for systems whose component type no entity has ever had. That was the biggest
win in the previous article's performance work, covered there. The design point
here is that this is a linear scan over a flat array, not a sparse-set or
archetype lookup. That is right at GBA scene sizes (tens of entities) and wrong
at thousands, where you would reach for Flecs.

What this design gives up
=======================================

Two backends exist so that these trade-offs are made once, explicitly, per
target:

- **No entity generations.** IDs are recycled immediately and look identical
  to the entity that held them before.
- **No archetypes, no sparse sets.** Matching is a linear scan with a bitmask
  test, not a cache-friendly iteration over exactly the matching entities.
  Fine at dozens of entities, wrong past that.
- **64 component types in total, for the whole world.** Not per query: every
  component type in the engine, shared across every system. The current 19
  leaves room, but adding a component means someone must recheck that ceiling.
- **No relationships, hierarchies or observers.** Flecs has all three. This
  backend has entities, components and queries.

Flecs has these capabilities and this backend does not, and they are the
features that cost a heap, dynamic bookkeeping and memory use unknowable at
compile time, none of which a bare-metal ROM can afford.

Where this goes next
======================================

Every retro target on the roadmap has the same constraints: no OS, no heap, a
fixed memory map and a known component set. The 32-bit-era consoles mentioned
at the end of the previous article, starting with the PlayStation 1, have far
more RAM and a real GPU but still no OS and no desktop heap. I expect them to
use this static backend with much larger pool constants, not Flecs and not a
third ECS. Whether that holds on a real PS1 build is for a later article.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _Flecs: https://github.com/SanderMertens/flecs
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
