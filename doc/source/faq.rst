FAQ
===

Why Snakemake?
--------------

Using `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_ gives us certain advantages in comparison with the previous solutions used, in particular:

 * minimum boilerplate for describing task dependencies
 * tracking the needed updates (if some file changed, all its dependencies would be re-generated automatically)
 * running tasks in parallel
 * possibility to run tasks locally as well as with with SLURM
 * creating reproducible environments for tasks using `BBP archive S/W modules <https://bbpteam.epfl.ch/project/spaces/display/BBPHPC/BBP+ARCHIVE+SOFTWARE+MODULES>`_

This could be considered an intermediate step towards more general workflow engine developed by NSE team.

Why making an intermediate step?

 * to make circuit build description more transparent to new users
 * to speed up circuit building by running the tasks in parallel where possible
 * to provide a better documented solution than the previous one
 * to improve circuit build reproducibility
 * to facilitate merging circuit building pipelines for different projects (SSCX, Hippocampus, Thalamus)

Where can I find the logs?
--------------------------

Logs for most of the phases could be found in ``logs`` dir in circuit build folder.


How can I see the full list of the phases and their status?
-----------------------------------------------------------

.. code-block:: bash

    sm --list

or

.. code-block:: bash

    sm --summary

Please refer to `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_ documentation for more details.


How can I see the exact commands run?
-------------------------------------

Run `snakemake` with ``-p`` argument:

.. code-block:: bash

    sm -p place_cells


How can I re-build some file and all its dependencies?
------------------------------------------------------

.. code-block:: bash

    sm -R start.target

Please note that you can use file names as well as phase names for defining build targets:

.. code-block:: bash

    sm -R targetgen_mvd3

thus will have the same effect.

Please refer to `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_ documentation for more details, and other options (run *upto* particular phase, etc).


Troubleshooting
---------------


spark-submit command not found
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`assign_morphologies` phase failing with a message like:

.. code-block:: bash

    ModuleCmd_Load.c(213):ERROR:105: Unable to locate a modulefile for 'spark'
    /nix/store/c5bazvr75ic5399apdj272pprscxfir0-generated-env-module-placement-algorithm/bin/assign-morphologies: line 3: spark-submit: command not found

Cause: `assign_morphologies` phase relies on `spark` module which is stored at NFS.

Fix: Make sure your Kerberos token is not expired:

.. code-block:: bash

    kinit

Killed: Out of Memory
~~~~~~~~~~~~~~~~~~~~~

If you are seeing something like:

.. code-block:: bash

    Killed
    srun: error: r1i7n0: task 0: Out Of Memory

when running circuit build phases, please consider increasing memory limit for your Slurm allocation, for instance:

.. code-block:: bash

    salloc ... --mem 32G ...

More information on configuring Slurm allocations could be found `here <https://slurm.schedmd.com/sbatch.html>`_.