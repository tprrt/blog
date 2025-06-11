=========================
Build RIOT-OS with Podman
=========================

:date: 2020-09-27 13:01
:modified: 2025-06-11 14:53
:tags: container, podman, riot-os
:category: riot-os
:slug: build-riot-os-with-podman
:authors: tperrot
:summary: This article is a tip that explains how it is possible to build a
	  `RIOT-OS`_ application with `Podman`_.
:lang: en
:status: published

Summary
=======

This article is a tip that explains how it is possible to build a `RIOT-OS`_
application with `Podman`_ and the official build container. And I would like to
take this opportunity to introduce you to `Podman`_ and `RIOT-OS`_.

Podman
======

Some Linux distribution, like `Fedora`_ chosen to officially support only
`Podman`_ instead of `Docker`_ for several reasons:

- It is daemonless container engine.
- It is rootless.
- It follows Open Container Initiative (`OCI`_) standards.
- It is safer than the `Docker`_ engine.
- It introduces the notion of `Pods`_: a group of container(s) that share storage
  or network resources.

Moreover, `Podman`_ is able to use the images built by the `Docker`_ engine and
has been stored in `Docker`_ registry.

However, most of the time the `Podman`_ commands are identical to that of
`Docker`_, then a simple alias is enough to be misleading:
*alias docker=podman*.

But as `Podman`_ is rootless and safer than `Docker`_, then sometimes it is
necessary to specify additional security parameters.

RIOT-OS
=======

`RIOT-OS`_ is a memory-constrained `RTOS`_, such as `Contiki`_, that provides
real-time and multithreading abilities, and it runs on processors from 8bits to
32bits.

It was designed for `IoT`_ devices then to be low power consumption and it
provides three very complete network stacks including some protocols as:

- `IPv6`_
- `6LoWPAN`_
- `CoAP`_
- etc.

The `RIOT-OS`_ project also provides some useful tools including a build
container (`riotdocker`_).

And the build environment of `RIOT-OS`_ offers a `Makefile`_ to build an
application with this container simply by setting the variable *BUILD_IN_DOCKER*
to  *1*. Then the prebuilt image is downloaded and instantiated to execute the
`make`_ command.

By default, this feature is configured to be used with the `Docker`_ engine,
but it is possible to override some variables from the build environment
either to use a custom prebuilt image, either use another engine or to use
custom engine parameters.

Then here, we will use these environments variable to instantiate a container
with `Podman`_ (instead of `Docker`_) and with the required parameters.

Tip of the day
==============

In the following example, we build the Helloworld application for a STM32
Discovery board.
To do that we specify the engine by setting the variable *DOCKER* to the value
*podman*. The variable *DOCKER_USER* is set empty because in the variable
*DOCKER_RUN_FLAGS* the parameter *--userns* is set to *keep-id* to map the
uid:gid of the current rootless user (from host) with the values that will be
used into the container.

.. code-block:: bash

    export BUILD_IN_DOCKER=1
    export DOCKER="podman"
    export DOCKER_USER=""
    export DOCKER_RUN_FLAGS="--rm -i -t --security-opt seccomp=unconfined --security-opt label=disable --userns=keep-id"
    export DOCKER_MAKE_ARGS="-j$(nproc)"

    make BOARD=stm32l476g-disco
    Launching build container using image "riot/riotbuild:latest".
    podman run --rm -i -t --security-opt seccomp=unconfined --security-opt label=disable --userns=keep-id -v '/usr/share/zoneinfo/Europe/Paris:/etc/localtime:ro' -v '/home/tperrot/dev/tprrt/pwm-ramp-gen/RIOT:/data/riotbuild/riotbase:delegated' -e 'RIOTBASE=/data/riotbuild/riotbase' -e 'CCACHE_BASEDIR=/data/riotbuild/riotbase' -e 'BUILD_DIR=/data/riotbuild/riotbase/build' -v '/home/tperrot/dev/tprrt/pwm-ramp-gen:/data/riotbuild/riotproject:delegated' -e 'RIOTPROJECT=/data/riotbuild/riotproject' -e 'RIOTCPU=/data/riotbuild/riotbase/cpu' -e 'RIOTBOARD=/data/riotbuild/riotbase/boards' -e 'RIOTMAKE=/data/riotbuild/riotbase/makefiles'     -v '/home/tperrot/dev/tprrt/pwm-ramp-gen/.git:/home/tperrot/dev/tprrt/pwm-ramp-gen/.git:delegated' -e 'BOARD=stm32l476g-disco'  -w '/data/riotbuild/riotproject/' 'riot/riotbuild:latest' make 'BOARD=stm32l476g-disco'   -j8 
    Building application "hello-world" for "stm32l476g-disco" with MCU "stm32".

    [INFO] cloning stm32cmsis
    fatal: not a git repository: /data/riotbuild/riotbase/../.git/modules/RIOT
    Cloning into '/data/riotbuild/riotbase/cpu/stm32/include/vendor/cmsis/l4'...
    remote: Enumerating objects: 364, done.
    remote: Counting objects: 100% (364/364), done.
    remote: Compressing objects: 100% (71/71), done.
    remote: Total 364 (delta 309), reused 344 (delta 289), pack-reused 0
    Receiving objects: 100% (364/364), 709.56 KiB | 561.00 KiB/s, done.
    Resolving deltas: 100% (309/309), done.
    HEAD is now at e442c72 Release v1.6.1
    [INFO] updating stm32cmsis /data/riotbuild/riotbase/cpu/stm32/include/vendor/cmsis/l4/.pkg-state.git-downloaded
    echo e442c72651e8d4757f6562acc14da949644944ce   > /data/riotbuild/riotbase/cpu/stm32/include/vendor/cmsis/l4/.pkg-state.git-downloaded
    [INFO] patch stm32cmsis
    "make" -C /data/riotbuild/riotbase/boards/stm32l476g-disco
    "make" -C /data/riotbuild/riotbase/core
    "make" -C /data/riotbuild/riotbase/cpu/stm32
    "make" -C /data/riotbuild/riotbase/drivers
    "make" -C /data/riotbuild/riotbase/sys
    "make" -C /data/riotbuild/riotbase/cpu/cortexm_common
    "make" -C /data/riotbuild/riotbase/cpu/stm32/periph
    "make" -C /data/riotbuild/riotbase/drivers/periph_common
    "make" -C /data/riotbuild/riotbase/cpu/stm32/stmclk
    "make" -C /data/riotbuild/riotbase/sys/auto_init
    "make" -C /data/riotbuild/riotbase/cpu/cortexm_common/periph
    "make" -C /data/riotbuild/riotbase/cpu/stm32/vectors
    "make" -C /data/riotbuild/riotbase/sys/malloc_thread_safe
    "make" -C /data/riotbuild/riotbase/sys/newlib_syscalls_default
    "make" -C /data/riotbuild/riotbase/sys/pm_layered
    "make" -C /data/riotbuild/riotbase/sys/stdio_uart
       text    data     bss     dec     hex filename
       8900     112    2300   11312    2c30 /data/riotbuild/riotproject/bin/stm32l476g-disco/hello-world.elf

.. _6LoWPAN: https://en.wikipedia.org/wiki/6LoWPAN
.. _CoAP: https://en.wikipedia.org/wiki/Constrained_Application_Protocol
.. _Contiki: https://en.wikipedia.org/wiki/Contiki
.. _Fedora: https://getfedora.org
.. _Docker: https://www.docker.com
.. _IoT: https://en.wikipedia.org/wiki/Internet_of_things
.. _IPv6: https://en.wikipedia.org/wiki/IPv6
.. _make: https://en.wikipedia.org/wiki/Make_(software)
.. _Makefile: https://en.wikipedia.org/wiki/Makefile
.. _OCI: https://opencontainers.org
.. _Podman: https://podman.io
.. _Pods: https://kubernetes.io/docs/concepts/workloads/pods
.. _riotdocker: https://github.com/RIOT-OS/riotdocker
.. _RIOT-OS: https://github.com/RIOT-OS/RIOT
.. _RTOS: https://en.wikipedia.org/wiki/Real-time_operating_system
