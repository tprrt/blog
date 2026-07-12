=====================================================================
No Heap, No Problem: a Static Micro-ECS for the Game Boy Advance
=====================================================================

:date: 2026-06-25 23:30
:modified: 2026-06-25 23:30
:tags: gba, ecs, embedded, retro, gamedev, c, article
:category: gamedev
:slug: static-ecs-no-heap-retro-platforms
:authors: tperrot
:summary: How framer-engine's Entity Component System works on hardware
    that has no operating system, no virtual memory, and no malloc(),
    plus two real bugs the design caught before they shipped.
:lang: en
:status: published

Introduction
============

The `previous article <gba-performance-article_>`_ on this blog was about
squeezing cycles out of framer-engine's GBA renderer. This one is about
something that has to be settled *before* any of that renderer work is
possible at all: how do you run an Entity Component System — the
architecture pattern the whole engine is built around — on a console with
32KB of fast RAM, 256KB of slow RAM, no operating system, and no
``malloc()`` you can lean on?

`framer-engine`_'s answer is a second, much smaller ECS implementation
living behind the same interface as the desktop one. Every game-logic
line — component definitions, systems, queries — is identical between a
PC build and a GBA build. Only one file differs: which ``world.c`` gets
linked in.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

Two ECS backends, one interface
=================================

framer-engine's default ECS backend is `Flecs`_, a full-featured ECS used
for desktop and handheld targets with a real OS underneath (PSP, 3DS,
Switch, PC). Flecs is excellent at what it does — archetypes, queries,
observers, relationships — but all of that bookkeeping assumes a working
heap it can grow and shrink as entities and component types come and go.
That's simply not available on a target like the GBA: 32KB of IWRAM,
256KB of EWRAM, both fixed-size and fully accounted for from the moment
the ROM boots, with no MMU and no OS to page anything in. There's no heap
to assume.

Rolling a second full-featured ECS to fit that budget wasn't the
answer either — that's a lot of complexity to maintain for a problem
that doesn't need it. What GBA-class scenes actually look like is a
handful of objects (`examples/simple_cube` uses one mesh and a camera;
`examples/spinning_shapes` uses three), not thousands, and the
component types are known and fixed at compile time, not user-extensible
at runtime. That's a much smaller problem than "general-purpose ECS,"
and ``src/ecs/static/world.c`` — about 550 lines of plain C — is sized to
match it instead of to match Flecs:

.. code-block:: c

    /* Entities */
    static bool s_alive[FRAMER_STATIC_MAX_ENTITIES];
    static uint64_t s_comp_mask[FRAMER_STATIC_MAX_ENTITIES];

    /* Component data store: row = component slot, column = entity slot.
     * Each entity slot is FRAMER_STATIC_MAX_COMPONENT_SIZE bytes wide. */
    static uint8_t s_store[FRAMER_STATIC_MAX_COMPONENTS]
                           [FRAMER_STATIC_MAX_ENTITIES *
                            FRAMER_STATIC_MAX_COMPONENT_SIZE];

Every one of those arrays is a fixed-size global, sized by compile-time
constants. There is no ``framer_entity_create()`` call anywhere in this
file that can fail by running out of memory in some unpredictable way —
it can only fail by running out of *array slots*, a number known before
the program even starts.

Both backends sit behind the exact same ``include/framer/ecs.h`` —
``framer_world_t``, ``framer_component_register()``, ``framer_query_create()``,
``framer_system_register()``, the ``FRAMER_GET``/``FRAMER_SET``/``FRAMER_FIELD``
macros. A component defined with ``FRAMER_COMPONENT_DEFINE(Velocity)`` and
a system registered with ``framer_system_register()`` compiles and runs
unchanged on either backend; which one a build gets is a single Meson
option, ``-Decs=flecs`` or ``-Decs=static``, and GBA's cross file pins it
to ``static`` (Flecs needs an OS, and bare-metal GBA doesn't have one) —
the build refuses to configure any other way for that target.

Entities are array slots, nothing more
========================================

An entity in this backend isn't an object — it's a 1-based index into
those parallel arrays. ``framer_entity_create()`` finds the lowest dead
slot and claims it, first-fit:

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

That's the entire allocator. No free list to maintain, no fragmentation
to worry about — there's nothing to fragment when every slot is the same
fixed size and lives at a compile-time-known address. The price for that
simplicity is explicit and deliberate: destroying entity 5 and creating a
new one immediately afterward hands back the same ID, 5, for a
completely different logical entity. There's no generation counter to
tell the two apart. For the scene sizes and lifetimes this backend
targets — a handful of objects that mostly live for the whole level, not
a churn of thousands spawning and despawning every frame — that's an
acceptable trade, not an oversight; it's directly covered by a unit test
(``test_entity_slot_recycled_first_fit``) precisely so it stays a known,
intentional property instead of a surprise.

Components: a bitmask and a flat array
=========================================

Each entity slot carries one ``uint64_t`` bitmask, one bit per registered
component type. ``framer_component_set()`` is a ``memcpy`` into a
fixed-stride row of the flat ``s_store`` array, plus a bit set:

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

A query is just a precomputed mask built from the component ids it asks
for; matching an entity against it is one ``AND`` and one comparison
(``(s_comp_mask[ei] & mask) == mask``). The ``uint64_t`` bitmask is also
the hard ceiling on how many distinct component *types* can exist in one
world — 64 — which is generous for a retro scene's needs but means the
type system itself enforces "don't try to build something Flecs-shaped
on top of this."

War story: a silent NULL deref vs. a loud abort()
====================================================

The single most important property of this backend isn't the data
layout — it's what happens when a limit is hit. Early on,
``framer_component_register()`` returned 0 when a component was too big
or the registry was full, the same "just signal failure" convention used
everywhere else in this API. That sounds reasonable until you trace what
a 0 component id actually does downstream: ``framer_query_create()``
silently skips it when building a query's mask, and the system that
registered that query goes on to call ``FRAMER_FIELD()`` for a field that
was quietly dropped — which dereferences NULL on the system's very next
matching entity. That's exactly what happened on a real GBA build: a
``Text`` component at 288 bytes against a 64-byte cap, and 17 registered
component types against a cap of 12. The crash that surfaced wasn't "your
component is too big," it was a NULL-pointer SIGSEGV deep inside a render
system, two layers removed from the actual mistake.

The fix removes the silent path entirely:

.. code-block:: c

    if (size > FRAMER_STATIC_MAX_COMPONENT_SIZE) {
        fprintf(stderr,
            "framer_component_register: \"%s\" is %lu bytes, "
            "exceeding FRAMER_STATIC_MAX_COMPONENT_SIZE (%d)\n",
            name ? name : "?", (unsigned long)size,
            (int)FRAMER_STATIC_MAX_COMPONENT_SIZE);
        abort();
    }

``abort()`` rather than an ``assert()`` or a GCC/Clang-specific builtin,
because this backend also has to compile under cc65 and SDCC for
8-bit targets — plain C89 ``abort()`` is the one failure primitive
guaranteed to exist everywhere this code runs. The test suite verifies
the *contract*, not just the arithmetic: ``test_ecs_static_limits.c``
forks a child process, registers one component past the limit inside it,
and asserts the child died of ``SIGABRT`` rather than returning normally
— proving the fail-loud path actually fires, not just that the size
check's math is correct.

The broader lesson generalizes past this one bug: on a backend built
entirely out of fixed-size arrays, every hard limit is a wall, not a
suggestion. The only choice that matters is whether you hit that wall
with a clear error message at the exact call site that caused it, or
with a corrupted query and a crash three function calls away. This
backend picked loud, on purpose, everywhere a hard cap exists.

Sizing the pools, and a second silent-failure bug
====================================================

Each target's ``meson.build`` picks ``FRAMER_STATIC_MAX_COMPONENTS``,
``FRAMER_STATIC_MAX_ENTITIES``, and ``FRAMER_STATIC_MAX_COMPONENT_SIZE``
to fit what that platform actually needs — there's no universal default
that's right for every target, because the engine registers its full set
of core components (``Transform``, ``Velocity``, ``Sprite``, ``Light``,
``Text``, ``Camera``, and so on — 19 today) unconditionally, regardless
of whether a given example actually uses all of them:

.. code-block:: text

    # Embedded (system == 'none'):
    -DFRAMER_STATIC_MAX_COMPONENTS=19
    -DFRAMER_STATIC_MAX_ENTITIES=96
    -DFRAMER_STATIC_MAX_COMPONENT_SIZE=64

That ``MAX_ENTITIES=96`` number has its own bug story behind it. Each
*registered component type* — not each entity actually created — reserves
one sentinel slot out of the same entity pool, so the entities actually
available to a scene is ``MAX_ENTITIES`` minus however many component
types exist. At ``MAX_ENTITIES=64`` and 19 components, that left 45 usable
slots — comfortably enough for `examples/simple_cube`, but one short of
`examples/input_tester`'s 48 (47 on-screen panel entities plus one
camera). The failure mode was, again, silent: ``framer_entity_create()``
returning 0 once the pool filled, and the caller that wanted one more
entity for a gamepad-axis label simply never got it — the text just never
appeared on screen, with nothing in the logs to say why. Raising the cap
to 96 (77 free after the 19 sentinels) fixed it with headroom to spare.
On the GBA build that growth costs about 544 bytes of IWRAM (three
per-entity arrays scale with the cap), which was checked against the
build's actual free IWRAM margin before landing — on a 32KB budget,
guessing isn't good enough, you measure.

That measurement habit is the same one from the performance article:
``arm-none-eabi-size -A`` on a current GBA build shows exactly where this
backend's memory actually goes. The flat component store
(19 × 96 × 64 bytes ≈ 114KB) is placed in EWRAM's ``.sbss`` section — too
big for IWRAM, and zero-initialized for free by the startup code without
costing any ROM space:

.. code-block:: c

    #ifdef GBA
    #define _FRAMER_STORE_ATTR __attribute__((section(".sbss")))
    #else
    #define _FRAMER_STORE_ATTR
    #endif

    static uint8_t _FRAMER_STORE_ATTR
        s_store[FRAMER_STATIC_MAX_COMPONENTS]
               [FRAMER_STATIC_MAX_ENTITIES * FRAMER_STATIC_MAX_COMPONENT_SIZE];

Everything else — the alive flags, the masks, the per-frame iterator's
entity list — is small enough to live in IWRAM, the GBA's fast 32KB
scratch memory, where the CPU actually wants its hot working data. On
the current ``examples/simple_cube`` build that's roughly 19.5KB of
IWRAM used out of 32KB, leaving real headroom for the next component or
two — a number worth checking again every time that count grows, the
same way the 96-entity fix had to be checked against it.

The scan loop, briefly
========================

``framer_world_progress()`` walks every registered system, in phase
order, and for each one scans entity slots up to the high-water mark
(``s_entity_high``, one past the highest slot any entity or component
sentinel has ever occupied) looking for bitmask matches. That scan, and
the sticky ``s_any_mask`` check that skips it entirely for systems whose
component type no entity has ever had, was the single biggest win in
the previous article's performance work — covered there in full, since
it's a perf story more than a design story. The design point that
matters here is simpler: this is a linear scan over a flat array, not a
sparse-set or archetype-table lookup. That's the right trade at GBA
scene sizes (tens of entities), and the wrong one at thousands — which is
exactly the line where you'd reach for Flecs instead.

What this design explicitly gives up
=======================================

None of the above is free, and being upfront about the trade-offs is the
point of having two backends instead of pretending one ECS fits every
target:

- **No entity generations.** As covered above, IDs are recycled
  immediately and look identical to the entity that previously held
  them.
- **No archetypes, no sparse sets.** Matching is a linear scan with a
  bitmask test, not a cache-optimized contiguous iteration over exactly
  the matching entities. Fine at dozens of entities; the wrong tool past
  that.
- **64 component types, total, forever, for the whole world.** Not per
  query — for every component type that exists anywhere in the engine,
  shared across every system. The engine's current 19 leaves room to
  grow, but a "just add a component" change always has a final cost
  attached: someone, somewhere, has to recheck that ceiling.
- **No relationships, no hierarchies, no observers.** Flecs has all of
  these; this backend has entities, components, and queries, deliberately
  nothing more.

Every one of these is a real capability Flecs has and this backend
doesn't. They're also exactly the features that cost the heap, the
dynamic bookkeeping, and the unpredictable-at-compile-time memory use
that a bare-metal ROM target can't afford. The two-tier split exists so
that trade only has to be made once, explicitly, per target — not
silently, by whichever ECS happened to compile.

Where this goes next
======================

The same problem — "no OS, no heap, fixed memory map, known component
set" — is true of every retro target on framer-engine's roadmap, not just
the GBA. The 32-bit-era consoles mentioned in the previous article's
closing section, starting with the PlayStation 1, sit in an interesting
middle ground: dramatically more RAM and a real GPU compared to the GBA,
but still no OS and still nothing resembling a desktop heap. The
expectation going in is that they'll want this same static backend, just
with much larger pool constants — not Flecs, and not a third ECS
implementation. Whether that expectation survives contact with an actual
PS1 build, the way the "obviously correct" tricks in the performance
article sometimes didn't survive contact with measurement, is exactly
the kind of thing a future article on this blog will have to report
honestly either way.

.. _framer-engine: https://github.com/tprrt/framer-engine
.. _Flecs: https://github.com/SanderMertens/flecs
.. _gba-performance-article: https://tprrt.tupi.fr/gba-performance-optimization-framer-engine.html
