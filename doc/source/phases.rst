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

.. tip::

    This phase consumes amount of memory proportional to atlas size times number of mtypes.

    Please consider increasing allocation memory limit if you are facing "out of memory" errors.


.. _ref-phase-assign-morphologies:

assign_morphologies
-------------------

Assign morphologies to cell positions using `placement hints <https://bbpteam.epfl.ch/documentation/placement-algorithm-1.1/index.html>`_ approach.

.. tip::

    This task uses ``$TMPDIR`` environment variable to configure temporary folder for Spark.

    Recommended SLURM allocation (time limit depends on circuit size, 2 hours should suffice for up to 10M cells):

    ::

        -A <proj> -p prod --constraint=nvme -N1 --exclusive --mem 0 --time <time>

Parameters
~~~~~~~~~~

**resolution**
    Cluster cell positions by Y-value with given resolution in micrometers.

    Use this value to speed up morphology scoring;

    *resolution=10* usually provides a good trade-off between execution speed and score precision.

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

Detect touches between neurites using `TouchDetector <https://bbpteam.epfl.ch/documentation/#touchdetector>`_.

.. tip::

    Recommended SLURM allocation (time limit and number of tasks depends on circuit size):

    ::

        -A <proj> -p prod --constraint=cpu -n<tasks> --time <time>


.. _ref-phase-s2f:

s2f
---

Prune touches and convert them into synapses using `Functionalizer <https://bbpteam.epfl.ch/documentation/#functionalizer>`_.


.. _ref-phase-s2s:

s2s
---

Analogous to ``s2f``, but does not prune touches.

.. _ref-phase-touch2parquet:

touch2parquet
-------------

Convert touches to Parquet format (to use as input for `Spark Functionalizer <https://bbpteam.epfl.ch/documentation/#spykfunc>`_).

.. tip::

    We use MPI-enabled version of the converter; thus it is beneficial to configure an allocation with multiple tasks.

.. _ref-phase-spykfunc_s2f:

spykfunc_s2f
------------

Prune touches and convert them into synapses (S2F) using `Spark Functionalizer <https://bbpteam.epfl.ch/documentation/#spykfunc>`_.

.. tip::

    Recommended SLURM allocation (time limit and number of nodes depend on circuit size):

    ::

        -A <proj> -p prod --constraint=nvme -N<nodes> --exclusive --mem 0 --time <time>

To provide additional arguments to ``sm_run``, put those to the :ref:`cluster config <ref-cluster-config>`.
For instance, to disable HDFS mode:

::

    spykfunc_s2f:
        salloc: ...
        sm_run: '-H'

Please refer to `Spark Functionalizer <https://bbpteam.epfl.ch/documentation/#spykfunc>`_ documentation for the details.


.. _ref-phase-spykfunc_s2s:

spykfunc_s2s
------------

Analogous to ``spykfunc_s2f``, but does not prune touches.

.. _ref-phase-parquet2syn2:

parquet2syn2
------------

Convert `Spark Functionalizer <https://bbpteam.epfl.ch/documentation/#spykfunc>`_ output to SYN2 format.

.. tip::

    We use MPI-enabled version of the converter; thus it is beneficial to configure an allocation with multiple tasks.


.. _ref-phase-subcellular:

subcellular
-----------

Assign gene expressions / protein concentrations to cells.

Parameters
~~~~~~~~~~

**gene-mapping**
    PyTables_ HDF5 file with single ``\gene_mapping`` table storing gene to protein correspondence.

    It has four columns:

      - ``gene`` with gene name
      - ``lead_protein`` with the name of the main protein associated with the gene
      - ``maj_protein`` with ';'-separated list of other proteins associated with the gene
      - ``comment`` with free-form optional comment

    For instance:

    +---------------+--------------+----------------------+----------------------------------+
    | gene          | lead_protein | maj_protein          | comment                          |
    +===============+==============+======================+==================================+
    | 0610011F06Rik | Q9DCS2       | Q9DCS2;E9Q7K5;G5E8X1 | UPF0585 protein C16orf13 homolog |
    +---------------+--------------+----------------------+----------------------------------+

**gene-expressions**
    PyTables_ HDF5 file with a collection of tables corresponding to different gene expressions.

    Tables are stored in the root ``\gene_expressions`` group; each of those has a unique identifier in this group.
    It is envisioned that eventually each of those tables will be a separate *entity instance* in Nexus data storage platform, which we can reference by its UUID.

    Each of those tables has two columns:
      - ``gene`` with gene name
      - ``expr`` with corresponding gene expression (floating point value)

    For instance:

    +--------+-----+
    | gene   |expr |
    +========+=====+
    | Tshz1  | 1.0 |
    +--------+-----+


    In addition, each table has an attribute ``mtype``, which stores '|'-separated list of mtypes "compatible" with a given gene expression (for instance, ``L1_DAC|L1_HAC``).

**cell-proteins**
    PyTables_ HDF5 file with a collection of tables corresponding to different cell proteins concentration measurements.

    Tables are stored in the root ``\cell_proteins`` group; similar to **gene-expressions** each of those tables is a "proto-entity".

    Each of those tables has nine columns corresponding to protein concentraion in each of cell organelles; plus ``total`` with protein concentration across all the cell.
    Concentrations are measured in nM (nanomoles / litre); missing values are encoded with ``NaN``.

    For instance:

    +---------------+--------+---------+---------+-----+----------+-------+----------+--------------+------------+----------+
    | gene          | total  | cytosol | nucleus | ER  | endosome | golgi | lysosome | mitochodrion | peroxisome | membrane |
    +===============+========+=========+=========+=====+==========+=======+==========+==============+============+==========+
    | 0610009B22Rik | 37.076 | NaN     | 1.729   | NaN | NaN      | NaN   | NaN      | NaN          | NaN        | NaN      |
    +---------------+--------+---------+---------+-----+----------+-------+----------+--------------+------------+----------+

**synapse-proteins**
    PyTables_ HDF5 file with a collection of tables corresponding to different synapse proteins concentration measurements.

    Tables are stored in the root ``\synapse_proteins`` group; similar to **gene-expressions** each of those tables is a "proto-entity".

    Each of those tables has three columns:

      - ``post_exc`` with protein *density* in excitatory synapses on postsynaptic side [count / um^2]
      - ``post_inh`` with protein *density* in inhibitory synapses on postsynaptic side [count / um^2]
      - ``pre`` with protein *concentration* on presynaptic side (without distinguishing synapse type) [nM]

    For instance:

    +---------------+----------+----------+-------+
    | gene          | post_exc | post_inh | pre   |
    +===============+==========+==========+=======+
    | 0610005C13Rik | 0.947    | 0.390    | 0.528 |
    +---------------+----------+----------+-------+

**seed**
    Pseudo-random generator seed.

.. warning::

    | It is assumed that gene namespace is same across all subcellular data sources;
    | though cell or synapse protein concentrations tables don't necessarily have *all* the genes.
    | It is up to data source provider to ensure that; ``circuit-build`` makes no extra effort to check that assumption.

.. note::

    | One can observe that source data layout is far from being optimal (for instance, "squashing" gene expressions collection into a single table could reduce the file size by ~20 times).
    | The main intent here is to provide an (experimental) uniform approach for storing the source data for gene expressions and cell / synapse protein concentrations, which could be later extended to using Nexus entities.


.. _PyTables: <https://www.pytables.org/>
