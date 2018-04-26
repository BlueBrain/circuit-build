.. _ref-phases:

Circuit building phases
=======================

.. _ref-phase-place-cells:

place_cells
-----------

Generate cell positions; assign cell orientations and properties.

Properties assigned (in addition to position and orientation):
    - *region*
    - *mtype*
    - *etype*
    - *morph_class*
    - *synapse_class*
    - *layer* [if requested]
    - *hypercolumn* [if requested]

Parameters
~~~~~~~~~~

**density_factor**
    Multiply all mtype densities specified in the cell composition recipe by the given recipe.

    Optional; if omitted, mtype densities are used as-is.

**soma_placement**
    Soma placement method used by `brainbuilder`.

    Could be either *basic* for uniform random placement; or *poisson_disc* for `Poisson disc sampling <https://bbpteam.epfl.ch/project/spaces/display/BBPNSE/On+sampling+methods+to+generate+cell+positions>`_.

**assign_column**
    Add *hypercolumn* property to MVD3 (applicable for mosaic atlases only)

    Optional; if omitted, defaults to *false*.

**assign_layer**
    Add *layer* property to MVD3 (applicable for cortex atlases only)

    Optional; if omitted, defaults to *false*.

**seed**
    Pseudo-random generator seed.

.. warning::

    This phase consumes amount of memory proportional to atlas size times number of mtypes.

    Please consider increasing your allocation memory limit if your are facing "out of memory" errors.

.. _ref-phase-assign-morphologies:

assign_morphologies
-------------------

Assign morphologies to cell positions using `placement hints <https://bbpteam.epfl.ch/documentation/placement-algorithm-1.0/index.html>`_ approach.

Parameters
~~~~~~~~~~

**resolution**
    Cluster cell positions by Y-value with given resolution in micrometers.

    Use this value to speed up morphology scoring;

    *resolution=10* usually provides a good trade-off between execution speed and score precision.


**layers**
    List of layer names (from 'bottom' to 'top').

    For instance, ['L6', 'L5', 'L4', 'L3', 'L2', 'L1']

**layer_ratio**
    List of relative layer thickness (in the order specified by **layers**).

**alpha**
    Use `score ** alpha` as morphology choice probability.

**ntasks**
    Number of Spark tasks to use for scoring.

**seed**
    Pseudo-random generator seed.

.. _ref-phase-assign-emodels:

assign_emodels
--------------

Add *me_combo* property to MVD3.

Parameters
~~~~~~~~~~

**seed**
    Pseudo-random generator seed.

targetgen_mvd3
--------------

Generate *start.target* file.

.. _ref-phase-touchdetector:

touchdetector
-------------

Write sbatch script for running `TouchDetector <https://bbpteam.epfl.ch/documentation/touchdetector-4.3.1-2017.10dev/index.html>`_ on BlueGene.

Parameters
~~~~~~~~~~

**account**
    SBATCH_ACCOUNT

**partition**
    SBATCH_PARTITION

**nodes**
    SBATCH_NNODES

**ntasks**
    SBATCH_NTASKS

**time**
    SBATCH_TIMELIMIT

.. _ref-phase-s2f:

s2f
---

Write sbatch script for running `Functionalizer <https://bbpteam.epfl.ch/documentation/functionalizer-3.11.0/index.html>`_ on BlueGene (with synapse pruning **enabled**).

Parameters
~~~~~~~~~~

**account**
    SBATCH_ACCOUNT

**partition**
    SBATCH_PARTITION

**nodes**
    SBATCH_NNODES

**ntasks**
    SBATCH_NTASKS

**time**
    SBATCH_TIMELIMIT

.. _ref-phase-s2s:

s2s
---

Write sbatch script for running `Functionalizer <https://bbpteam.epfl.ch/documentation/functionalizer-3.11.0/index.html>`_ on BlueGene (with synapse pruning **disabled**).

Parameters
~~~~~~~~~~

**account**
    SBATCH_ACCOUNT

**partition**
    SBATCH_PARTITION

**nodes**
    SBATCH_NNODES

**ntasks**
    SBATCH_NTASKS

**time**
    SBATCH_TIMELIMIT


transcriptome
-------------

Assign gene expressions to cells.

Parameters
~~~~~~~~~~

**db**
    HDF5 file with gene expressions database.

**seed**
    Pseudo-random generator seed.

Gene expressions database HDF5 file has the following layout:

::

    \library
        -- expressions [N x M, float32]
        -- genes [M x 1, string]
    \mapping
        -- by_mtype
        ---- <mtype1> [K(<mtype1>), int32]
        ---- <mtype2> [K(<mtype2>), int32]
        ...

where:

  * ``N`` is the total number of gene expression vectors
  * ``M`` is the length of each expression vector (number of genes)
  * ``K(mtype)`` is the number of expressions corresponding to a given *mtype*.

Each ``/mapping/by_mtype/<mtype>`` dataset contains row indices in ``/library/expressions`` corresponding to a given mtype.
