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
    We strongly recommend to keep `bioname` content under VCS, one way or another; and to reference a read-only snapshot of it for the released circuits.

    An approach taken in `proj1` and `proj42` is to store all bionames in git-controlled ``<proj>/entities/bionames/`` folder and symlink the corresponding one from circuit build folder.

3. Get a snapshot of circuit building pipeline:

.. code-block:: bash

    $ git clone ssh://bbpcode.epfl.ch/common/circuit-build

4. Make `snakemake` command available.

On vizcluster `snakemake` is available as a module:

.. code-block:: bash

    $ module load nix/py36/snakemake

Alternatively, it can be pip-installed in any Python 3.5+ virtual environment:

    $ pip install snakemake

`snakemake` could run the tasks locally or automatically allocate SLURM partition for each task based on the provided `cluster config <http://snakemake.readthedocs.io/en/latest/snakefiles/configuration.html#cluster-configuration>`_.

For simplicity we will use local operational mode throughout the tutorial. We will also assume that all the commands below are executed on a vizcluster allocation similar to:

.. code-block:: bash

    $ salloc -A proj64 -p prod --mem 32G --time 8:00:00 --cpus-per-task 8

Specifying ``--cpus-per-task`` would allow to run circuit building phases in parallel where possible.

.. note::
    Please note that a the moment "supercomputer" phases (`touchdetector`, `functionalizer`) are launched manually.
    Once "supercomputer" and "conventional" clusters would be combined into single one, it would be no longer necessary. At that point we'll simplify the pipeline description and update the instructions here accordingly.

For all the commands below we assume that a following alias is defined:

.. code-block:: bash

    $ alias sm='snakemake --config bioname=<path-to-bioname> --snakefile <circuit-build>/snakemake/Snakefile'

We also assume that all ``sm`` commands are executed from circuit release folder root.


Cell collection
---------------

To build a minimal circuit execute:

.. code-block:: bash

    $ sm

To execute up to 4 phases in parallel:

.. code-block:: bash

    $ sm -j4

After the command above has completed, the following files could be found in circuit folder:

::

    CircuitConfig
    circuit.mvd3
    connectome/functional/start.target -> ../../start.target
    start.target

At this point the circuit is partially complete and should be readable by `BluePy <https://bbpcode.epfl.ch/documentation/bluepy-0.11.11/index.html>`_ for analysis not involving connectome.

There are also intermediate MVD3 files, dumped after each phase:

::

    circuit.mvd3.metypes
    circuit.mvd3.morphologies
    circuit.mvd3.emodels

These could be safely removed, should you not need them. We recommend to keep them however, at least until the circuit build is finalized to speed up potential rebuilds.

Now we can prepare sbatch scripts for building the connectome:

.. code-block:: bash

    sm sbatch

This would create three sbatch scripts to be executed on BlueGene (see the next section):

::

    connectome/touches/run.sbatch
    connectome/structural/run.sbatch
    connectome/functional/run.sbatch

In parallel with launching these scripts, we can start segment spatial index build (on vizcluster):

.. code-block:: bash

    sm spatial_index_segment

.. note::
    Spatial index is more demanding to computing resources than all the other steps run at vizcluster.
    Please either launch `Snakemake` in `cluster mode <http://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration>`_ or get a larger SLURM allocation by hand:

    .. code-block:: bash

        $ ssh bbpviz2.cscs.ch
        $ cd <circuit-dir>
        $ salloc -A <proj> -p prod --mem 120G --time 3-00:00:00 --cpus-per-task 16 --exclusive
        $ sm spatial_index_segment


Connectome - BlueGene
---------------------

The next two phases are executed on BlueGene.

.. code-block:: bash

    $ ssh bbpbg1.cscs.csh

For these phases no `snakemake` environment is needed, it is enough to `sbatch` the scripts prepared at previous step.

First `touchdetector`:

.. code-block:: bash

    $ sbatch <circuit-dir>/connectome/touches/run.sbatch

Once `touchdetector` has successfully finished, `functionalizer`:

.. code-block:: bash

   $ sbatch <circuit-dir>/connectome/functional/run.sbatch

To avoid waiting for `touchdetector`, one can queue `functionalizer` right away:

.. code-block:: bash

   $ sbatch -d afterok:<touchdetector Slurm job ID> <circuit-dir>/connectome/functional/run.sbatch


Connectome - vizcluster
-----------------------

Once `functionalizer` run on BlueGene has successfully finished, we can go back to executing `Snakemake` on vizcluster:

.. code-block:: bash

    $ sm -j8 functional

would finish building functional circuit (merging the output of `functionalizer` etc).

At this point any analysis not involving spatial indices should be possible.

Finally, to obtain synapse spatial index:

.. code-block:: bash

    $ sm spatial_index_synapse

which should give you a complete functionalized circuit with all the files described in :ref:`ref-circuit-files` section.

.. tip::

    .. code-block:: bash

        $ sm functional_all

    would ensure that `functional` as well as `spatial_index_[segment|synapse]` phases are complete.

.. tip::

    Once circuit build is complete, we'd recommend to make its `bioname`, as well as the result circuit files, read-only.

    If you've merged NRN files by copy (default mode), you can also remove ``nrn*.h5.*`` chunk files from ``connectome/functional/``.


Structural circuit
------------------

If you'd like to build a structural circuit instead of functional one (i.e., avoid pruning synapses when executing `functionalizer`), on BlueGene execute:

.. code-block:: bash

   $ sbatch <circuit-dir>/connectome/structural/run.sbatch

instead of:

.. code-block:: bash

   $ sbatch <circuit-dir>/connectome/functional/run.sbatch

; and afterwards:

.. code-block:: bash

    $ sm -j8 structural

instead of:

.. code-block:: bash

    $ sm -j8 functional

on vizcluster.

.. note::
    You can also build structural circuit *in addition* to the functional one. They do not conflict with each other, but share the common files (``circuit.mvd3``, ``start.target`` etc). Structural circuit would be available via ``CircuitConfig_struct`` file.


Tips & Tricks
-------------

How to speed up NRN merging?
----------------------------

By default NRN files produced by `functionalizer` are merged by copying their content to the merged file.

Instead one can produce a merged file using HDF5 *external links*. This could be less robust, but reduces significantly time needed to produce merged files (which could be particularly useful for structural circuits). To instruct `snakemake` to merge NRN files by linking use:

.. code-block:: bash

    $ sm -j8 structural --config nrn_merge=link

instead of:

.. code-block:: bash

    $ sm -j8 structural
