How to create a new circuit build
=================================

.. note::

    Neocortex circuit building pipeline has diverged from the "master" one.
    Please make sure to check :ref:`ref-neocortex` section after reading the main tutorial.

Preparation
-----------

1. Create circuit release folder

.. code-block:: bash

    $ cd /gpfs/bbp.cscs.ch/project/<proj>/circuits
    $ mkdir -p <release-name> && cd <release-name>

2. Create and populate `bioname` folder or copy it over from another build.

Please refer to :ref:`ref-bioname` section for the list of the files that constitute a `bioname`.

.. tip::

    We strongly recommend to keep `bioname` content under VCS, one way or another; and to reference
    a read-only snapshot of it for the released circuits.

    An approach taken in `proj1` and `proj42` is to store all bionames in git-controlled
    ``<proj>/entities/bionames/`` folder and symlink the corresponding one from circuit build folder.

3. Get a circuit building pipeline:

**Locally**

.. code-block:: bash

    $ git clone ssh://bbpcode.epfl.ch/common/circuit-build
    # we assume here that your `pip` points to a virtual environment
    $ pip install ./circuit-build

**BB5**

.. code-block:: bash

    $ module load unstable # or an archive module if you need a specific version
    $ module load circuit-build


Running
-------
Two commands appear in your path: `circuit-build` and `snakemake`. We suggest to use `circuit-build`.
It is a wrapper around `snakemake` with default preset options and arguments. It uses the same
options and arguments as `snakemake`. For example:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml

is equivalent to:

.. code-block:: bash

    $ snakemake --jobs 8 --printshellcmds  --config bioname=/path/to/bioname --snakefile circuit_build/snakemake/Snakefile --cluster-config /path/to/cluster.yaml

As you can see by default `circuit_build/snakemake/Snakefile` of this project is used. We suggest to
use it as it takes care of all necessary preparations. If you choose to use `snakemake` directly
then get familiar with Slurm allocations in :ref:`ref-cluster-config` section. `--printshellcmds`
flag ensures that subsequent spawned commands are dumped to the logs.  `--jobs 8` allows to launch
up to `8` tasks in parallel.
Further on we assume that you use `circuit-build run` command which is executed from the circuit's
release folder root.

`circuit_build/snakemake/Snakefile` contains many ready to use recipes that allow you to generate
any part of a circuit. Such recipes are called phases in `snakemake`. Usually it is a name of a
circuit file you want to generate. To choose a phase, type its name at the end of
`circuit-build run` call. For example:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml phase-name

To get an absolute path to `circuit_build/snakemake/Snakefile` type:

.. code-block:: bash

    $ circuit-build snakefile-path

For more detailed examples see below. For more predefined phases see :ref:`ref-phases`.


Cell collection
~~~~~~~~~~~~~~~

To build a minimal circuit (SONATA + target definitions) execute:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml

After the command above has completed, the following files could be found in circuit folder:

::

    CircuitConfig_base
    circuit.h5
    start.target

At this point the circuit is partially complete and should be readable by
`BluePy <https://bbpcode.epfl.ch/documentation/bluepy-0.13.5/index.html>`_ for analysis not
involving connectome. There are also some intermediate partial Sonata files:

::

    circuit.somata.h5
    circuit.morphologies.h5

These could be safely removed, should you not need them. We recommend to keep them however, at
least until the circuit build is finalized to speed up potential rebuilds.


Connectome
~~~~~~~~~~

Building connectome involves two phases: :ref:`ref-phase-touchdetector`, followed by :ref:`ref-phase-spykfunc_s2f`.

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml functional

After the command above has completed, any analysis not involving spatial indices should be possible.


Spatial indices
~~~~~~~~~~~~~~~

To build *segment* spatial index:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml spatial_index_segment

Segment spatial index requires only cell collection, and thus can be built prior to connectome
(or in parallel with it).

To build *synapse* spatial index:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml spatial_index_synapse

Synapse spatial index obviously requires connectome as well, and thus is executed after `functional`
target is built.


Structural circuit
~~~~~~~~~~~~~~~~~~

If you'd like to build a structural circuit instead of functional one (i.e., avoid pruning synapses
when executing `functionalizer`):

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml structural

instead of:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml functional

.. note::

    You can also build structural circuit *in addition* to the functional one.
    They do not conflict with each other, but share the common files (`circuit.h5`, `start.target` etc).
    Structural circuit would be available via `CircuitConfig_struct` file.


Subcellular
~~~~~~~~~~~

To assign gene expressions and protein concentrations to the cells:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml subcellular

One command to build it all
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml -j 99 -k functional_all

would launch all the tasks needed to generate files listed in :ref:`ref-circuit-files` section.

Providing `-j <N>` allows to launch up to `<N>` tasks in parallel; `-k` flag instructs
`Snakemake` to proceed with other jobs if some independent job has failed.


.. _ref-cluster-config:

Cluster config
--------------

By default `snakemake` launches all the tasks locally. To use *cluster mode* (i.e. launch every
task in a separate Slurm allocation) one has to provide YAML file with allocation parameters for
each phase. Such file is required by `circuit-build run` command.

.. code-block:: bash

    $ snakemake --cluster-config cluster.yaml ...

For instance, to specify Slurm allocation for `touchdetector` phase, YAML should contain an entry
like:

.. code-block:: yaml

    touchdetector:
        jobname: td
        salloc: '-A proj68 -p prod --constraint=cpu -n100 --time 1:00:00'

`jobname` key is optional (if omitted, Slurm job will be given some default name).

Sometimes it can be convenient to use multi-line string for `salloc` key:

.. code-block:: yaml

    touchdetector:
        jobname: td
        salloc: >-
            -A proj68
            -p prod
            --constraint=cpu
            -n100
            --time 1:00:00

`YAML` *must* also contain `__default__` section which will be used for phases with no corresponding section, for instance:

.. code-block:: yaml

    __default__:
        salloc: '-A proj68 -p prod_small --time 0:15:00'


Tips & Tricks
-------------


After build is complete
~~~~~~~~~~~~~~~~~~~~~~~

Once circuit build is complete, we'd recommend to make its `bioname`, as well as the result circuit
files, read-only. You can also remove intermediate files and folders like `circuit.<suffix>.h5`
or `connectome/<type>/spykfunc`.
