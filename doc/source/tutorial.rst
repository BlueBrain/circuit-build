How to create a new circuit build
=================================

.. note::

    | Neocortex circuit building pipeline has diverged from the "master" one.
    | Please make sure to check :ref:`ref-neocortex` section after reading the main tutorial.

Preparation
-----------

1. Create circuit release folder

.. code-block:: bash

    $ cd /gpfs/bbp.cscs.ch/project/<proj>/circuits
    $ mkdir -p <release-name> && cd <release-name>

2. Create and populate `bioname` folder or copy it over from another build.

Please refer to :ref:`ref-bioname` section for the list of the files that constitute a `bioname`.

.. tip::

    We strongly recommend to keep `bioname` content under VCS, one way or another; and to reference a read-only snapshot of it for the released circuits.

    An approach taken in `proj1` and `proj42` is to store all bionames in git-controlled ``<proj>/entities/bionames/`` folder and symlink the corresponding one from circuit build folder.

3. Get a snapshot of circuit building pipeline:

.. code-block:: bash

    $ git clone ssh://bbpcode.epfl.ch/common/circuit-build

4. Make `snakemake` command available.

On BB5 cluster `snakemake` is available as a module:

.. code-block:: bash

    $ module load snakemake

`snakemake` can run all the tasks locally or launch every task in a separate `Slurm` allocation.
In practice the latter option is preferred, please refer to :ref:`ref-cluster-config` section for the details.

It is also recommended to always use ``-p`` flag to ensure commands spawned by `snakemake` are dumped to the logs.

For all the commands below we assume that a following alias is defined:

.. code-block:: bash

    $ alias sm='snakemake -p --config bioname=<path-to-bioname> --snakefile <circuit-build>/snakemake/Snakefile --cluster-config <path-to-config>'

We also assume that all ``sm`` commands are executed from circuit release folder root.


Running
-------

With `snakemake`, one can choose which phases to run.
To get a feel for the process, and to only run a subset of the pipeline, it's instructive to run the `Cell collection`_.

The reasoning for using `snakemake` is available here: :ref:`ref-faq-why-snakemake`


Cell collection
~~~~~~~~~~~~~~~

To build a minimal circuit (MVD3 + target definitions) execute:

.. code-block:: bash

    $ sm

After the command above has completed, the following files could be found in circuit folder:

::

    CircuitConfig_base
    circuit.mvd3
    start.target

At this point the circuit is partially complete and should be readable by `BluePy <https://bbpcode.epfl.ch/documentation/bluepy-0.13.5/index.html>`_ for analysis not involving connectome.

There are also some intermediate partial MVD3 files:

::

    circuit.mvd3.somata
    circuit.mvd3.morphologies

These could be safely removed, should you not need them.
We recommend to keep them however, at least until the circuit build is finalized to speed up potential rebuilds.


Connectome
~~~~~~~~~~

Building connectome involves two phases: :ref:`ref-phase-touchdetector`, followed by :ref:`ref-phase-spykfunc_s2f`.

.. code-block:: bash

    $ sm -j8 functional

After the command above has completed, any analysis not involving spatial indices should be possible.


Spatial indices
~~~~~~~~~~~~~~~

To build *segment* spatial index:

.. code-block:: bash

    $ sm spatial_index_segment

Segment spatial index requires only cell collection, and thus can be built prior to connectome (or in parallel with it).

To build *synapse* spatial index:

.. code-block:: bash

    $ sm spatial_index_synapse

Synapse spatial index obviously requires connectome as well, and thus is executed after `functional` target is built.


Structural circuit
~~~~~~~~~~~~~~~~~~

If you'd like to build a structural circuit instead of functional one (i.e., avoid pruning synapses when executing `functionalizer`):

.. code-block:: bash

    $ sm -j8 structural

instead of:

.. code-block:: bash

    $ sm -j8 functional

.. note::

    You can also build structural circuit *in addition* to the functional one.
    They do not conflict with each other, but share the common files (``circuit.mvd3``, ``start.target`` etc).
    Structural circuit would be available via ``CircuitConfig_struct`` file.


Subcellular
~~~~~~~~~~~

To assign gene expressions and protein concentrations to the cells:

.. code-block:: bash

    $ sm subcellular

One command to build it all
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    $ sm -j99 -k functional_all

would launch all the tasks needed to generate files listed in :ref:`ref-circuit-files` section.

Providing ``-j<N>`` allows to launch up to ``<N>`` tasks in parallel; ``-k`` flag instructs `Snakemake` to proceed with other jobs if some independent job has failed.


.. _ref-cluster-config:

Cluster config
--------------

By default `snakemake` launches all the tasks locally.
To use *cluster mode* (i.e. launch every task in a separate Slurm allocation) one has to provide YAML file with allocation parameters for each phase.

.. code-block:: bash

    $ snakemake --cluster-config cluster.yaml ...

For instance, to specify Slurm allocation for ``touchdetector`` phase, YAML should contain an entry like:

::

    touchdetector:
        jobname: td
        salloc: '-A proj68 -p prod --constraint=cpu -n100 --time 1:00:00'

``jobname`` key is optional (if omitted, Slurm job will be given some default name).

Sometimes it can be convenient to use multi-line string for ``salloc`` key:

::

    touchdetector:
        jobname: td
        salloc: >-
            -A proj68
            -p prod
            --constraint=cpu
            -n100
            --time 1:00:00

`YAML` *must* also contain ``__default__`` section which will be used for phases with no corresponding section, for instance:

::

    __default__:
        salloc: '-A proj68 -p prod_small --time 0:15:00'


Tips & Tricks
-------------


After build is complete
~~~~~~~~~~~~~~~~~~~~~~~

Once circuit build is complete, we'd recommend to make its `bioname`, as well as the result circuit files, read-only.

You can also remove intermediate files and folders like ``circuit.mvd3.<suffix>`` or ``connectome/<type>/spykfunc``.
