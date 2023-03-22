How to create a new circuit build
=================================

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

.. warning::
    Please use the bb5 modules when possible.

**Locally**

.. code-block:: bash

    $ git clone git@bbpgitlab.epfl.ch:nse/circuit-build.git
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

Since version 4.0.0, ``circuit-build`` provides two options useful for reporting:

- ``--with-summary``: it will save a tab-separated summary in ``logs/<timestamp>/summary.tsv``
  (it wraps the ``--detailed-summary`` option of Snakemake).
- ``--with-report``: it will save a html report in ``logs/<timestamp>/report.html``
  (it wraps the ``--report`` option of Snakemake).

Further on we assume that you use `circuit-build run` command which is executed from the circuit's
release folder root.

`circuit_build/snakemake/Snakefile` contains many ready to use recipes that allow you to generate
any part of a circuit. Such recipes are called phases in `snakemake`. Usually it is a name of a
circuit file you want to generate. To choose a phase, type its name at the end of
`circuit-build run` call. For example:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml phase-name

For more detailed examples of phases see below. For more predefined phases see :ref:`ref-phases`.
To get an absolute path to `circuit_build/snakemake/Snakefile` type:

.. code-block:: bash

    $ circuit-build snakefile-path


Custom modules
~~~~~~~~~~~~~~

.. warning::

    Deprecated, see how to define custom environments :ref:`here <ref-environments>`.

To use custom modules for `circuit_build/snakemake/Snakefile` you can specify them
inside ``MANIFEST.yaml`` in a separate section named ``modules``,
as a list of strings using the format ``<module_env>:<module_names>`` or
``<module_env>:<module_names>:<optional_module_path>``, where:

- *module_env* is the name of the environment used in a specific phase.
- *module_names* is a comma-separated list of modules to be loaded.
- *optional_module_path* is the module path where to search the modules specified in *module_names*.
  If omitted, a default value is used.

Example:

.. code-block:: yaml

    modules:
      - brainbuilder:archive/2020-08,brainbuilder/0.14.0
      - touchdetector:archive/2020-05,touchdetector/5.4.0,hpe-mpi
      - spykfunc:archive/2020-06,spykfunc/0.15.6:/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta

Alternatively, you can specify the custom modules from the command line, but this option is
intended for internal or experimental use.


Cell collection
~~~~~~~~~~~~~~~

To build a minimal circuit (SONATA + target definitions) execute:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml

After the command above has completed, the following files could be found in circuit folder:

::

    circuit.h5

At this point the circuit is partially complete and should be readable by
`BluePy <https://bbpteam.epfl.ch/documentation/projects/bluepy/latest/index.html>`_ for analysis not
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


.. raw:: html

    <details open>
    <summary>Functional</summary>

.. image:: ../build/graphs/functional.svg
    :target: _images/functional.svg

.. raw:: html

    </details>


Spatial indices
~~~~~~~~~~~~~~~

To build *segment* spatial index:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml spatial_index_segment

Segment spatial index requires only cell collection, and thus can be built prior to connectome
(or in parallel with it).

.. raw:: html

    <details open>
    <summary>Spatial index segment</summary>

.. image:: ../build/graphs/spatial_index_segment.svg
    :target: _images/spatial_index_segment.svg

.. raw:: html

    </details>


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
    They do not conflict with each other, but share the common files (`circuit.h5`, `node_sets.json` etc).
    Structural circuit would be available via `struct_circuit_config.json` file.

.. raw:: html

    <details open>
    <summary>Structural</summary>

.. image:: ../build/graphs/structural.svg
    :target: _images/structural.svg

.. raw:: html

    </details>


Subcellular
~~~~~~~~~~~

To assign gene expressions and protein concentrations to the cells:

.. code-block:: bash

    $ circuit-build run --bioname /path/to/bioname --cluster-config /path/to/cluster.yaml subcellular

.. raw:: html

    <details open>
    <summary>Subcellular</summary>

.. image:: ../build/graphs/subcellular.svg
    :target: _images/subcellular.svg

.. raw:: html

    </details>


.. _ref-cluster-config:

Cluster config
--------------

By default `snakemake` launches all the tasks locally. To use *cluster mode* (i.e. launch every
task in a separate Slurm allocation) one has to provide YAML file with allocation parameters for
each phase. Such file is required by `circuit-build run` command.

.. code-block:: bash

    $ snakemake --cluster-config cluster.yaml ...

To specify a Slurm allocation for a phase, find the phase in the used `Snakefile`. For example,
a phase 'touchdetector' in the default `Snakefile`:

.. code-block::

    rule touchdetector:
    message:
        "Detect touches between neurites"

    ...

    shell:
        bbp_env(
            ...
            slurm_env='touchdetector'
        )

Find the used value for ``slurm_env`` argument. This value must be used in `cluster.yaml`. For
'touchdetector' it is the same string 'touchdetector', so `cluster.yaml` should contain an entry
like:

.. code-block:: yaml

    touchdetector:
        jobname: td
        salloc: '-A proj68 -p prod --constraint=cpu -n100 --time 1:00:00'

- ``jobname`` is optional. If omitted, the Slurm job will use the entry name.
- ``salloc`` specifies the necessary parameters for the job allocation.
  Sometimes it can be convenient to use a multi-line string for the ``salloc`` key,
  as in the following example:

.. code-block:: yaml

    touchdetector:
        jobname: td
        salloc: >-
            -A proj68
            -p prod
            --constraint=cpu
            -n100
            --time 1:00:00

- It's also possible to specify ``env_vars`` to set some environment variables before allocating the job,
  as in this example:

.. code-block:: yaml

    synthesize_morphologies:
        jobname: synthesize_morphologies
        salloc: '-A proj68 -p prod_small --constraint=cpu -n20 --time 1:00:00'
        env_vars:
            NEURON_MODULE_OPTIONS: "-nogui"


The `YAML` file *must* also contain a `__default__` section which will be used for phases
without a corresponding section, for instance:

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
