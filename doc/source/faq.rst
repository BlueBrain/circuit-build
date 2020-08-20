FAQ
===

.. _ref-faq-why-snakemake:

How to contribute to this documentation?
----------------------------------------

1. Fetch the circuit building pipeline repository:

.. code-block:: bash

    $ git clone ssh://bbpcode.epfl.ch/common/circuit-build

2. Edit the documentation in ``doc/source``

3. Bump the version in ``doc/source/conf.py`` so that the change is deployed on merge

4. Ensure the documentation still builds and renders as expected

.. code-block:: bash

    $ push doc
    $ make html

5. Submit the patchset to Gerrit

Why Snakemake?
--------------

Using `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_ gives us certain advantages in comparison with the previous solutions used, in particular:

* minimum boilerplate for describing task dependencies
* tracking the needed updates (if some file changed, all its dependencies would be re-generated automatically)
* running tasks in parallel
* possibility to run tasks locally as well as with with Slurm
* creating reproducible environments for tasks using BBP modules

This could be considered an intermediate step towards more general workflow engine developed by NSE team.

Why making an intermediate step?

* to make circuit build description more transparent to new users
* to speed up circuit building by running the tasks in parallel where possible
* to provide a better documented solution than the previous one
* to improve circuit build reproducibility
* to facilitate merging circuit building pipelines for different projects (SSCX, Hippocampus, Thalamus)

.. _ref-faq-bioname:

Where can I find a sample *bioname*?
------------------------------------

Some sample bioname(s) can be found in ``circuit-build`` `Git repo <https://bbpcode.epfl.ch/browse/code/common/circuit-build/tree/tests>`_.

While not biologically realistic, these sample bionames serve as integration tests and are built on BB5 `daily <https://bbpcode.epfl.ch/ci/job/nse.circuit-build.tests/>`_; which gives certain guarantee that they are in sync with latest S/W deployed on BB5 cluster, as well as `circuit-build` script itself.


Where can I find logs for a given circuit build?
------------------------------------------------

`Snakemake` execution logs (which rules we launched along with full launch commands) can be found in ``.snakemake/logs`` subfolder of each circuit build folder.

STDOUT / STDERR output for most of the rules can be found in ``logs`` subfolder.


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

In fact, for better traceability we recommend to specify this argument *always*.


How can I re-build some file and all its dependencies?
------------------------------------------------------

.. code-block:: bash

    sm -R start.target

Please note that you can use file names as well as phase names for defining build targets:

.. code-block:: bash

    sm -R targetgen

thus will have the same effect.

Please refer to `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_ documentation for more details, and other options (run *upto* particular phase, etc).

How can I avoid regenerating files if I know they won't change?
---------------------------------------------------------------

`Snakemake` operates similar to `make` utility, and treats an output file as "outdated", if some of its inputs has a more recent timestamp.

To suppress this behavior (for instance, to skip TouchDetector re-run if a circuit file was re-generated in a way that does not affect touch detection), one can trick `Snakemake` by manually updating the timestamp of the output:

.. code-block:: bash

    touch connectome/touches/_SUCCESS


Which modules are used for executing phases?
--------------------------------------------

The list of modules used for executing each phase is hard-coded in ``Snakefile``.
Thus the environment created is isolated (to some degree); and replacing some module with a dev version is only a matter of changing absolute path to this module in your local copy of ``circuit-build`` (please look for ``MODULES`` mapping there).

With a few exceptions, normally we are using Spack-based archive modules deployed at BB5.
For better traceability, MODULEPATH and list of modules loaded is dumped to each phase log (for those phases where we keep logs).


Troubleshooting
---------------

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
