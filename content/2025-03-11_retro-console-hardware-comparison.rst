==============================================================
Retro Console Hardware Comparison: A Technical Deep Dive
==============================================================

:date: 2025-03-11 10:00
:modified: 2025-03-11 10:00
:tags: hardware, retro, console, comparison, technical
:category: hardware
:slug: retro-console-hardware-comparison
:authors: tperrot
:summary: A technical comparison of classic gaming consoles, covering CPU
    specifications, graphics capabilities, audio systems, and special features
    across multiple generations of hardware.
:lang: en
:status: published

Introduction
============

Understanding the hardware capabilities of classic gaming consoles
provides valuable insight for both homebrew developers and retro gaming
enthusiasts. Each console generation brought significant improvements in
processing power, graphics capabilities, and audio quality, while
working within tight memory constraints and power budgets.

This guide provides detailed technical comparisons across multiple
console generations, from the 8-bit Game Boy to modern hybrid systems
like the Nintendo Switch. Whether you're developing homebrew games or
simply curious about the technical evolution of gaming hardware, these
tables offer a reference.

.. contents:: Table of Contents
   :depth: 2

CPU and Memory Architecture
============================

The processors and memory configurations of gaming consoles reveal much
about their capabilities and limitations. Early consoles operated with
kilobytes of RAM, while modern systems have gigabytes at their disposal.

Processor Specifications
-------------------------

+------------------+----------------------------------+-------------+
|   Console        |   CPU                            |   Clock     |
|                  |                                  |   Speed     |
+==================+==================================+=============+
| Game Boy         | Custom Sharp LR35902             | 4.19 MHz    |
+------------------+----------------------------------+-------------+
| Game Boy Color   | Custom Sharp Z80                 | 8 MHz       |
+------------------+----------------------------------+-------------+
| NES              | Ricoh 2A03 (MOS 6502)            | 1.79 MHz    |
|                  |                                  | (NTSC) /    |
|                  |                                  | 1.66 MHz    |
|                  |                                  | (PAL)       |
+------------------+----------------------------------+-------------+
| SNES             | Ricoh 5A22 (65C816-based)        | 3.58 MHz    |
|                  |                                  | (max)       |
+------------------+----------------------------------+-------------+
| PC Engine        | HuC6280 (MOS 6502-based)         | 7.16 MHz    |
+------------------+----------------------------------+-------------+
| Neo Geo          | Motorola 68000 + Zilog Z80       | 12 MHz +    |
|                  |                                  | 4 MHz       |
+------------------+----------------------------------+-------------+
| Game Boy Adv.    | ARM7TDMI                         | 16.78 MHz   |
+------------------+----------------------------------+-------------+
| Nintendo DS      | ARM946E-S + ARM7                 | 67 MHz +    |
|                  |                                  | 33 MHz      |
+------------------+----------------------------------+-------------+
| Nintendo 3DS     | Dual-Core ARM11 MPCore           | 268 MHz     |
+------------------+----------------------------------+-------------+
| Wii              | IBM PowerPC "Broadway"           | 729 MHz     |
+------------------+----------------------------------+-------------+
| PSP              | MIPS R4000-based CPU             | 333 MHz     |
+------------------+----------------------------------+-------------+
| Switch           | NVIDIA Tegra X1                  | 1.02 GHz    |
|                  | (ARM Cortex-A57)                 |             |
+------------------+----------------------------------+-------------+

Memory Configurations
----------------------

+------------------+--------------------------------------------+
|   Console        |   RAM                                      |
+==================+============================================+
| Game Boy         | 8 KB                                       |
+------------------+--------------------------------------------+
| Game Boy Color   | 32 KB + 16 KB VRAM                         |
+------------------+--------------------------------------------+
| NES              | 2 KB + 2 KB VRAM                           |
+------------------+--------------------------------------------+
| SNES             | 128 KB + 64 KB VRAM                        |
+------------------+--------------------------------------------+
| PC Engine        | 8 KB + 64 KB VRAM                          |
+------------------+--------------------------------------------+
| Neo Geo          | 64 KB + 68 KB VRAM                         |
+------------------+--------------------------------------------+
| Game Boy Adv.    | 256 KB + 96 KB VRAM                        |
+------------------+--------------------------------------------+
| Nintendo DS      | 4 MB + 656 KB VRAM                         |
+------------------+--------------------------------------------+
| Nintendo 3DS     | 128 MB + 6 MB VRAM                         |
+------------------+--------------------------------------------+
| Wii              | 88 MB (24 MB + 64 MB GDDR3)                |
+------------------+--------------------------------------------+
| PSP              | 32 MB (PSP-1000) / 64 MB (PSP-2000+)       |
+------------------+--------------------------------------------+
| Switch           | 4 GB LPDDR4                                |
+------------------+--------------------------------------------+

**Key Observations:**

The evolution from kilobytes to gigabytes of RAM represents a
million-fold increase in memory capacity. The NES operated with just
2 KB of main RAM, requiring extremely efficient programming. Modern
consoles like the Switch have 4 GB, enabling complex 3D worlds and
high-resolution textures.

2D Graphics Capabilities
=========================

Early gaming consoles were built around dedicated 2D graphics hardware
with hardware sprites and tile-based rendering systems.

Color Depth and Palette
------------------------

+------------------+---------------------------+--------------------+
| Console          | Graphics Processor        | Displayable Colors |
+==================+===========================+====================+
| Game Boy         | Custom Sharp LR35902      | 4 shades of gray   |
+------------------+---------------------------+--------------------+
| Game Boy Color   | Custom Sharp Z80          | 32,768, 56 max     |
+------------------+---------------------------+--------------------+
| NES              | PPU (2C02 or 2C03)        | 52, 25 max         |
+------------------+---------------------------+--------------------+
| SNES             | S-PPU                     | 32,768, 256 max    |
+------------------+---------------------------+--------------------+
| PC Engine        | HuC6270A VDC              | 512, 482 max       |
+------------------+---------------------------+--------------------+
| Neo Geo          | Custom LSPC2-A2           | 65,536, 4,096 max  |
+------------------+---------------------------+--------------------+
| Game Boy Adv.    | Custom 2D Core            | 32,768, 512 max    |
+------------------+---------------------------+--------------------+
| Nintendo DS      | 2D/3D Graphics Engine     | 32,768, 4,096 max  |
+------------------+---------------------------+--------------------+
| Nintendo 3DS     | PICA200 GPU               | 16.8 million       |
+------------------+---------------------------+--------------------+
| Wii              | ATI Hollywood GPU         | 16.8 million       |
+------------------+---------------------------+--------------------+
| PSP              | Sony CXD2962GG + Media    | 16.8 million       |
+------------------+---------------------------+--------------------+
| Switch           | NVIDIA Tegra X1           | 16.8 million       |
+------------------+---------------------------+--------------------+

Sprite Capabilities
-------------------

+------------------+---------------------+----------------------------+
| Console          | Sprite Size         | Max Sprites on Screen      |
+==================+=====================+============================+
| Game Boy         | 8x8 or 8x16 px      | 40 sprites, max 10 per     |
|                  |                     | line                       |
+------------------+---------------------+----------------------------+
| Game Boy Color   | 8x8 or 8x16 px      | 40 sprites, max 10 per     |
|                  |                     | line                       |
+------------------+---------------------+----------------------------+
| NES              | 8x8 or 8x16 px      | 64 sprites, max 8 per line |
+------------------+---------------------+----------------------------+
| SNES             | Up to 64x64 px      | 128 sprites, max 32 per    |
|                  |                     | line                       |
+------------------+---------------------+----------------------------+
| PC Engine        | 16x16 px            | 64 sprites, max 16 per     |
|                  |                     | line                       |
+------------------+---------------------+----------------------------+
| Neo Geo          | Up to 16x512 px     | 380 sprites, no strict     |
|                  |                     | limit                      |
+------------------+---------------------+----------------------------+
| Game Boy Adv.    | Up to 64x64 px      | 128 sprites, max 32 per    |
|                  |                     | line                       |
+------------------+---------------------+----------------------------+
| Nintendo DS      | Up to 64x64 px      | 128 sprites, max 32 per    |
|                  |                     | line                       |
+------------------+---------------------+----------------------------+
| Nintendo 3DS     | Variable            | Sprite handling via 3D     |
|                  |                     | engine                     |
+------------------+---------------------+----------------------------+
| Wii              | Variable            | Sprite handling via 3D     |
|                  |                     | engine                     |
+------------------+---------------------+----------------------------+
| PSP              | Variable            | Sprite handling via 3D     |
|                  |                     | engine                     |
+------------------+---------------------+----------------------------+
| Switch           | Variable            | Sprite handling via 3D     |
|                  |                     | engine                     |
+------------------+---------------------+----------------------------+

**Key Observations:**

Sprite-per-line limits were a critical constraint for 8-bit and 16-bit
consoles. Developers had to carefully manage sprite placement to avoid
flickering. The Neo Geo's massive sprite sizes (up to 16x512 pixels)
and high sprite count made it exceptional for arcade-style action games.

Video Output Specifications
============================

Display resolution, refresh rate, and aspect ratio define the visual
output characteristics of each console.

Display Characteristics
-----------------------

+------------------+----------------------+----------------+----------+
| Console          | Resolution           | Refresh Rate   | Aspect   |
|                  |                      |                | Ratio    |
+==================+======================+================+==========+
| Game Boy         | 160x144              | 59.7 Hz        | 10:9     |
+------------------+----------------------+----------------+----------+
| Game Boy Color   | 160x144              | 59.7 Hz        | 10:9     |
+------------------+----------------------+----------------+----------+
| NES              | 256x240              | 60 Hz (NTSC)   | 4:3      |
|                  |                      | 50 Hz (PAL)    |          |
+------------------+----------------------+----------------+----------+
| SNES             | 256x224              | 60 Hz (NTSC)   | 4:3      |
|                  | 512x448i             | 50 Hz (PAL)    |          |
+------------------+----------------------+----------------+----------+
| PC Engine        | 256x224              | 59.94 Hz       | 4:3      |
+------------------+----------------------+----------------+----------+
| Neo Geo          | 320x224              | 59.18 Hz       | 4:3      |
+------------------+----------------------+----------------+----------+
| Game Boy Adv.    | 240x160              | 59.7 Hz        | 3:2      |
+------------------+----------------------+----------------+----------+
| Nintendo DS      | 256x192              | 59.8 Hz        | 4:3      |
|                  | (per screen)         |                |          |
+------------------+----------------------+----------------+----------+
| Nintendo 3DS     | 400x240 (top)        | 60 Hz          | 5:3      |
|                  | 320x240 (bottom)     |                | (top)    |
|                  |                      |                | 4:3      |
|                  |                      |                | (bottom) |
+------------------+----------------------+----------------+----------+
| Wii              | 640x480              | 60 Hz          | 4:3 or   |
|                  |                      |                | 16:9     |
+------------------+----------------------+----------------+----------+
| PSP              | 480x272              | 60 Hz          | 16:9     |
+------------------+----------------------+----------------+----------+
| Switch           | 1280x720             | 60 Hz          | 16:9     |
|                  | (Handheld)           |                |          |
|                  | 1920x1080 (Docked)   |                |          |
+------------------+----------------------+----------------+----------+

**Key Observations:**

Resolution evolved from the Game Boy's 160x144 to Full HD (1920x1080)
on the Switch when docked. Most classic consoles targeted NTSC's 60 Hz
or PAL's 50 Hz refresh rates. The shift from 4:3 to 16:9 aspect ratios
occurred around the PSP/Wii generation.

Audio Capabilities
==================

Audio capabilities progressed from simple tone generators to full PCM
sample playback and streaming capabilities.

Sound Architecture
------------------

+------------------+-------------------------+------------------+
| Console          | Sound Channels          | Sample Rate      |
+==================+=========================+==================+
| Game Boy         | 4 (2 square, 1 wave,    | ~8 kHz           |
|                  | 1 noise)                |                  |
+------------------+-------------------------+------------------+
| Game Boy Color   | 4 (same as GB)          | ~8 kHz           |
+------------------+-------------------------+------------------+
| NES              | 5 (2 pulse, 1 triangle, | ~21.3 kHz (NTSC) |
|                  | 1 noise, 1 DPCM)        | ~17.3 kHz (PAL)  |
+------------------+-------------------------+------------------+
| SNES             | 8 PCM                   | 32 kHz           |
+------------------+-------------------------+------------------+
| PC Engine        | 6 PCM                   | ~7.16 kHz to     |
|                  |                         | ~20 kHz          |
+------------------+-------------------------+------------------+
| Neo Geo          | 4 FM, 3 PSG, ADPCM-A,   | ~15.7 kHz        |
|                  | ADPCM-B                 | (ADPCM-A)        |
|                  |                         | ~18.5 kHz        |
|                  |                         | (ADPCM-B)        |
+------------------+-------------------------+------------------+
| Game Boy Adv.    | 6 (2 direct PCM +       | 32 kHz           |
|                  | 4 PSG)                  |                  |
+------------------+-------------------------+------------------+
| Nintendo DS      | 16 PCM                  | 32 kHz           |
+------------------+-------------------------+------------------+
| Nintendo 3DS     | 24 PCM                  | 32 kHz           |
+------------------+-------------------------+------------------+
| Wii              | 64 PCM                  | 48 kHz           |
+------------------+-------------------------+------------------+
| PSP              | 32 PCM                  | 44.1 kHz         |
+------------------+-------------------------+------------------+
| Switch           | 32 PCM                  | 48 kHz           |
+------------------+-------------------------+------------------+

Audio Output
------------

+------------------+---------------------------+------------------+
| Console          | Audio Processor           | Audio Output     |
+==================+===========================+==================+
| Game Boy         | Custom Sharp LR35902      | Mono             |
+------------------+---------------------------+------------------+
| Game Boy Color   | Custom Sharp Z80          | Mono             |
+------------------+---------------------------+------------------+
| NES              | Ricoh 2A03 (NTSC) /       | Mono             |
|                  | Ricoh 2A07 (PAL)          |                  |
+------------------+---------------------------+------------------+
| SNES             | Sony SPC700 + DSP         | Stereo           |
+------------------+---------------------------+------------------+
| PC Engine        | HuC6280 PSG               | Mono             |
+------------------+---------------------------+------------------+
| Neo Geo          | Yamaha YM2610             | Stereo           |
+------------------+---------------------------+------------------+
| Game Boy Adv.    | Custom 2D Core            | Stereo           |
+------------------+---------------------------+------------------+
| Nintendo DS      | 2D/3D Graphics Engine     | Stereo           |
+------------------+---------------------------+------------------+
| Nintendo 3DS     | PICA200 GPU               | Stereo           |
+------------------+---------------------------+------------------+
| Wii              | ATI Hollywood GPU         | Stereo / DPL II  |
+------------------+---------------------------+------------------+
| PSP              | Sony CXD2962GG + Media    | Stereo           |
+------------------+---------------------------+------------------+
| Switch           | NVIDIA Tegra X1           | Stereo / DPL IIx |
+------------------+---------------------------+------------------+

**Key Observations:**

The SNES was revolutionary with its 8-channel PCM audio at 32 kHz,
enabling CD-quality sound. The transition from mono to stereo output
occurred in the 16-bit generation. Modern consoles support Dolby
Pro Logic surround sound encoding.

Special Graphics Features
==========================

Beyond basic sprite and tile rendering, many consoles included special
graphics modes that enabled advanced visual effects.

Hardware Effects by Console
----------------------------

**Game Boy / Game Boy Color:**

- No special graphics modes beyond basic tile and sprite rendering

**NES:**

- Attribute Tables (Limited Tile Coloring)
- CHR-ROM for Tile-Based Graphics

**SNES:**

- **Mode 7**: Affine transformations for scaling and rotation, enabling
  pseudo-3D effects (used in games like F-Zero and Super Mario Kart)
- **Windowing Effects**: Variable transparency regions
- **HDMA** (Horizontal Direct Memory Access): Per-scanline effects
- **Color Math**: Hardware addition/subtraction for transparency and
  lighting effects

**PC Engine:**

- No special graphics modes beyond standard tile/sprite capabilities

**Neo Geo:**

- **Hardware Scaling** for sprites
- **Line Scroll**: Independent line offsets for parallax effects
- **Raster Effects**: Per-scanline modifications

**Game Boy Advance:**

- **Affine Transformation**: Mode 7-like scaling and rotation
- **Mosaic Effect**: Hardware pixelation for special effects
- **Alpha Blending**: Multi-layer transparency
- **Object Priority**: Hardware Z-ordering for sprites and backgrounds

**Nintendo DS:**

- **3D Rendering**: Hardware-accelerated 3D graphics engine
- **Extended Affine Transformations**: Advanced 2D rotation and scaling
- **Fog Effects**: Depth-based atmospheric effects
- **Multiple Background Layers**: Up to 4 background layers with
  independent scrolling

**Nintendo 3DS:**

- **Stereoscopic 3D**: Glasses-free autostereoscopic 3D display
- **Advanced Shader Support**: Programmable vertex and fragment shaders
- **GPU-Accelerated Rendering**: PICA200 graphics processor

**Wii:**

- **GPU Effects**: Programmable shaders, bloom, motion blur
- **Texture Mapping**: Advanced texture filtering and mipmapping
- **Bump Mapping**: Per-pixel lighting simulation
- **Hardware Anti-Aliasing**: Multi-sample anti-aliasing (MSAA)

**PSP:**

- **Hardware Transform & Lighting** (T&L): Vertex processing on GPU
- **Texture Compression**: Efficient VRAM usage
- **Advanced Alpha Blending**: Complex transparency effects

**Switch:**

- **Advanced Shaders**: Physically-Based Rendering (PBR)
- **Hardware-Accelerated Global Illumination**: Realistic lighting
- **HDR** (High Dynamic Range): Expanded color and brightness range
- **Post-Processing Effects**: Depth of field, screen-space ambient
  occlusion (SSAO), temporal anti-aliasing

**Key Observations:**

The SNES Mode 7 was revolutionary for its time, enabling pseudo-3D
effects with 2D hardware. The transition from fixed-function 2D
hardware to programmable 3D GPUs occurred around the Nintendo DS/PSP
generation. Modern consoles like the Switch support physically-based
rendering and advanced post-processing effects comparable to modern
gaming PCs.

Conclusion
==========

The evolution of gaming console hardware represents one of the most
dramatic technological progressions in computing history. From the
humble Game Boy's 4.19 MHz processor and 8 KB of RAM to the Switch's
1+ GHz quad-core CPU and 4 GB of RAM, each generation brought order-of-
magnitude improvements in capabilities.

Understanding these hardware specifications is essential for homebrew
developers targeting specific platforms. The constraints of each
system - limited sprite counts, scanline restrictions, memory budgets -
defined the creative solutions developers employed to create memorable
gaming experiences.

Whether you're developing a Game Boy game with 40 sprites and 4 colors,
or a Switch title with millions of polygons and advanced shaders, these
specifications provide the foundation for understanding what's possible
on each platform.

For developers, these tables serve as quick references when planning
projects. For enthusiasts, they illuminate why certain games looked and
played the way they did. The ingenuity of developers working within
these constraints produced some of gaming's most iconic titles.
