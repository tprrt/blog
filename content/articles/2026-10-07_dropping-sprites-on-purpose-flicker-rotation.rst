==========================================================================
Dropping Sprites on Purpose: Flicker Rotation on GBA and NDS
==========================================================================

:date: 2026-10-07 22:10
:tags: sprites, oam, gba, nds, flicker, shmup, embedded, retro, gamedev, c, article
:category: gamedev
:slug: dropping-sprites-on-purpose-flicker-rotation
:authors: tperrot
:summary: The Game Boy Advance and the Nintendo DS can show 128 sprites at
    once, so a bullet pattern bigger than that has to lose some. Losing
    the same ones every frame makes them disappear for good; losing a
    different set each frame makes them flicker, which is what the
    consoles' own shoot-'em-ups did. Here is the small mechanism that does
    it, and the debugger sampling that checks it on both consoles.
:lang: en
:status: published

Introduction
============

The `article about bullet pools <sprite-batch-article_>`_ ended with a
number: on the Game Boy Advance, a pool of bullets stops being fully
visible at 121 of them, and on the Nintendo DS at 126. Both consoles have
128 hardware sprite entries (OAM), and a few of them always go to the
player, the target and the text. Past that number, the renderer runs out
of entries and has to stop drawing.

That raises the question the first article left open: *which* bullets stop
being drawn? The first answer the engine gave was the dull one, the last
ones in the array, and it was wrong for a reason that has nothing to do
with performance. This article is about the second answer, the cheaper
and older one, and about how to check on an emulator that it does what it
claims.

.. note::

   ``framer-engine`` is a personal side project. The source code will be
   made publicly available once the engine reaches a sufficient level of
   maturity.

The first answer: the same ones, every frame
============================================

A sprite batch is drawn in array order, and the loop stops as soon as there
is no OAM entry left. With 200 bullets and room for 121, the same 79
bullets, the ones at the end of the pool, are skipped in every frame. They
are not drawn late or drawn thin. They are never drawn, and for a bullet
that is a worse failure than it sounds: a bullet that is not drawn still
moves, and still hits the player. A pattern ends with the player dying to
something that was never on the screen.

The engine already had one tool for this, and it is the right one for
most of the problem: a priority per batch. A batch with a lower priority
number is drawn first and so gets its OAM entries first; the batches that
matter least lose theirs. On the GBA, two stationary pools of 100 bullets
that together overflow OAM behave as expected: the one created second but
given priority 0 kept all 100 of its sprites, and the one created first,
with priority 200, kept 22.

.. code-block:: c

    /* The enemy's bullets decide whether the player lives. */
    framer_sprite_batch_set_priority(world, enemy_pool, 0);
    /* The player's own shots and the sparks come after. */
    framer_sprite_batch_set_priority(world, shot_pool, 200);

Priority decides *between* batches. It says nothing about what happens
inside the one that does not fit, and the pool that loses is still cut
off at the same element every frame.

The second answer: start where you stopped
==========================================

The consoles' own games had this problem first. A Famicom can draw eight
sprites on a scanline and sixty-four in all, and the shoot-'em-ups of that
era did not pretend otherwise: when a boss made of many segments crossed a
line, some of its sprites were missing. The fix that players know as *flicker* is that the
missing ones are not the same ones from one frame to the next. Every
sprite is on screen on some frames, none is gone for good, and at 60
frames a second the eye reads a dim, busy sprite rather than a hole.
`Recca <https://en.wikipedia.org/wiki/Recca>`_ is the example people
remember. The hardware did not do this; the games did, by rotating the
order they wrote their sprites in.

The same rotation fits a batch in a few lines. Each frame, a batch that
has opted in starts drawing at the element where the previous frame
stopped, and wraps around to the front when it reaches the end:

.. code-block:: c

    int n = framer_sprite_batch_count(batch);
    int start = framer_sprite_batch_start(batch);

    for (k = 0; k < n; k++) {
        i = start + k < n ? start + k : start + k - n;
        q = framer_sprite_batch_get(batch, i);

        if (s_next_oam_slot >= GBA_OAM_HW_SLOT_COUNT) {
            framer_sprite_batch_resume_at(batch, i);
            return;
        }
        /* ... write the OAM entry for q ... */
    }
    framer_sprite_batch_resume_at(batch, 0);

When the whole batch fits, the loop finishes, the resume point goes back to
zero and nothing rotates. When it does not fit, the element that was
refused is the one the next frame starts with. The first frame draws
elements 0 to 120 of 200, the second draws 121 to 199 and then 0 to 41, the
third starts at 42, and so on. Every element is drawn about 60% of the
frames, and which ones are missing keeps moving.

Where the index lives
---------------------

The resume index has to survive from one frame to the next, and the
obvious place, a field of the batch's own component, does not work: a render
system is handed a copy of the component, so a write to it is lost. A
second component would work, but the static ECS this engine runs on GBA and
NDS has a fixed table of components, and on the GBA that table is nearly
full (the
`article about it <static-ecs-article_>`_ explains the budget). So the
index sits in a small table in ``sprite_batch.c``, keyed by the address of
the batch's elements and sized for the sixteen batches a frame can draw. A
batch that does not find a slot is simply not remembered, and draws from
the front each frame, which is what a batch without flicker does anyway.
The only change to the component itself is one byte, the flag.

It is off by default, with one call to turn it on:

.. code-block:: c

    framer_sprite_batch_set_flicker(world, shot_pool, 1);

The desktop backends ignore it, since they have no OAM and draw everything.

Not for the enemy's bullets
---------------------------

Flicker is the right trade for effects, sparks and the player's own shots,
where a missing sprite on one frame costs nothing. It is the wrong one for
the bullets that can kill the player. A bullet that blinks is harder to
read than one that is steadily absent from a crowd, and at 60% visibility
it still hits on the frames it is invisible. Those bullets belong in a
batch that always fits, at the lowest priority number. That advice is
written next to the API in the engine's docs, because the mechanism makes it
easy to get wrong.

Checking it
===========

The claim to test is narrow: with flicker on, every bullet is drawn on some
frame, and with it off, the same bullets never are. Taking screenshots of
an emulator window does not show that, because a single screenshot looks
like any other, so the check reads the OAM instead.

The test program is the bullets example with a pool of 200 stationary
bullets laid out in a grid of 20 by 10, which never move. A script connects to the emulator's GDB stub, lets the program
run for a random fraction of a second, stops it, reads the 1 KB of OAM,
and picks out the bullets, which are the 8 by 8 sprites that share the most
common tile. It does that dozens of times and counts how many different
positions it ever saw.

On the GBA, in mGBA, with room for 121:

.. list-table::
   :header-rows: 1

   * - Flicker
     - Samples
     - Bullets drawn per sample
     - Distinct positions ever drawn
   * - off
     - 60
     - 121 to 128
     - 122
   * - on
     - 60
     - 121
     - 200

The "off" row is noisier than it should be: the per-sample count ran up to
128 and 122 positions were seen, where 121 is the most that fits. I did not
track down the difference. It is small next to 122 against 200, but it means
the sampler is not exact on the GBA.

On the DS, in melonDS 1.1, with room for 126, the program toggles the flag
itself every 180 frames, so one launch gives both rows, and the script
reads the current flag from a global at each stop:

.. list-table::
   :header-rows: 1

   * - Flicker
     - Samples
     - Bullets drawn per sample
     - Distinct positions ever drawn
   * - off
     - 82
     - 126
     - 126
   * - on
     - 78
     - 126
     - 200

In both cases the number drawn at any one moment does not change. Flicker
does not draw more sprites; it changes which ones. The figure below puts
the samples on the grid they were laid out in: three samples for each
setting from a GBA run, taken a second or so apart (the positions come from
the OAM dumps, mapped back onto the 20 by 10 layout):

.. figure:: {static}/static/images/dropping-sprites-on-purpose-flicker-rotation/gba-oam-drawn-and-dropped.png
   :alt: Two rows of three 20 by 10 grids of dots. In the top row, labelled flicker off, the same rows of dots are filled in all three samples and the top three and a half rows are always empty. In the bottom row, labelled flicker on, a different block of dots is empty in each of the three samples.
   :align: center

   Filled dots are bullets present in OAM, hollow ones are bullets that were
   not drawn. With flicker off, the same 79 are missing in every sample.
   With it on, the gap moves.

The method has the limits of an emulator: melonDS and mGBA are not a
console, and none of this has been run on hardware. The per-scanline limits
were not checked at all.

What is left
============

The rotation only deals with the whole-OAM limit, the 128 entries. Both
consoles also limit how many sprites can be on one scanline, and that
limit can be hit by a wide row of bullets before the 128 total is, so it is
the next thing to check. Two other items sit next to it in the roadmap: a way to report how
many sprites a frame used, so a game can see its budget without a
debugger, and a priority for single sprite entities and text, which today
are always drawn before every batch.

.. _sprite-batch-article: https://tprrt.tupi.fr/one-entity-many-bullets-sprite-batch-ecs.html
.. _static-ecs-article: https://tprrt.tupi.fr/static-ecs-no-heap-retro-platforms.html
