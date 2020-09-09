===================================
How the Busybox's chrt applet works
===================================

:date: 2020-09-08 19:20
:modified: 2020-09-09 07:05
:tags: busybox, chrt
:category: busybox
:slug: busybox-chrt-dissection
:authors: tperrot
:summary: This article details the implementation of the *chrt* applet from Busybox
:lang: en
:status: draft

Introduction
============

In this article, I will dissect how the *chrt* applet from the release 1.32.0 of Busybox works, what it does, etc.

This command is a Linux utils allowing to consult or to modify the scheduling attributes of a process.

::

   $ chrt -m
   SCHED_OTHER min/max priority    : 0/0
   SCHED_FIFO min/max priority     : 1/99
   SCHED_RR min/max priority       : 1/99
   SCHED_BATCH min/max priority    : 0/0
   SCHED_IDLE min/max priority     : 0/0
   SCHED_DEADLINE min/max priority : 0/0

   $ pidof firefox
   6987 6851 6825 6816 6800 6771 6767 6761 6720 6611

   $ chrt -p 6987
   pid 6987's current scheduling policy: SCHED_OTHER
   pid 6987's current scheduling priority: 0

   $ sudo chrt -f -p 1 6987
   $ chrt -p 6987
   pid 6987's current scheduling policy: SCHED_FIFO
   pid 6987's current scheduling priority: 1

Busybox provides an applet which size, once compiled, and ten times smaller than that of the binary implementation and with
some limitations.


The dissection
==============

The implementation of the *chrt* applet is in the file
`util-linux/chrt.c <https://elixir.free-electrons.com/busybox/1.32.0/source/util-linux/chrt.c>`_ that containing several
functions which are called in the main function of this applet.

The main function of this applet is divised in three main parts:
- the first parses the command options
- the second prints the scheduler's information
- the last one, to apply scheduler changes in case of a set

At start of main, the character string containing the options are parsed to obtain a bitfield easier to use:

::

        opt = getopt32(argv, "^"
                        "+" "mprfobi"
                        "\0"
                        /* only one policy accepted: */
                        "r--fobi:f--robi:o--rfbi:b--rfoi:i--rfob"
        );

If the (-m) is set then the min and max valid priorities for each scheduling policies are shown and the command is existed:

::

        if (opt & OPT_m) { /* print min/max and exit */
                show_min_max(SCHED_OTHER);
                show_min_max(SCHED_FIFO);
                show_min_max(SCHED_RR);
                show_min_max(SCHED_BATCH);
                show_min_max(SCHED_IDLE);
                fflush_stdout_and_exit(EXIT_SUCCESS);
        }

The function *show_min_max* sends use the Posix functions *sched_get_priority_max* and *sched_get_priority_min* from the
standard C library to send a syscall to the kernel in order to obtain the min and max values accepted by each policy:

::

    max = sched_get_priority_max(pol);
    min = sched_get_priority_min(pol);
    if ((max|min) < 0)
        fmt = "SCHED_%s not supported\n";

Otherwise the required options and arguments to show or to apply real-time attributes of a process:

::

    //if (opt & OPT_r)
    //  policy = SCHED_RR; - default, already set
    if (opt & OPT_f)
        policy = SCHED_FIFO;
    if (opt & OPT_o)
        policy = SCHED_OTHER;
    if (opt & OPT_b)
        policy = SCHED_BATCH;
    if (opt & OPT_i)
        policy = SCHED_IDLE;

    argv += optind;
    if (!argv[0])
        bb_show_usage();
    if (opt & OPT_p) {
        pid_str = *argv++;
        if (*argv) { /* "-p PRIO PID [...]" */
                priority = pid_str;
                pid_str = *argv;
        }
        /* else "-p PID", and *argv == NULL */
        pid = xatoul_range(pid_str, 1, ((unsigned)(pid_t)ULONG_MAX) >> 1);
    } else {
        priority = *argv++;
        if (!*argv)
                bb_show_usage();
    }

Then the applet uses the Posix function *sched_getscheduler* provides by the standard C library to obtain the scheduling attributes of the process specified by the pid.

::

    print_rt_info:
        pol = sched_getscheduler(pid);
        if (pol < 0)
                bb_perror_msg_and_die("can't %cet pid %u's policy", 'g', (int)pid);

Finally, when the *chrt* applet is used to modify scheduling attributes then the Posix function *sched_getscheduler* is used and the new scheduling attributes are showed:

::

    if (sched_setscheduler(pid, policy, &sp) < 0)
        bb_perror_msg_and_die("can't %cet pid %u's policy", 's', (int)pid);

    if (!argv[0]) /* "-p PRIO PID [...]" */
        goto print_rt_info;

The function *sched_getscheduler* and *sched_getscheduler* will send a syscall to the scheduler subsystem of the kernel Linux.
This subsystem also exposes this information from */proc*:

::

    $ cat /proc/6987/sched
    WebExtensions (6987, #threads: 23)
    -------------------------------------------------------------------
    se.exec_start                                :       4421312.640001
    se.vruntime                                  :        344438.942254
    se.sum_exec_runtime                          :         38238.466094
    se.nr_migrations                             :                 6811
    nr_switches                                  :                49452
    nr_voluntary_switches                        :                21749
    nr_involuntary_switches                      :                27703
    se.load.weight                               :              1048576
    se.runnable_weight                           :              1048576
    se.avg.load_sum                              :                 3415
    se.avg.runnable_load_sum                     :                 3415
    se.avg.util_sum                              :              3497621
    se.avg.load_avg                              :                   74
    se.avg.runnable_load_avg                     :                   74
    se.avg.util_avg                              :                   74
    se.avg.last_update_time                      :        4421312640000
    se.avg.util_est.ewma                         :                   75
    se.avg.util_est.enqueued                     :                   75
    policy                                       :                    0
    prio                                         :                  120
    clock-delta                                  :                   89
    mm->numa_scan_seq                            :                    0
    numa_pages_migrated                          :                    0
    numa_preferred_nid                           :                   -1
    total_numa_faults                            :                    0
    current_node=0, numa_group_id=0
    numa_faults node=0 task_private=0 task_shared=0 group_private=0 group_shared=0


Limitations
===========

Below a short list of limitations that I observed during my analysis of this applet.

Resetting scheduling policy
---------------------------

The *chrt* applet doesn't offer an option (-R) to specify if the scheduling policy should be applied or reseted when a
process is fork to create children. This feature, introduced since Linux 2.6.32, can be only enabled or disabled at the
build of busybox and it is applied on all scheduling attributes modifications done with this applet.

Deadline support
----------------

The *chrt* applet doesn't provide the required scheduling options (-d, -T, -P and -D) to set the deadline scheduling attributes of a process.
