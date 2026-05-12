===========================================
Open-Source Game Engines for Retro Consoles
===========================================

:date: 2025-12-31 10:00
:modified: 2025-12-31 10:00
:tags: gamedev, retro, homebrew, console, open-source, article
:category: gamedev
:slug: retro-console-game-engines
:authors: tperrot
:summary: A guide to modern open-source game engines and frameworks for
    developing games on classic consoles from 8-bit to sixth generation, all
    compatible with Linux.
:lang: en
:status: published

Introduction
============

Homebrew communities now maintain open-source SDKs for most classic consoles,
and a Linux machine is enough to build for them. This is a catalogue of the
engines and frameworks I know of, from the 8-bit Game Boy Color to sixth
generation systems like the PlayStation 2. All of them work on Linux.

.. contents:: Table of Contents
   :depth: 2

8-bit and 16-bit Consoles
=========================

Game Boy Color (GBC)
--------------------

GB Studio
~~~~~~~~~

**GB Studio** is a visual game editor for making Game Boy games without
writing code. Its drag-and-drop interface covers RPGs, adventure games,
platformers and shooters.

**Key Features:**

- Visual scene editor
- Built-in sprite and background editors
- Integrated music tracker
- Event system for complex game logic
- Exports to actual GB/GBC ROMs that run on real hardware
- Cross-platform support (Linux, Windows, macOS)

**License:** MIT

**Links:** `GitHub <https://github.com/chrismaltby/gb-studio>`_ |
`Website <https://www.gbstudio.dev/>`_ |
`Documentation <https://www.gbstudio.dev/docs/>`_

GBDK-2020
~~~~~~~~~

**GBDK-2020** is a fork of the Game Boy Development Kit that adds C99
support and a newer toolchain.

**Key Features:**

- C99 compiler
- ROM banking support for large games
- Libraries for sprites, backgrounds, and sound
- Compatible with both Game Boy and Game Boy Color

**License:** Various (mostly permissive)

**Links:** `GitHub <https://github.com/gbdk-2020/gbdk-2020>`_ |
`API Documentation <https://gbdk-2020.github.io/gbdk-2020/docs/api/>`_

Game Boy Advance (GBA)
----------------------

Butano
~~~~~~

**Butano** is a C++17 game engine built on devkitARM. It abstracts the
hardware while leaving the system's capabilities reachable.

**Key Features:**

- Sprite management with affine transformations
- Regular and affine background layers
- Audio support (DMG and DirectSound)
- Scene management system
- GBA-optimized math utilities

**License:** zlib License

**Links:** `GitHub <https://github.com/GValiente/butano>`_ |
`Documentation <https://gvaliente.github.io/butano/>`_

Tonclib
~~~~~~~

**Tonclib** is the long-standing GBA library. It is less actively developed
but stable, and comes with the Tonc tutorial, one of the best-documented
resources for GBA development.

**Key Features:**

- Advanced sprite and background management
- Mode 7 (affine) support for pseudo-3D effects
- Built-in text rendering

**License:** MIT-like (custom permissive)

**Links:** `GitHub <https://github.com/devkitPro/libtonc>`_ |
`Tonc Tutorial <https://www.coranac.com/tonc/text/>`_

Nintendo DS (NDS)
-----------------

NightFox's Lib
~~~~~~~~~~~~~~

**NightFox's Lib** is a high-level 2D game library built on libnds.

**Key Features:**

- Sprite engine with rotation and scaling
- Tiled background support
- Collision detection
- 2D and 3D text rendering
- Sound and MOD music playback
- File system access

**License:** MIT

**Links:** `GitHub <https://github.com/knightfox75/nds_nflib>`_

libnds + devkitARM
~~~~~~~~~~~~~~~~~~

**libnds** is the official devkitPro library, with low-level access to all DS
features. It requires knowing the hardware.

**Key Features:**

- Complete hardware access to both screens
- 2D and 3D graphics support
- Touchscreen and button input
- WiFi networking support
- FAT file system access
- Audio subsystem control

**License:** zlib License

**Links:** `GitHub <https://github.com/devkitPro/libnds>`_ |
`Documentation <https://libnds.devkitpro.org/>`_ |
`Examples <https://github.com/devkitPro/nds-examples>`_

Nintendo 3DS
------------

citro2d / citro3d
~~~~~~~~~~~~~~~~~

The **citro** libraries are the official devkitPro solution for 3DS
development, with hardware-accelerated 2D and 3D graphics.

**Key Features:**

- Hardware-accelerated rendering via PICA200 GPU
- 2D sprite batching (citro2d)
- Full 3D graphics pipeline (citro3d)
- Shader support
- Stereoscopic 3D rendering
- Text rendering

**License:** zlib License

**Links:** `citro3d <https://github.com/devkitPro/citro3d>`_ |
`citro2d <https://github.com/devkitPro/citro2d>`_ |
`Documentation <https://github.com/devkitPro/citro3d/wiki>`_ |
`Examples <https://github.com/devkitPro/3ds-examples>`_

Super Nintendo (SNES)
---------------------

PVSnesLib
~~~~~~~~~

**PVSnesLib** is a C library for the Super Nintendo.

**Key Features:**

- Sprite management (OAM)
- Background and tilemap support
- Mode 7 support for rotation and scaling
- Sound driver integration
- Gamepad input handling
- DMA and HDMA operations

**License:** MIT

**Links:** `GitHub <https://github.com/alekmaul/pvsneslib>`_ |
`Wiki <https://github.com/alekmaul/pvsneslib/wiki>`_

libSFX
~~~~~~

**libSFX** is a macro assembler framework for SNES development.

**Key Features:**

- Assembly-first with C support
- Super FX (GSU) support
- Music and sound effects
- Steeper learning curve

**License:** MIT

**Links:** `GitHub <https://github.com/Optiroc/libSFX>`_ |
`Wiki <https://github.com/Optiroc/libSFX/wiki>`_

Sega Mega Drive / Genesis
--------------------------

SGDK (Sega Genesis Development Kit)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**SGDK** is the most widely used framework for Mega Drive homebrew, with an
active community and extensive documentation.

**Key Features:**

- Sprite engine with hardware scrolling
- Multiple background plane support
- VDP (video display processor) management
- Z80 sound driver with XGM music format
- DMA operations
- Built-in collision detection
- ResComp resource compiler for assets

**License:** MIT

**Links:** `GitHub <https://github.com/Stephane-D/SGDK>`_ |
`Wiki <https://github.com/Stephane-D/SGDK/wiki>`_ |
`Forums <https://segaxtreme.net/forums/sgdk.77/>`_

Neo Geo
-------

NGDK (Neo Geo Development Kit)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**NGDK** brings C development to the Neo Geo arcade platform and AES
home console.

**Key Features:**

- C framework for Neo Geo development
- Sprite system management
- Background and fix layer handling
- Input handling for arcade controls
- Sound support (Z80 + YM2610)
- Asset conversion tools
- Example games included

**License:** Custom permissive

**Links:** `GitHub <https://github.com/dciabrin/ngdevkit>`_ |
`Wiki <https://github.com/dciabrin/ngdevkit/wiki>`_

PC Engine / TurboGrafx-16
-------------------------

HuC (Hudson C Compiler)
~~~~~~~~~~~~~~~~~~~~~~~

**HuC** is the classic PC Engine C compiler, still maintained by the
community.

**Key Features:**

- C compiler for PC Engine
- Support for HuCard and CD-ROM²
- PSG sound support
- Sprite management
- Background and tilemap support
- ADPCM audio for CD games
- Standard C library subset

**License:** BSD-like

**Links:** `GitHub <https://github.com/uli/huc>`_

Squirrel (HuDK)
~~~~~~~~~~~~~~~

**Squirrel** (HuDK) is a newer alternative to HuC.

**Key Features:**

- CD-ROM support

**License:** Open source

**Links:** `GitHub <https://github.com/BlockoS/HuDK>`_

Fifth and Sixth Generation Consoles
====================================

Sony PlayStation 1 (PS1)
------------------------

PSn00bSDK
~~~~~~~~~

**PSn00bSDK** is a lightweight open-source PS1 SDK, a free alternative to the
old Psy-Q SDK.

**Key Features:**

- Hardware 3D graphics (GTE) support
- 2D sprite and primitive rendering
- CD-ROM file system access
- SPU sound support with ADPCM and XA audio
- Memory card management
- Controller input (standard and analog)
- Serial I/O support

**License:** MPL 2.0

**Links:** `GitHub <https://github.com/Lameguy64/PSn00bSDK>`_ |
`Wiki <https://github.com/Lameguy64/PSn00bSDK/wiki>`_ |
`Examples <https://github.com/Lameguy64/PSn00bSDK/tree/master/examples>`_

Sega Saturn
-----------

Jo Engine
~~~~~~~~~

**Jo Engine** is a high-level 2D and 3D game engine for the Saturn.

**Key Features:**

- High-level API for 2D and 3D
- Sprite engine with scaling and rotation
- 3D model support with converter tools
- Audio support (PCM, CD audio)
- Save game management
- Collision detection
- Map and tilemap support
- USB dev cart support for rapid testing
- Video tutorials available

**License:** MIT

**Links:** `GitHub <https://github.com/johannes-fetz/joengine>`_ |
`Website <https://jo-engine.org/>`_ |
`Wiki <https://github.com/johannes-fetz/joengine/wiki>`_

Yaul
~~~~

**Yaul** is a replacement for the old Sega Basic Library, aimed at developers
who want low-level Saturn access.

**Key Features:**

- VDP1 and VDP2 support
- SCU DMA operations
- CD block support
- SCSP (sound) support
- USB dev cart support

**License:** BSD

**Links:** `GitHub <https://github.com/ijacquez/libyaul>`_ |
`Documentation <https://ijacquez.github.io/libyaul/>`_

Nintendo 64
-----------

libdragon
~~~~~~~~~

**libdragon** is the open-source N64 SDK, an alternative to the official
Nintendo one.

**Key Features:**

- 3D graphics via RDP/RSP
- Audio subsystem support
- Controller input
- ROM file system
- Hardware sprites

**License:** Unlicense (public domain)

**Links:** `GitHub <https://github.com/DragonMinded/libdragon>`_ |
`Documentation <https://dragonminded.github.io/libdragon/>`_

Sega Dreamcast
--------------

KallistiOS (KOS)
~~~~~~~~~~~~~~~~

**KallistiOS** is the de facto standard for Dreamcast homebrew.

**Key Features:**

- Complete OS-like framework
- 2D and 3D graphics (PowerVR)
- Network support (modem, broadband adapter)
- VMU (Visual Memory Unit) support
- Input device support
- CD-ROM file system (ISO9660)
- AICA SPU audio support
- Threading and multitasking
- USB development support

**License:** BSD-style

**Links:** `GitHub <https://github.com/KallistiOS/KallistiOS>`_ |
`Documentation <https://kos-docs.dreamcast.wiki/>`_ |
`Forums <https://dcemulation.org/phpBB/>`_

Additional KOS libraries include GLdc (OpenGL-like API) and SDL ports,
making cross-platform development easier.

Sony PlayStation 2 (PS2)
------------------------

PS2SDK
~~~~~~

**PS2SDK** gives access to the PlayStation 2 hardware.

**Key Features:**

- Graphics Synthesizer (GS) support for 2D/3D
- Emotion Engine and I/O Processor access
- Vector Unit (VU) programming
- Sound library (audsrv)
- USB and network support
- Memory card management
- DVD file system access

**License:** BSD/Academic Free License

**Links:** `GitHub <https://github.com/ps2dev/ps2sdk>`_ |
`Website <https://ps2dev.github.io/>`_ |
`Examples <https://github.com/ps2dev/ps2sdk/tree/master/samples>`_

Nintendo GameCube / Wii
-----------------------

devkitPPC + libogc
~~~~~~~~~~~~~~~~~~

The **devkitPro** toolchain for GameCube and Wii, with **libogc**.

**Key Features:**

- Official devkitPro toolchain
- Full hardware access for both systems
- GX 3D graphics library
- ASND audio library
- Controller support (PAD/WPAD)
- Network library
- USB and SD card storage
- DVD reading
- Homebrew Channel integration (Wii)

**License:** Various (permissive)

**Links:** `GitHub <https://github.com/devkitPro/libogc>`_ |
`Documentation <https://libogc.devkitpro.org/>`_ |
`Examples <https://github.com/devkitPro/gamecube-examples>`_ |
`devkitPro <https://devkitpro.org/>`_

Sony PlayStation Portable (PSP)
-------------------------------

PSPSDK
~~~~~~

**PSPSDK** is the homebrew SDK for the PSP.

**Key Features:**

- 3D graphics (GU library) with hardware acceleration
- 2D sprite rendering
- Multi-format audio support
- WiFi and networking
- USB support
- Memory Stick access
- Save data management
- MP3, AAC playback

**License:** BSD/GPL

**Links:** `GitHub <https://github.com/pspdev/pspsdk>`_ |
`Forums <https://forums.ps2dev.org/>`_ |
`Examples <https://github.com/pspdev/psp-packages>`_

PlayStation Vita
----------------

Vita SDK
~~~~~~~~

**Vita SDK** is the homebrew SDK for Sony's Vita.

**Key Features:**

- OpenGL ES-like graphics
- Touch screen support
- Accelerometer and gyroscope
- Camera support
- Network and WiFi
- Trophy system support
- Save data management
- Multi-format audio

**License:** Various

**Links:** `GitHub <https://github.com/vitasdk/vita-headers>`_ |
`Website <https://vitasdk.org/>`_ |
`Documentation <https://docs.vitasdk.org/>`_ |
`Examples <https://github.com/vitasdk/samples>`_

Xbox (Original)
---------------

nxdk
~~~~

**nxdk** is a clean-room Xbox SDK with no Microsoft code.

**Key Features:**

- Direct3D 8-like graphics API
- Audio support
- Controller input
- Network support
- Hard drive access
- SDL port available

**License:** Various (LGPL/MIT)

**Links:** `GitHub <https://github.com/XboxDev/nxdk>`_ |
`Wiki <https://github.com/XboxDev/nxdk/wiki>`_ |
`Examples <https://github.com/XboxDev/nxdk/tree/master/samples>`_

Development Tools and Workflow
===============================

DevkitPro Toolchain
-------------------

Many frameworks (GBA, DS, 3DS, GameCube/Wii) require the **devkitPro**
toolchain, which runs on Linux:

- `Website <https://devkitpro.org/>`_
- `Getting Started Guide <https://devkitpro.org/wiki/Getting_Started>`_
- Includes devkitARM, devkitPPC, and associated libraries
- Available via pacman (devkitPro package manager) on Fedora

Graphics Tools
--------------

These tools are free, open-source and run on Linux:

**Pixel Art Editors:**

- **Pixelorama** (MIT): Modern pixel art editor with animation support,
  built with Godot. An Aseprite alternative.
  `Website <https://pixelorama.org/>`_
- **LibreSprite** (GPL v2): Fork of old GPL Aseprite with familiar
  interface. `Website <https://libresprite.github.io/>`_
- **GrafX2** (GPL v2): Inspired by Deluxe Paint, excellent for retro
  graphics. `Website <http://grafx2.chez.com/>`_
- **Piskel** (Apache 2.0): Web-based and offline pixel art editor.
  `Website <https://www.piskelapp.com/>`_

**Tilemap Editor:**

- **Tiled** (GPL v2/BSD): Industry-standard tilemap editor.
  `Website <https://www.mapeditor.org/>`_

**General Graphics:**

- **GIMP** (GPL v3+): Full-featured image editor.
  `Website <https://www.gimp.org/>`_

Music and Sound Tools
---------------------

All tools below are free, open-source and run on Linux:

**Chiptune (Hardware Chip Emulation):**

- **Furnace** (GPL v2+): Multi-system chiptune tracker supporting 60+
  sound chips (NES, SNES, Genesis, Game Boy, etc.). Available on Flathub.
  `GitHub <https://github.com/tildearrow/furnace>`_

**Module Trackers (Sample-based):**

- **MilkyTracker** (GPL v3): FastTracker II-inspired tracker for
  MOD/XM formats. `Website <https://milkytracker.org/>`_
- **Schism Tracker** (GPL v2): Impulse Tracker clone for S3M/IT
  formats. `Website <http://schismtracker.org/>`_

**NES/Famicom Specific:**

- **FamiStudio** (MIT): DAW-style NES/Famicom music editor with
  expansion chip support. Available on Flathub.
  `Website <https://famistudio.org/>`_

**Audio Editor:**

- **Audacity** (GPL v2/v3): Multi-track audio editor and recorder.
  `Website <https://www.audacityteam.org/>`_

Emulators for Testing
----------------------

All emulators below are open-source and Linux-compatible:

- **mGBA**: Game Boy Advance - `Website <https://mgba.io/>`_
- **DeSmuME**: Nintendo DS - `Website <https://desmume.org/>`_
- **Citra**: Nintendo 3DS - `Website <https://citra-emu.org/>`_
- **bsnes**: Super Nintendo -
  `GitHub <https://github.com/bsnes-emu/bsnes>`_
- **Genesis Plus GX**: Sega Mega Drive -
  `GitHub <https://github.com/ekeeke/Genesis-Plus-GX>`_
- **Mednafen**: Multi-system (PC Engine, PS1, Saturn, etc.) -
  `Website <https://mednafen.github.io/>`_
- **DuckStation**: PlayStation 1 -
  `GitHub <https://github.com/stenzek/duckstation>`_
- **PCSX2**: PlayStation 2 - `Website <https://pcsx2.net/>`_
- **Dolphin**: GameCube/Wii - `Website <https://dolphin-emu.org/>`_
- **PPSSPP**: PlayStation Portable - `Website <https://www.ppsspp.org/>`_
- **Vita3K**: PlayStation Vita - `Website <https://vita3k.org/>`_
- **Flycast**: Sega Dreamcast -
  `GitHub <https://github.com/flyinghead/flycast>`_
- **Mupen64Plus**: Nintendo 64 -
  `Website <https://www.mupen64plus.org/>`_
- **xemu**: Original Xbox - `Website <https://xemu.app/>`_

Recommendations by Experience Level
====================================

Beginner-Friendly
-----------------

**8-bit/16-bit:**

- **GB Studio** (GBC): Visual editor, no coding required
- **GBDK-2020** (GBC): Simple C development
- **SGDK** (Mega Drive): Excellent documentation and community

**Fifth/Sixth Generation:**

- **PSn00bSDK** (PS1): lightweight API
- **Jo Engine** (Saturn): High-level engine with tutorials
- **PSPSDK** (PSP): stable, documented

Intermediate
------------

**8-bit/16-bit:**

- **Butano** (GBA): C++17, documented
- **PVSnesLib** (SNES): Comprehensive library
- **NightFox's Lib** (DS): High-level 2D development

**Fifth/Sixth Generation:**

- **KallistiOS** (Dreamcast): Mature ecosystem
- **devkitPPC** (GC/Wii): Official toolchain
- **Vita SDK** (Vita): Active community

Advanced
--------

**8-bit/16-bit:**

- **libSFX** (SNES): Assembly-first, highly optimized
- **citro3d** (3DS): Direct hardware access
- **libnds** (DS): Low-level control

**Fifth/Sixth Generation:**

- **PS2SDK** (PS2): Complex but powerful
- **Yaul** (Saturn): Modern low-level library
- **libdragon** (N64): RDP/RSP programming
- **nxdk** (Xbox): Direct3D 8 development

Community Resources
===================

**General Communities:**

- **NESDev Forums**: Multi-platform retro development -
  `Forums <https://forums.nesdev.org/>`_
- **GBAtemp**: DS/3DS homebrew - `Website <https://gbatemp.net/>`_
- **devkitPro Discord**: Nintendo handheld development

**Platform-Specific:**

- **GBADev**: Game Boy Advance - `Website <https://gbadev.net/>`_
- **PSXDev**: PlayStation 1 - `Website <https://www.psxdev.net/>`_
- **PS2Dev Forums**: PS2, PSP - `Forums <https://forums.ps2dev.org/>`_
- **DCEmulation**: Dreamcast - `Website <https://dcemulation.org/>`_
- **SegaXtreme**: Saturn, Mega Drive -
  `Website <https://segaxtreme.net/>`_
- **N64brew**: Nintendo 64 - `Website <https://n64brew.dev/>`_
- **GC-Forever**: GameCube/Wii - `Website <https://www.gc-forever.com/>`_
- **r/vitahacks**: PS Vita homebrew

Conclusion
==========

Everything here is free and open-source, from the SDKs to the pixel editors and
music trackers, and runs on Linux. The range goes from a no-code Game Boy
puzzle game in GB Studio to assembly-optimized code for the PlayStation 2's
Emotion Engine.

May your sprites never flicker.
