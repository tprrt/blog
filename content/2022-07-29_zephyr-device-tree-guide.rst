========================
Zephyr Device Tree Guide
========================

:date: 2022-07-29 20:32
:modified: 2022-07-29 20:32
:tags: zephyr, device-tree, rtos, embedded
:category: Embedded
:slug: zephyr-device-tree-guide
:authors: tperrot
:summary:
:lang: en
:status: published

Introduction
============

The goal of the `Zephyr project`_, hosted by the Linux foundation, since 2016, is to provide a safe and secured real time operating system (RTOS) for connected devices that are too small for Linux, or for core companion, through the Apache 2.0 open source license.

It is designed for resource-constrained devices such as microcontrollers and Internet of Things (IoT) devices, to be modular and scalable. This makes it ideal for a wide range of devices, from simple sensors to complex systems. The operating system is written in C and is fully compatible with the C11 and C++17 standards.

One of the key benefits of the Zephyr device model is its small footprint, it can be configured to run on devices with as little as 10 KB of memory.

It supports multiple 32 bits and 64 bits architectures: Cortex-A, Cortex-M, Cortex-R, RISC-V, x86-64, etc.
But it also support several boards and extensions: Feather, nRF52840, ST Discovery, ST Nucleo, ESP-32, etc.
It is able to manage several kinds of connectivity: Bluetooth, ethernet, wifi, LoRa.
And it support some network protocols: IPv4, IPv6,UDP, TCP, CoAP, LWM2M, MQTT, DNS, etc.

As Linux, Zephyr use `Kconfig`_, and its device model is mainly based on `device tree`_.

Device tree
===========

Device trees are tree data structures that describe the hardware components and their relationships in a system.
They are stored in a text file, named device tree sources (\*.dts), and they written by developers to describe hardware architectures of SoCs and boards.
And they are used by the operating system to determine how to initialize and interact with the hardware.

Each node describe a device of the system, has its own properties that describe their characteristics, and they have only one parent (except for the root node).

Each device driver is associated with a specific device tree node, which represents a hardware component in the system. The device driver provides the necessary code and data to control the behavior of the hardware component.

.. code-block:: c

    test_i2c_bme280: bme280@6 {
            compatible = "bosch,bme280";
            reg = <0x6>;
    };

In the Linux kernel, device tree sources are compiled to device tree binaries (dtb) that are parsed, at boot, by bootloader stages (U-Boot, TF-A...) and the kernel to allow support several hardware configuration with same binaries.

But in Zephyr, device tree sources are transformed to a "devicetree_generated.h" C header file at build, that contains macro definitions and data structures allowing device drivers to access information about the hardware components in the system, such as the memory mapping of a device, its pin assignments, and its IRQ numbers:

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

Content of device tree sources is described in binding files, that are written in human readable and easy to parse YAML.
Binding files can be also used to validate device tree sources by comparing the information in the YAML file with the information in the device tree sources.

.. code-block:: yaml

    description: BME280 integrated environmental sensor

    compatible: "bosch,bme280"

    include: [sensor-device.yaml, i2c-device.yaml]

Device driver
=============

In Zephyr, a device driver can access the properties of an associated node in the device tree using the macro that are defined in C header files.
For example, the following code can be used to initialize a BME280 sensor using properties defined in the device tree:

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

Those who have already implemented BSP or driver on Linux shouldn't encounter too much difficulty, but on the other hand, the step is a little higher for people coming from the world of micro-controllers.

.. _Zephyr project: https://zephyrproject.org/
.. _Kconfig: https://www.kernel.org/doc/html/latest/kbuild/kconfig-language.html
.. _device tree: https://www.devicetree.org/
