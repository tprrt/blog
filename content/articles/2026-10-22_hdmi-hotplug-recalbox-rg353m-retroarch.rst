==========================================================================
Plugging a Mini-HDMI into a Running Game: Six Wrong Turns on an RG353M
==========================================================================

:date: 2026-10-22 23:00
:tags: recalbox, retroarch, kms, drm, rockchip, buildroot, embedded, linux, retro, article
:category: Embedded
:slug: hdmi-hotplug-recalbox-rg353m-retroarch
:authors: tperrot
:summary: On an Anbernic RG353M running Recalbox, a game started after
    plugging the mini-HDMI cable exited at once, the panel stayed black
    after unplugging it, and every display change took 25 seconds. Each
    symptom had a cause other than the one I first blamed: a missing DRM
    encoder, a stale binary in a Buildroot per-package directory, a
    kernel race on shared VOP2 registers, a frontend never rebuilt, and a
    thread sleeping for 30 seconds.
:lang: en
:status: published

Introduction
============

The Anbernic RG353M is a handheld built around a Rockchip RK3568, with a
640x480 DSI panel and a mini-HDMI connector. Recalbox runs on it, and
until now the HDMI output only half worked: plug the cable before
powering on and the menu appears on the TV, but plug it afterwards and
nothing follows. This article is about making the menu, the boot video,
and above all a *running game* follow the cable, in both directions.

The fix came as a merge request on the Recalbox side and a few patches
on RetroArch's KMS context. It took six detours to get there. In every one
of them the first explanation was wrong, and what told me so was a log
line or a file date, not intuition.

The setup, for reference:

* Recalbox, a Buildroot external tree, target ``rg353x``, Linux 6.16.5;
* RetroArch 1.22.2, plus a stack of local patches;
* the Recalbox frontend, an EmulationStation fork, drawing through SDL's
  KMSDRM backend;
* two connectors: ``DSI-1`` (the panel) and ``HDMI-A-1``.

A note on method: I build in a rootless Podman container, flash an SD
card, test on the real device and paste the logs back. A cycle takes
several minutes, so each wrong guess is expensive, and that shaped how
this went.

Wrong turn 1: the game that exits right away
============================================

The first piece was easy. The frontend reads
``/sys/class/drm/card*-HDMI-A-*/status`` every half second, waits for
three identical reads (about 1.5 s) to ignore a sink that bounces while
the link comes up, and then relaunches itself. SDL's KMSDRM backend picks
its connector once, at init, so a new process is the simplest way to
follow the cable. After that, the menu showed up on the TV.

Then I started a game on the TV and it quit immediately, back to the
menu. RetroArch's log had the reason:

.. code-block:: text

    [WARN] [DRM] Couldn't find DRM encoder.

RetroArch's KMS context looks for the encoder the selected connector is
currently using. When the board boots without a cable, ``HDMI-A-1`` has
no encoder at all, because nothing ever drove it. Plugged in later, the
connector is connected but has none, and the context gives up.

The fix is what a modeset does anyway: take one of the connector's
possible encoders, and a CRTC that is off, falling back to a lit one only
when none is free. A second small fix goes with it. RetroArch asks for the
size the game was started with, 640x480 on the panel; the TV has no such
mode, and the start failed again. Falling back to the display's first mode
costs nothing.

Wrong turn 2: the patch that never reached the image
====================================================

I added the patch, rebuilt, flashed. The same error. The RetroArch log
printed its build date:

.. code-block:: text

    [INFO] Built: Oct 20 2026

Two days old. The patch was in the source tree, the package had been
rebuilt, and the image still had the old binary.

Recalbox builds with ``BR2_PER_PACKAGE_DIRECTORIES=y``. Each package gets
its own copy of the target tree, assembled from its dependencies. Three
packages that depend on ``retroarch`` (``retroarch-assets``,
``libretro-holani`` and ``libretro-mojozork``) carried their own copy of
the *old* ``/usr/bin/retroarch``, and when the final tree is put
together theirs won. Rebuilding only the dependency leaves the stale files
in the dependents.

The fix is to clean the dependents too, and the check is cheap: the
``Built:`` line, or ``strings`` on the binary in ``output/target``. I
should have looked at that line before touching the code. It is the first
thing I do now.

Wrong turn 3: restarting everything just to change the screen
=============================================================

With games starting on the TV, I wanted the next step: plug or unplug
the cable *during* a game and have the game move. RetroArch already
knows how to restart its video driver; what it lacked was a reason to do
it.

The context polls the connectors once a second from ``check_window``, and
asks for a restart when the monitor index would now pick another display.
Three details made it behave:

* **Debounce:** a restart only on two identical polls in a row, as with
  the frontend side;
* **A loop guard:** a connector already tried is not requested again, so
  a display with no usable mode cannot cause an endless restart;
* **Where it runs:** the poll runs on the video thread, which cannot
  restart itself. It sets a flag, and the main loop does the restart.

It worked. The log showed the connector change four times in one game,
HDMI to panel to HDMI to panel, and the game kept running. But the sound
cut at each switch. The reason was one argument:
``command_event(CMD_EVENT_REINIT, NULL)`` restarts *all* the drivers,
audio included, and I had also suspended audio explicitly around it.
Passing a mask of video, input and menu was enough. In the next log
``Started synchronous audio driver`` appears once for the whole game, not
once per switch.

Wrong turn 4: the panel that stayed black
=========================================

This one cost the most. Boot with the cable plugged, unplug it, and the
frontend relaunches on the panel (``Trying Resolution: 640,480``), but the
panel stays black. The backlight reads 128. The DRM state, dumped from
debugfs, is identical to the working case. Stopping the frontend does not
bring the console back either, so the panel is not being scanned out
whatever userspace does.

I proposed three explanations to myself and had to retract all of them:

* the date of ``/dev/dri/card0`` looked like the device had been recreated.
  It is the *last access* time;
* the plane assignment looked different. The working case had the same one;
* the Dim screensaver sets brightness to a smaller step, and brightness 8
  fits ``(7 >> 1) = 3`` then ``1 << 3``. It was not the cause here, since
  the backlight read 128 with a black panel.

What finally gave a direction was a line in ``dmesg``, present on every
boot with the cable plugged, around the start of fbdev:

.. code-block:: text

    rockchip-vop2 fe040000.vop: [drm:rk3568_vop2_setup_overlay] *ERROR*
        wait layer cfg done timeout: 0x54760213--0x54762013

On the RK3568 the VOP2 has several video ports sharing the layer and port
select registers, and those registers are latched by the vsync of *one*
of the ports. The 6.16.5 code waits for the wrong value, and switches the
vsync source before the previous latch happened. With two ports started
together, HDMI and DSI at boot, the configuration of one of them may
never be applied.

Four upstream commits fix this, the last two merged in June 2026. I took
them unchanged as kernel patches, in order, so that together they give
the upstream ``rk3568_vop2_setup_layer_mixer()``. After flashing, the
error is gone from ``dmesg`` and the panel comes back after an unplug.

I want to be honest about what this proves. The link between that error
and the black panel is a hypothesis that survived the one test I could
run; an earlier boot logged the same error and the panel had worked. The
patches are correct on their own merits, and the symptom went away. I
cannot yet say that one caused the other.

Wrong turn 5: a panel that was "on" at brightness 0
===================================================

Next, a game on HDMI, then unplug. RetroArch switched to the panel
(``Connector 54 is now the display to use``), the DSI link was enabled
and connected, and the panel was black again:

.. code-block:: text

    # cat /sys/class/backlight/backlight/brightness
    0
    # cat /sys/class/drm/card0-DSI-1/enabled /sys/class/drm/card0-DSI-1/status
    enabled
    connected

Brightness zero, with the video path fine. The frontend keeps the panel
dark while HDMI is in use, and a commit I had written was supposed to
restore it on unplug. The code looked right. So I compared the file the
build had compiled with the one in the source tree:

.. code-block:: text

    build/.../es-app/src/MainRunner.cpp   2026-10-21 13:03
    projects/frontend/es-app/src/MainRunner.cpp   2026-10-21 21:06

The frontend is a Buildroot package with ``SITE_METHOD = local``. It is
copied into the build directory once, and a plain ``make`` never copies
it again. My advice to rebuild with a plain ``make`` was wrong for this
package; it needs ``recalbox-emulationstation2-rebuild``, which clears
the rsync stamp. A ``diff -r`` of the two trees, which must print
nothing, is now part of my pre-flash checklist.

Wrong turn 6: a relaunch that took 25 seconds
=============================================

With everything working, the one thing that felt wrong was time. Unplug
in the menu and the screen stayed blank for ten to twenty seconds. The
detection is instant (two lines in the log). What was slow was the
frontend quitting.

The log of the quit gave the answer, once I looked at the *gaps* instead
of the messages. The unplug came at 12:14:42, about eleven seconds after
the frontend had started. The Hasher thread, which computes ROM hashes,
exited at 12:15:01, about thirty seconds after that start, while every
other thread had stopped within a couple of seconds.

.. code-block:: cpp

    // Initial delay
    Thread::Sleep(30 * 1000);

The hasher waits thirty seconds before starting its work, and that sleep
cannot be interrupted. Quitting inside that window waits for the end of
it. Other threads had the same shape: the netplay and command threads
sleep five seconds at the start, and the file watcher and others one
second per loop. Together they made up the five seconds of teardown I
could see even when the hasher was idle.

The fix is small: a ``Thread::SleepWhileRunning(ms)`` that sleeps in steps
of at most 50 ms and returns as soon as the thread is stopped, used in
those loops. The order of the sleeps is unchanged, only the exit is
faster. One detail worth a sentence: ``Thread.h`` has Windows line endings
in the repository, and my first scripted edit silently converted the whole
file. The diff stat (240 lines for a 14-line change) caught it before the
commit.

Epilogue: upstream got there first
===================================

When I went to rebase the RetroArch branch on the current master, the
first commit conflicted. Upstream had landed, that morning, its own
version of the same work: a free CRTC for a display nothing had set up,
a fallback to the first mode, and a udev-based hotplug watch that
restarts the video driver when the display in use goes away. Two of those
commits credit me as co-author.

I had not looked at upstream between writing the patches and rebasing
them, and that is the lesson I take from this: check what is already on
master *before* the third commit, not after the fifth.

The upstream behaviour has one gap for my use case. If the panel is in
use and HDMI is plugged in, the output stays where it is: the restart
only happens when the display in use is lost. The change I could add on
top is four lines: with the default monitor index, a display that now
ranks *before* the one in use takes over, and an index set by the user
is left alone. It has a unit test, and it worked on the board, but it
needs a newer RetroArch than 1.22.2. Recalbox keeps its three patches for
now.

A smaller lesson on the way. One of my patches had an all-zero ``From``
line, which I had written by hand when porting it to the 1.22.2 tree. It
looked harmless and it was not valid. The right way is to apply the
patch on a real branch of the upstream repository at the target tag,
commit, and regenerate the file with ``git format-patch``, so that the
commit ID, the date and the blob hashes are real.

What is left
============

* The frontend relaunch is still a whole process restart. The quit is
  fast now, but the init takes about eight seconds, two for the window
  and five and a half to load the systems, plus the time the TV needs to
  lock the HDMI link. An in-place display reinit, which another merge
  request on the Recalbox side proposes, would remove most of it.
* Only RetroArch cores follow a live switch. A standalone emulator keeps
  the display it picked until it exits.
* The audio output is not switched automatically, and it stops during a
  frontend relaunch.
* I decided against pausing the game during a switch. The restart already
  blocks it for about a second.

The work is in the `Recalbox merge request`_. Whether the black panel was
really the VOP2 race, I would like a second board to confirm.

.. _Recalbox merge request: https://gitlab.com/recalbox/recalbox/-/merge_requests/3764
