========================
Zephyr Device Tree Guide
========================

:date: 2022-07-29 20:32
:modified: 2022-07-29 20:32
:tags: zephyr, device-tree, rtos, embedded, article
:category: Embedded
:slug: zephyr-device-tree-guide
:authors: tperrot
:summary: How Zephyr uses devicetree: sources, the generated header, bindings and drivers.
:lang: en
:status: published

Introduction
============

The `Zephyr project`_, hosted by the Linux Foundation since 2016, provides a real-time operating system (RTOS), under the Apache 2.0 license, for connected devices too small for Linux or acting as companions to a Linux core. It targets microcontrollers and IoT devices, is modular, and is written in C (C11, with C++17 supported).

It can be configured to run on devices with as little as 10 KB of memory. It supports 32-bit and 64-bit architectures (Cortex-A, Cortex-M, Cortex-R, RISC-V, x86-64, etc.), many boards (Feather, nRF52840, ST Discovery, ST Nucleo, ESP32, etc.), connectivity such as Bluetooth, Ethernet, Wi-Fi and LoRa, and network protocols including IPv4, IPv6, UDP, TCP, CoAP, LWM2M, MQTT and DNS.

Like Linux, Zephyr uses `Kconfig`_, and its device model is mainly based on `device tree`_.

Device tree
===========

Device trees are tree data structures that describe the hardware components and their relationships in a system.
They are stored in text files, the device tree sources (\*.dts), which developers write to describe the hardware of SoCs and boards. The operating system uses them to determine how to initialize and interact with the hardware.

Each node describes a device of the system, has properties that describe its characteristics, and has exactly one parent (except the root node).

Each device driver is associated with a specific device tree node, which represents a hardware component in the system. The device driver provides the necessary code and data to control the behavior of the hardware component.

.. code-block:: c

    test_i2c_bme280: bme280@6 {
            compatible = "bosch,bme280";
            reg = <0x6>;
    };

In the Linux kernel, device tree sources are compiled to device tree binaries (dtb) that the bootloader stages (U-Boot, TF-A...) and the kernel parse at boot, so the same binaries can support several hardware configurations.

In Zephyr, device tree sources are instead turned at build time into a ``devicetree_generated.h`` C header. It contains the macros and data structures that let drivers read the hardware description, such as a device's memory mapping, pin assignments and IRQ numbers:

.. code-block:: c

    #define DT_COMPAT_HAS_OKAY_bosch_bme280 1
    #define DT_N_INST_bosch_bme280_NUM_OKAY 1
    #define DT_FOREACH_OKAY_bosch_bme280(fn) fn(DT_N_S_soc_S_i2c_40005400_S_bme280_77)
    #define DT_FOREACH_OKAY_VARGS_bosch_bme280(fn, ...) fn(DT_N_S_soc_S_i2c_40005400_S_bme280_77, __VA_ARGS__)
    #define DT_FOREACH_OKAY_INST_bosch_bme280(fn) fn(0)
    #define DT_FOREACH_OKAY_INST_VARGS_bosch_bme280(fn, ...) fn(0, __VA_ARGS__)
    #define DT_COMPAT_bosch_bme280_BUS_i2c 1

Where:

- **DT_COMPAT_HAS_OKAY_bosch_bme280**: indicates that there is at least one instance of BME280
- **DT_N_INST_bosch_bme280_NUM_OKAY**: defines the number of BME280 instances that are marked okay
- **DT_FOREACH_OKAY_bosch_bme280**: allows you to apply a function *fn* to each instance of the BME280
- **DT_FOREACH_OKAY_VARGS_bosch_bme280**: also allows you to apply a function *fn* to each instance of the BME280, but with additional arguments
- **DT_FOREACH_OKAY_INST_bosch_bme280**: allows you to apply a function *fn* to each instance of the BME280, passing the instance number as an argument
- **DT_FOREACH_OKAY_INST_VARGS_bosch_bme280**: is similar to the previous macro, but this one allows for additional arguments
- **DT_COMPAT_bosch_bme280_BUS_i2c**: indicates that the BME280 device is connected to an I2C bus.
- **DT_N_S_soc_S_i2c_40005400_S_bme280_77**: refers to a specific node in the device tree, here it refers to the BME280 sensor connected to the I2C controller with the base address 0x40005400 within the SoC. The sensor's address on this I2C bus is 0x77.

In addition, device tree sources can be extended or overridden, for example to connect additional devices to a board, or to disable board devices which will not be used:

.. code-block:: c

    / {
            aliases {
                    bme280 = &bme280;
            };
    };

    &spi1 {
            status = "disabled";
    };

    &i2c1 {
            status = "okay";
            bme280: bme280@77 {
                    compatible = "bosch,bme280";
                    reg = <0x77>;
            };
    };

Binding
=======

The content of device tree sources is described in binding files, written in YAML. They are also used to validate device tree sources against the YAML description.

.. code-block:: yaml

    description: BME280 integrated environmental sensor

    compatible: "bosch,bme280"

    include: [sensor-device.yaml, i2c-device.yaml]

Device driver
=============

A Zephyr driver reads the properties of its device tree node through macros defined in C headers. For example, this code initializes a BME280 sensor using properties from the device tree:

.. code-block:: c

    #include <device.h>
    #include <drivers/i2c.h>
    #include <devicetree.h>
    #include <zephyr.h>

    // Define the node identifier for the BME280 sensor
    #define BME280_NODE DT_N_S_soc_S_i2c_40005400_S_bme280_77

    // Function to initialize the BME280 sensor
    static int bme280_init(const struct device *dev)
    {
        // Check if the node is available
        if (!device_is_ready(dev)) {
            printk("Device %s is not ready\n", dev->name);
            return -ENODEV;
        }

        // Retrieve the I2C device associated with the BME280 node
        const struct device *i2c_dev = DEVICE_DT_GET(DT_BUS(BME280_NODE));

        if (!device_is_ready(i2c_dev)) {
            printk("I2C device not ready\n");
            return -ENODEV;
        }

        // Write some initialization code here, such as configuring registers

        printk("BME280 sensor initialized\n");
        return 0;
    }

    // Initialize the BME280 sensor at boot time
    SYS_INIT(bme280_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);

Conclusion
==========

Anyone who has written a BSP or driver for Linux will find this familiar. It is a steeper step for people coming from bare microcontroller development.

.. _Zephyr project: https://zephyrproject.org/
.. _Kconfig: https://www.kernel.org/doc/html/latest/kbuild/kconfig-language.html
.. _device tree: https://www.devicetree.org/
