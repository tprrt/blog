=================================================
Secure Boot with AHAB on i.MX93: A Complete Guide
=================================================

:date: 2024-08-06 19:21
:modified: 2024-08-06 19:21
:tags: security, embedded, imx93, secure-boot, ahab, nxp
:category: Security
:slug: secure-boot-with-ahab-on-imx93
:authors: tperrot
:summary: Learn how to implement Secure Boot using AHAB on NXP i.MX93 processors
	  to protect your embedded devices from unauthorized code execution.
:lang: en
:status: published

**The security of embedded devices has never been more critical.** In a world
where attacks targeting IoT systems are becoming increasingly sophisticated,
ensuring the integrity of the boot process is a must. This is where **Secure
Boot** comes in—an essential technology that guarantees only authorized code can
execute on a device from the moment it starts. In this article, we will explore
the implementation of Secure Boot using AHAB, the solution provided by NXP to
secure the i.MX93 from its initial boot stages.

**Why is Secure Boot crucial for your device?**

A secure boot ensures that no malicious code interferes with the critical boot
process, protecting your device from attacks targeting the bootloader and early
boot stages. Furthermore, AHAB, integrated into i.MX93 processors, enables
advanced authentication right from the initial boot stages, ensuring that only
validated components can be loaded, thereby strengthening security from the
get-go.

Secure boot is a critical security feature that ensures only authenticated and
authorized code can run on a device. It operates through a chain of trust, where
each component verifies the integrity of the next element in the chain.

Several mechanisms must be used to authenticate each element of this chain, but
the mechanism for authenticating the first boot stages depends on the target SoC.
The i.MX93 series uses NXP's Advanced High Assurance Boot (AHAB) to secure the
first boot stages.

For subsequent stages, you can implement mechanisms such as:

- Using U-Boot's "verified boot" feature to sign the kernel,
- Using the default environment (cf. USE_DEFAULT_ENV_FILE), and restricting
  write access to only a few environment variables (cf. ENV_WRITEABLE_LIST),
  which are necessary for writable access, such as for OTA updates,
- Using DM-verity to authenticate the root filesystem,
- And finally, using OverlayFS combined with DM-crypt to mount encrypted,
  writable subfolders.

Here, we'll focus on the first part of the secure boot process, using NXP's AHAB
to authenticate the bootloader on the NXP i.MX93 in single-boot mode. We will
also briefly discuss how to generate the keys to sign the bootloader and provide
an introduction to AHAB.

*Note: AHAB also provides a complementary encryption feature designed to protect
the confidentiality and integrity of data, whereas secure boot focuses on
verifying the integrity and authenticity of the boot process. This post will not
cover encryption in detail.*

AHAB Architecture
=================

The AHAB authentication mechanism is based on public key cryptography using
asymmetric keys.

On the i.MX93, AHAB support is provided by a security co-processor, the EdgeLock
enclave (ELE), which handles the authentication of binaries signed with one or
more private keys. This co-processor contains fuses that must be burned with the
hash of the public keys.

AHAB Containers
---------------

Since multiple boot stages (e.g., TF-A, OP-TEE, U-Boot, etc.) and firmwares are
required to boot i.MX93 platforms, these binaries are packed into containers
using the `imx-mkimage`_ tool:

.. code-block:: text

   bl31.bin
   lpddr4_dmem_1d_v202201.bin
   lpddr4_dmem_2d_v202201.bin
   lpddr4_imem_1d_v202201.bin
   lpddr4_imem_2d_v202201.bin
   mx93a1-ahab-container.img
   tee.bin
   u-boot.bin
   u-boot-spl.bin

In i.MX93 single-boot mode, the bootloader image contains at least three
containers:

- **mx93a1-ahab-container.img**: Contains the ELE Firmware.
- **u-boot-atf-container.img**: Contains at least the SPL.
- **flash.bin**: Contains TF-A, OP-TEE, and U-Boot.

.. code-block:: text

           *start ----> +---------------------------+ ---------
                        |   1st Container header    |   ^
                        |       and signature       |   |
                        +---------------------------+   |
                        | Padding for 1kB alignment |   |
   *start + 0x400 ----> +---------------------------+   |
                        |   2nd Container header    |   |
                        |       and signature       |   |
                        +---------------------------+   |
                        |          Padding          |   |  Authenticated at
                        +---------------------------+   |  ELE ROM/FW Level
                        |           ELE FW          |   |
                        +---------------------------+   |
                        |          Padding          |   |
                        +---------------------------+   |
                        |       Cortex-M Image      |   |
                        +---------------------------+   |
                        |         SPL Image         |   v
                        +---------------------------+ ---------
                        |   3rd Container header    |   ^
                        |       and signature       |   |
                        +---------------------------+   |
                        |          Padding          |   | Authenticated
                        +---------------------------+   | at SPL Level
                        |            TF-A           |   |
                        +---------------------------+   |
                        |           OP-TEE          |   |
                        +---------------------------+   |
                        |           U-Boot          |   v
                        +---------------------------+ ---------

These containers are signed offline using `NXP Code-Signing Tools (CST)`_, which
also allow the creation of an OEM private key infrastructure (PKI) and the
generation of the associated public keys (SRK) table, which is burned into the
fuses. The CST can also be used with the PKCS#11 standard to access
cryptographic services from tokens or devices such as HSM, TPM, and smart cards.

The first container is signed with NXP keys and is authenticated by the ELE ROM,
while the other containers are signed with OEM keys.

AHAB Boot Flow
--------------

In single boot mode, the Cortex-A55 ROM reads data from the selected boot
device, loading all containers in the chosen boot image set one by one. All
images within each container (e.g., EdgeLock secure enclave firmware, Cortex-M33
firmware, A55 firmware, OP-TEE, and U-Boot) are loaded, and the EdgeLock secure
enclave (ELE) is tasked with authenticating them. The ELE firmware is
authenticated by the ELE ROM, and images in the second container are verified by
the ELE firmware.

If the bootloader image contains more than two containers, the third and
subsequent containers are authenticated by the SPL instead of the ELE.

PKI Generation
==============

To authenticate the bootloader, we need to generate keys. These keys can be
created with the CST_. The private key will be used to sign the bootloader, and
the public key will be burned into the i.MX93 fuses to authenticate the
bootloader during boot.

Follow these steps to generate the keys:

.. code-block:: bash

   cd cst-3.4.1/keys
   echo 00000001 > serial

Write the passphrase for the certificate (replace "fooahabcert" with your
choice) in two lines, separated by ``\n``. It is important to store this
passphrase securely with backups:

.. code-block:: bash

   echo -e "fooahabcert\nfooahabcert" > key_pass.txt

Generate a P384 ECC PKI tree with a subordinate SGK key on CST:

.. code-block:: bash

   ./ahab_pki_tree.sh
   [...]
   Do you want to use an existing CA key (y/n)?: n

   Key type options (confirm targeted device supports desired key type):
   Select the key type (possible values: rsa, rsa-pss, ecc)?: ecc
   Enter length for elliptic curve to be used for PKI tree:
   Possible values p256, p384, p521:  p384
   Enter the digest algorithm to use: sha384
   Enter PKI tree duration (years): 10
   Do you want the SRK certificates to have the CA flag set? (y/n)?: n

Generate the Signing Root Keys (SRK) Table and SRK Hash for 64-bit Linux machines:

.. code-block:: bash

   cd ../crts/
   ../linux64/bin/srktool -a -d sha256 -s sha384 -t SRK_1_2_3_4_table.bin \
       -e SRK_1_2_3_4_fuse.bin -f 1 -c \
       SRK1_sha384_secp384r1_v3_usr_crt.pem,\
       SRK2_sha384_secp384r1_v3_usr_crt.pem,\
       SRK3_sha384_secp384r1_v3_usr_crt.pem,\
       SRK4_sha384_secp384r1_v3_usr_crt.pem

Do not enter spaces between the commas when specifying the SRKs in the "-c" or
"--certs" option. Otherwise, the certificates specified after the first space
will be excluded from the table.

Regenerate the SRK HASH (SRK_1_2_3_4_fuse.bin) using SHA256 with the
SRK_1_2_3_4_table.bin:

.. code-block:: bash

   openssl dgst -binary -sha256 SRK_1_2_3_4_table.bin

Optionally, verify that the sha256sum of SRK_1_2_3_4_table matches the SRK_1_2_3_4_fuse.bin:

.. code-block:: bash

   od -t x4 SRK_1_2_3_4_fuse.bin
   0000000 29eec727 eaed9aa7 c7e53bc0 36835f78
   0000020 6901bc47 b244753c f78d3162 27ae36b9
   0000040

Bootloader Signature
====================

The CST uses CSF description files to sign (and encrypt) containers generated by
imx-mkimage with OEM keys. When imx-mkimage generates containers, it also
specifies the block offsets to be used in the CSF description files. For
example, imx-mkimage returns the following values for your bootloader:

.. code-block:: text

   CST: CONTAINER 0 offset: 0x0
   CST: CONTAINER 0: Signature Block: offset is at 0x190
   CST: CONTAINER 0 offset: 0x400
   CST: CONTAINER 0: Signature Block: offset is at 0x490

Where *0x190* is the block offset for the second container header and *0x490* is
the block offset for the third container header.

The CSF description file used to sign a container contains three sections:

- *[Header]*: Information about the HAB version to use for signing.
- *[Authenticate Data]*: Information about the key used to sign.
- *[Install SRK]*: Information about the container being signed.

The following CSF description files were used to sign the
*u-boot-atf-container.img* in our example:

.. code-block:: ini

   [Header]
   Target = AHAB
   Version = 1.0

   [Install SRK]
   # SRK table generated by srktool
   File = "SRK_1_2_3_4_table.bin"
   # Public key certificate in PEM format
   Source = "SRK1_sha384_secp384r1_v3_usr_crt.pem"
   # Index of the public key certificate within the SRK table (0 .. 3)
   Source index = 0
   # Type of SRK set (NXP or OEM)
   Source set = OEM
   # bitmask of the revoked SRKs
   Revocations = 0x0

   [Authenticate Data]
   # Binary to be signed generated by mkimage
   File = "u-boot-atf-container.img"
   # Offsets = Container header  Signature block (printed out by mkimage)
   Offsets = 0x0 0x190

The following CSF description files were used to sign *flash.bin* in our
example:

.. code-block:: ini

   [Header]
   Target = AHAB
   Version = 1.0

   [Install SRK]
   # SRK table generated by srktool
   File = "SRK_1_2_3_4_table.bin"
   # Public key certificate in PEM format
   Source = "SRK1_sha384_secp384r1_v3_usr_crt.pem"
   # Index of the public key certificate within the SRK table (0 .. 3)
   Source index = 0
   # Type of SRK set (NXP or OEM)
   Source set = OEM
   # bitmask of the revoked SRKs
   Revocations = 0x0

   [Authenticate Data]
   # Binary to be signed generated by mkimage
   File = "flash.bin"
   # Offsets = Container header  Signature block (printed out by mkimage)
   Offsets = 0x400 0x490

The first step is to generate a *u-boot-atf-container.img*, then copy the block
offsets into the CSF description file to sign it:

.. code-block:: bash

   make SOC=iMX9 REV=A1 dtbs=imx93-11x11-evk.dtb u-boot-atf-container.img

Next, sign it with the following command and replace the unsigned version:

.. code-block:: bash

   cst -i u-boot-atf-container.img.csf -o u-boot-atf-container.img.signed
   mv u-boot-atf-container.img.signed u-boot-atf-container.img

Then generate a *flash.bin* containing the signed *u-boot-atf-container.img*:

.. code-block:: bash

   make SOC=iMX9 REV=A1 V2X=NO dtbs=imx93-11x11-evk.dtb flash_singleboot

Finally, sign the resulting *flash.bin*:

.. code-block:: bash

   cst -i flash.bin.csf -o flash.bin.signed

Burn Fuses
==========

Once the signed *flash.bin* is flashed, you need to burn the public keys used to
sign the bootloader into the i.MX93 fuses to finalize AHAB secure boot. This
requires using a U-Boot that provides AHAB functionalities, such as checking ELE
events during bootloader authentication and securing the device.

Program SRK
-----------

The following commands enable AHAB secure boot by programming the
*SRK_HASH[255:0]* fuses on i.MX93, ensuring that only bootloaders signed with
keys matching the SRK hash programmed into the fuses will be accepted:

.. code-block:: bash

   fuse prog -y 16 0 0x29eec727
   fuse prog -y 16 1 0xeaed9aa7
   fuse prog -y 16 2 0xc7e53bc0
   fuse prog -y 16 3 0x36835f78
   fuse prog -y 16 4 0x6901bc47
   fuse prog -y 16 5 0xb244753c
   fuse prog -y 16 6 0xf78d3162
   fuse prog -y 16 7 0x27ae36b9

Close the Device
----------------

Once the SRK fuses are programmed, you can "close" the device to allow only the
bootloader signed with keys matching the SRK table to boot:

.. code-block:: bash

   ahab_close

Before closing the device, you can verify that the fuses have been written
correctly by checking that no ELE events are raised:

.. code-block:: bash

   ahab_status
   Lifecycle: 0x00000008, OEM Open

   No Events Found!
   =>
   Lifecycle: 0x00000008, OEM Open

   No Events Found!

Once the device is closed, the *ahab_status* command will show *OEM closed*:

.. code-block:: bash

   ahab_status
   Lifecycle: 0x00000020, OEM closed

   No Events Found!
   =>
   Lifecycle: 0x00000020, OEM closed
   No Events Found!

Until *OEM Open* appears in the status, the device is not secured and can still
execute unsigned bootloaders or those signed with invalid keys.

Conclusion
==========

By implementing AHAB on the i.MX93 platform, you can ensure that your boot
process is protected from unauthorized code. The use of public key cryptography
and secure containers adds an extra layer of security, making your device more
resilient to attacks. This process is crucial for applications where integrity
and authenticity from the very first boot stage are paramount.

.. _CST: https://www.nxp.com/webapp/sps/download/license.jsp?colCode=IMX_CST_TOOL_NEW
.. _imx-mkimage: https://github.com/nxp-imx/imx-mkimage
.. _NXP Code-Signing Tools (CST): https://www.nxp.com/webapp/sps/download/license.jsp?colCode=IMX_CST_TOOL_NEW
