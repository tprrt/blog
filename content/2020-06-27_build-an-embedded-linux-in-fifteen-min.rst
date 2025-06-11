===============================================
Build an embedded Linux in less than 15 minutes
===============================================

:date: 2020-06-27 13:01
:modified: 2025-06-11 14:53
:tags: busybox, embedded, intermediate, linux, qemu
:category: linux
:slug: build-an-embedded-linux-in-fifteen-min
:authors: tperrot
:summary: This article will explain how to build a minimal embedded Linux, in less than 15 minutes, and without a build framework.
:lang: en
:status: published

Introduction
============

Since some years, I haven't built an embedded Linux without using a framework, like `Open Embedded`_ from the `Yocto`_
project.
Then here, I wanted to make a guide to help you to build quickly, from "scratch" a very minimal embedded Linux to boot a
target.
The following examples have been written to boot a virtual Qemu target but, they can be adapted to boot a real target.
Moreover, the build environment will be bootstrapped with a prebuilt cross-toolchain, I have chosen to use one provided
by `Bootlin`_ and using glibc.

Setup the environment
=====================

First, it is required to install the packages that are needed to install and use the cross-toolchain but also to compile the host tools and to provide Qemu:

- The Ncurses libraries are only required to execute the command `make menuconfig`.
- The certificates and wget will be used to download the prebuilt toolchain.
- In the same way, git will be used to checkout the source of `Busybox`_ and `Linux`_.
- The Qemu packages will be used to emulate system platform and to execute static binaries cross-compiled for aarch64 on the x86-64 host.

.. code-block:: bash

   apt update
   apt install -y --no-install-recommends \
       bc \
       build-essential \
       ca-certificates \
       cpio \
       file \
       flex \
       git \
       ipxe-qemu \
       libncurses5-dev \
       libncursesw5-dev \
       libssl-dev \
       qemu \
       qemu-system-aarch64 \
       qemu-user-static \
       wget

Now, it is time to download and install the prebuilt toolchain:

.. code-block:: bash

   mkdir ~/src
   cd ~/src
   wget https://toolchains.bootlin.com/downloads/releases/toolchains/aarch64/tarballs/aarch64--glibc--stable-2020.08-1.tar.bz2
   tar xvjf aarch64--glibc--stable-2020.08-1.tar.bz2

Once the toolchain has been extracted you have to set the required environment variables to cross-compile binaries:

- ``PATH``: It shall be extended so that the cross-tools from the cross-toolchain will be available from the environment
- ``CROSS_COMPILE``: In order to clarify the prefix used by the cross-tools
- ``ARCH``: The architecture of the target platform
  
.. code-block:: bash

    ls ~/src/aarch64--glibc--stable-2020.08-1/bin/*gcc
    ~/src/aarch64--glibc--stable-2020.08-1/bin/aarch64-linux-gcc

    export PATH=~/src/aarch64--glibc--stable-2020.08-1/bin:$PATH
    export CROSS_COMPILE=aarch64-linux-

Now, it is possible to call the cross-tools from the shell:

.. code-block:: bash

    aarch64-linux-gcc -v
    Using built-in specs.
    COLLECT_GCC=~/src/aarch64--glibc--stable-2020.08-1/bin/aarch64-linux-gcc.br_real
    COLLECT_LTO_WRAPPER=~/src/aarch64--glibc--stable-2020.08-1/bin/../libexec/gcc/aarch64-buildroot-linux-gnu/9.3.0/lto-wrapper
    Target: aarch64-buildroot-linux-gnu
    <...>
    Thread model: posix
    gcc version 9.3.0 (Buildroot 2020.08-14-ge5a2a90)

Concerning the variable ``PATH`` this one will be set afterwards because its value depends on the binary that will be built.

Build the Linux kernel
======================

So, the environment is ready to pull the sources of the latest stable branch of the kernel `Linux`_ and to build them:

.. code-block:: bash

    git clone git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
    cd linux
    git checkout -b local/linux-5.4.y origin/linux-5.4.y
    # git show HEAD

    export ARCH=arm64

    make defconfig
      HOSTCC  scripts/basic/fixdep
      HOSTCC  scripts/kconfig/conf.o
      HOSTCC  scripts/kconfig/confdata.o
      HOSTCC  scripts/kconfig/expr.o
      LEX     scripts/kconfig/lexer.lex.c
      YACC    scripts/kconfig/parser.tab.[ch]
      HOSTCC  scripts/kconfig/lexer.lex.o
      HOSTCC  scripts/kconfig/parser.tab.o
      HOSTCC  scripts/kconfig/preprocess.o
      HOSTCC  scripts/kconfig/symbol.o
      HOSTLD  scripts/kconfig/conf
    *** Default configuration is based on 'defconfig'
    #
    # configuration written to .config
    #

    # make menuconfig

    make -j$(nproc)
      <...>
      AR      drivers/net/ethernet/built-in.a
      AR      drivers/net/built-in.a
      AR      drivers/built-in.a
      GEN     .version
      CHK     include/generated/compile.h
      LD      vmlinux.o
      MODPOST vmlinux.o
      MODINFO modules.builtin.modinfo
      LD      .tmp_vmlinux.kallsyms1
      KSYM    .tmp_vmlinux.kallsyms1.o
      LD      .tmp_vmlinux.kallsyms2
      KSYM    .tmp_vmlinux.kallsyms2.o
      LD      vmlinux
      SORTEX  vmlinux
      SYSMAP  System.map
      Building modules, stage 2.
      MODPOST 531 modules
      OBJCOPY arch/arm64/boot/Image
      GZIP    arch/arm64/boot/Image.gz

The command ``make defconfig`` will apply the default configuration for the target platform (cf. ``ARCH=arm64``), and the
compilation will be performed by ``make -j$(nproc)``.

The commands ``git show HEAD`` and ``make defconfig`` are optional:
- the first is useful to verify that the latest commit corresponding to the latest tag of the branch ``linux-5.4.y``.
- the second can be used if you want to customize the kernel configuration.

*NB*. The kernel `Linux`_ but also `Busybox`_ and some projects use `Kbuild`_ to manage the build options

Populate the sysroot
====================

The easy way to bootstrap a sysroot is to use `Busybox`_ that has been created to offer common UNIX tools into a single
executable and it is size-optimized. To create a sysroot, it is only required to add a few configuration files.

The steps to pull and build `Busybox`_ are similar to those of the kernel `Linux`_.

.. code-block:: bash

   git clone git://git.busybox.net/busybox
   cd busybox
   git checkout -b local/1_32_stable origin/1_32_stable
   # git show HEAD

   export ARCH=aarch64
   export LDFLAGS="--static"

   make defconfig
   # make menuconfig
   make -j$(nproc)

   make install

Here, the *LDFLAGS* is set to force static linking of `Busybox`_ quickly, but it is also possible to use
*make menuconfig* to set *CONFIG_STATIC=y*. The advantage of the static executable is that it can be tested with Qemu:

.. code-block:: bash

    qemu-aarch64-static busybox echo "Hello!"
    Hello!
    qemu-aarch64-static busybox date
    Sat Jun 27 15:06:41 UTC 2020

The binary *qemu-aarch64-static* allows to execute a binary built for another architecture on the host computer, for
example here it allows to execute the `Busybox`_ binary compiled for an aarch64 target on a x86-64 host.

The last command *make install* created a tree into the *\_install* directory that can be used to populate the sysroot:

.. code-block:: bash

    ls -l _install
    total 4
    drwxr-xr-x. 1 tperrot tperrot 974 Nov 30 15:22 bin
    lrwxrwxrwx. 1 tperrot tperrot  11 Nov 30 15:22 linuxrc -> bin/busybox
    drwxr-xr-x. 1 tperrot tperrot 986 Nov 30 15:22 sbin
    drwxr-xr-x. 1 tperrot tperrot  14 Nov 30 15:22 usr

    ls -l _install/bin
    <...>
    lrwxrwxrwx. 1 tperrot tperrot       7 Nov 30 15:22 umount -> busybox
    lrwxrwxrwx. 1 tperrot tperrot       7 Nov 30 15:22 uname -> busybox
    lrwxrwxrwx. 1 tperrot tperrot       7 Nov 30 15:22 usleep -> busybox
    lrwxrwxrwx. 1 tperrot tperrot       7 Nov 30 15:22 vi -> busybox
    lrwxrwxrwx. 1 tperrot tperrot       7 Nov 30 15:22 watch -> busybox
    lrwxrwxrwx. 1 tperrot tperrot       7 Nov 30 15:22 zcat -> busybox


In order, to finalize this minimal sysroot, it is required to create a rcS init script:

.. code-block:: bash

    mkdir _install/proc _install/sys _install/dev _install/etc _install/etc/init.d
    cat > _install/etc/init.d/rcS << EOF
    #!/bin/sh
    mount -t proc none /proc
    mount -t sysfs none /sys
    /sbin/mdev -s
    [ ! -h /etc/mtab ]  && ln -s /proc/mounts /etc/mtab
    [ ! -f /etc/resolv.conf ] && cat /proc/net/pnp > /etc/resolv.conf
    EOF
    chmod +x _install/etc/init.d/rcS

Build the filesystem
====================

The target of this step is to package the sysroot tree into a filesystem that can be mounted by the kernel.
There is two available possibilities, either build a *ramfs* or a *rootfs*.

Globally, the difference between both is that:

- the ramfs is a very simple filesystem that can be used by the kernel to create a block device into the RAM space from an archive.
- the rootfs is a filesystem mounted from a non volatile device by the kernel.

For more information about the difference between the ramfs and the rootfs, you can you refer to the `kernel documentation`_.

Build a ramfs
-------------

To build the ramfs we will use *cpio* and *gzip* to construct the compressed archive after modifying the rights:

.. code-block:: bash

    mkdir _rootfs
    rsync -a _install/ _rootfs
    chown -R root:root _rootfs
    cd _rootfs
    find . | cpio -o --format=newc > ../rootfs.cpio
    cd ..
    gzip -c rootfs.cpio > rootfs.cpio.gz

Build a rootfs
--------------

To build the rootfs, the first step is to create an empty binary blob that will be mounted into a loop device to be
formatted to create a ext3 filesystem. Then the tree can be copied and the rights updated.

.. code-block:: bash

    dd if=/dev/zero of=rootfs.img bs=1M count=10
    mke2fs -j rootfs.img
    mkdir _rootfs
    mount -o loop rootfs.img _rootfs
    rsync -a _install/ _rootfs
    chown -R root:root _rootfs
    sync
    umount _rootfs

Boot the target
===============

Following, the qemu commands to boot the minimal embedded Linux system that has been built.

.. code-block:: bash

    # With the ramfs
    qemu-system-aarch64 -nographic -no-reboot -machine virt -cpu cortex-a57 -smp 2 -m 256 \
        -kernel ~/src/linux/arch/arm64/boot/Image \
	-initrd ~/src/busybox/rootfs.cpio.gz \
	-append "panic=5 ro ip=dhcp root=/dev/ram rdinit=/sbin/init"

    # With the rootfs
    qemu-system-aarch64 -nographic -no-reboot -machine virt -cpu cortex-a57 -smp 2 -m 256 \
        -kernel ~/src/linux/arch/arm64/boot/Image \
	-append "panic=5 ro ip=dhcp root=/dev/vda" \
	-drive file=~/src/busybox/rootfs.img,format=raw,if=none,id=hd0 -device virtio-blk-device,drive=hd0

Then the target will be boot to shell, *"It's alive!"*:

.. code-block:: bash

    [    0.000000] Booting Linux on physical CPU 0x0000000000 [0x411fd070]
    [    0.000000] Linux version 5.10.0-rc5 (tperrot@27ea4a863f61) (aarch64-linux-gcc.br_real (Buildroot 2020.08-14-ge5a2a90) 9.3.0, GNU ld (GNU Binutils) 2.33.1) #1 SMP PREEMPT Mon Nov 30 14:40:05 UTC 2020
    [    0.000000] Machine model: linux,dummy-virt
    <...>
    [    0.858346] Sending DHCP requests ., OK
    [    0.870558] IP-Config: Got DHCP answer from 10.0.2.2, my address is 10.0.2.15
    [    0.870909] IP-Config: Complete:
    [    0.871199]      device=eth0, hwaddr=52:54:00:12:34:56, ipaddr=10.0.2.15, mask=255.255.255.0, gw=10.0.2.2
    [    0.871566]      host=10.0.2.15, domain=, nis-domain=(none)
    [    0.871825]      bootserver=10.0.2.2, rootserver=10.0.2.2, rootpath=
    [    0.871866]      nameserver0=10.0.2.3
    [    0.872389]
    [    0.875863] ALSA device list:
    [    0.876151]   No soundcards found.
    [    0.879353] uart-pl011 9000000.pl011: no DMA platform data
    [    0.920237] Freeing unused kernel memory: 5952K
    [    0.921223] Run /sbin/init as init process

    Please press Enter to activate this console.

.. _Bootlin: https://toolchains.bootlin.com
.. _Busybox: https://busybox.net
.. _Kbuild: https://www.kernel.org/doc/html/latest/kbuild/kbuild.html
.. _kernel documentation: https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html
.. _Linux: https://www.kernel.org
.. _Open Embedded: https://openembedded.org
.. _Yocto: https://yoctoproject.org
