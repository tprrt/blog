.. SPDX-FileCopyrightText: 2026 Thomas Perrot <thomas.perrot@tupi.fr>
.. SPDX-License-Identifier: CC-BY-SA-4.0

=====================================
Embedded Linux Digest — Week 38, 2026
=====================================

:date: 2026-09-15 13:47
:category: Linux
:tags: embedded, linux, digest
:slug: embedded-linux-digest-week-38-2026
:authors: tperrot
:summary: Weekly roundup of Embedded Linux news.
:lang: en
:status: published

Linux Kernel and System Software
--------------------------------

This week’s kernel and system software news covered performance benchmarking, platform cleanup, and utility releases. Phoronix tested the in-development Linux 7.3 on Intel Panther Lake and Framework hardware, while the kernel is on track to shed a large number of old ARM 32-bit drivers. GNU coreutils 9.12 also landed with a range of improvements, and a look at PostgreSQL development activity provided useful stats for the wider Linux ecosystem.

- `Linux 7.3 Delivering Some Performance Gains On Intel Panther Lake / Framework Laptop 13 Pro <https://www.phoronix.com/review/linux-73-panther-lake>`_ (Source: Phoronix)
- `Removing Drivers For Outdated ARM Platforms Will Lighten The Kernel By ~247k Lines <https://www.phoronix.com/news/Branch-Remove-Old-ARM-Drivers>`_ (Source: Phoronix)
- `GNU Core Utilities 9.12 released <https://lwn.net/Articles/1094312/>`_ (Source: LWN.net)
- `Vondra: PostgreSQL development activity <https://lwn.net/Articles/1094470/>`_ (Source: LWN.net)

Embedded Hardware and Platforms
-------------------------------

A variety of new embedded hardware and design guidance appeared this week. Alif Semi introduced StartKits for its Cortex-M55/Ethos-U55 MCUs, MSI detailed a fanless Jetson Orin Nano industrial PC, and articles on SWaP-optimized UAV compute and mil/aero system design offered practical insights. Power electronics also got attention with a 140-W USB-C GaN reference platform from Eggtronic and Renesas.

- `Alif Semi Balletto B1 and Ensemble E1C StartKits feature Cortex-M55 + Ethos-U55 MCU for IoT and Edge AI <https://www.cnx-software.com/2026/09/15/alif-semi-balletto-b1-and-ensemble-e1c-startkits-feature-cortex-m55-ethos-u55-mcu-for-iot-and-edge-ai/>`_ (Source: CNX Software – Embedded Systems News)
- `Fanless industrial PC integrates Jetson Orin Nano 8GB and M.2 expansion <https://linuxgizmos.com/fanless-industrial-pc-integrates-jetson-orin-nano-8gb-and-m-2-expansion/>`_ (Source: LinuxGizmos.com)
- `Designing SWaP-Optimized Compute for UAVs <https://www.embedded.com/designing-swap-optimized-compute-for-uavs/>`_ (Source: Embedded)
- `ESD eBook September/October 2026: Rethinking Mil/Aero System Design <https://www.embedded.com/esd-ebook-september-october-2026-rethinking-mil-aero-system-design/>`_ (Source: Embedded)
- `Eggtronic, Renesas Target 140-W USB-C Chargers with GaN <https://www.embedded.com/eggtronic-renesas-target-140-w-usb-c-chargers-with-gan/>`_ (Source: Embedded)

Security and Networking
-----------------------

Security updates and networking development featured prominently. Debian and Fedora shipped patches, a long-standing Rustls vulnerability was finally fixed, and wolfSSL announced a webinar on porting its wolfIP TCP/IP stack to RTOS environments.

- `Security updates for Tuesday <https://lwn.net/Articles/1094469/>`_ (Source: LWN.net)
- `Rustls 0.23.45 Released To Fix Two Year Old Security Issue <https://www.phoronix.com/news/Rustls-0.23.45-Released>`_ (Source: Phoronix)
- `wolfSSL webinar explores wolfIP network driver and RTOS integration <https://linuxgizmos.com/wolfssl-webinar-explores-wolfip-network-driver-and-rtos-integration/>`_ (Source: LinuxGizmos.com)

Design Tools and Prototyping
----------------------------

For engineers working on hardware, a sponsored piece highlighted a KiCad plugin from AIVON that aims to speed up PCB prototyping by allowing direct quote generation from the design tool.

- `Design in KiCad, Quote with AIVON: A Faster Path to PCB Prototyping (Sponsored) <https://www.cnx-software.com/2026/09/15/design-in-kicad-quote-with-aivon-a-faster-path-to-pcb-prototyping/>`_ (Source: CNX Software – Embedded Systems News)
