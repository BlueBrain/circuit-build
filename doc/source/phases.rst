.. _ref-phases:

Circuit building phases
=======================

.. _ref-phase-init-cells:

init_cells
----------

Generate an empty cell collection in Sonata format. Hereinafter referred to as *Cells*.


.. _ref-phase-place-cells:

place_cells
-----------

Provisions *Cells* with cells positions, orientations and properties.

Properties assigned (in addition to position and orientation):
    - *region*
    - *layer*
    - *mtype*
    - *etype*
    - *morph_class*
    - *synapse_class*

Handled by `BrainBuilder`_: ``brainbuilder cells place``.

Parameters
~~~~~~~~~~

**density_factor**
    Multiply all mtype densities specified in the cell composition recipe by the given recipe.

    Optional; if omitted, mtype densities are used as-is.

**soma_placement**
    Soma placement method used by `BrainBuilder`.

    Could be either *basic* for uniform random placement; or *poisson_disc* for `Poisson disc sampling <https://bbpteam.epfl.ch/project/spaces/display/BBPNSE/On+sampling+methods+to+generate+cell+positions>`_.

**atlas_property**
    Properties to assign based on auxiliary volumetric datasets.

    More specifically, it is a mapping like:

    ::

        place_cells:
            ...
            atlas_property:
                hypercolumn: 'column'
                region: '~brain_regions'


    where key is the property name to use in *Cells* (``hypercolumn``, ``region`` in the example above), and value is the name of volumetric dataset to query (``column``, ``brain_regions``).
    The corresponding atlas dataset would be queried at cell positions, and the result values would go to *Cells*.
    If dataset name is prefixed with ``~``, values from the dataset would be interpreted as region IDs and re-mapped to region acronyms using atlas ``hierarchy.json``.

    This mechanism provides flexibility in choosing how to assign ``region`` property in *Cells*.
    For instance, when building a model of Neocortex, one can opt for assigning ``region`` without layers (i.e., ``SSp-ll`` instead of ``SSp-ll[1-6]``.
    It also allows to embed additional properties like cell position in brain region-specific coordinate system; or column ID for artificial mosaic circuits.

    .. warning::

        | Please note that it's mandatory to define ``region`` property.
        | For backwards compatibility, if **atlas_property** section is missing from ``MANIFEST.yaml``, it will default to ``{'region': '~brain_regions'}``.

**append_hemisphere**
    Neocortex-specific flag.

    | If set to ``True``, ``hemisphere`` values would be appended to ``region`` (i.e., ``SSp-ll@left`` instead of ``SSp-ll``).
    | ``region`` and ``hemisphere`` should be specified using **atlas_property** mechanism.

**sort_by**
    Sort *Cells* by properties values.

    | A list of properties is anticipated (e.g., ``['region', 'mtype']``).
    | If omitted, cells are not sorted in any particular order

**seed**
    Pseudo-random generator seed.

.. tip::

    This phase consumes amount of memory proportional to atlas size times number of mtypes.

    Please consider increasing allocation memory limit if you are facing "out of memory" errors.


.. _ref-phase-choose-morphologies:

choose_morphologies
-------------------

Choose morphologies for cell positions using `placement_algorithm`_ ``choose-morphologies``.
This creates the ``morphologies.tsv`` described `here <https://bbpteam.epfl.ch/documentation/placement-algorithm-2.0.8/index.html#choose-morphologies>`_.

.. tip::

    This task requires at least a two task Slurm allocation.

    Please make sure you define it in the cluster config accordingly: ie ``-n2``

    Also, the memory requirements vary according to the atlas, please follow the process like in :ref:`place_cells <ref-phase-place-cells>`.

    Scaling should be good, so if this phase is running slow, increasing the number of Slurm tasks will help.


Parameters
~~~~~~~~~~

**alpha**
    Use `score ** alpha` as morphology choice probability.

**seed**
    Pseudo-random generator seed.


.. _ref-phase-assign-morphologies:

assign_morphologies
-------------------

Assign morphologies chosen with `choose_morphologies`_ to *Cells* using the `placement_algorithm`_ ``assign-morphologies``.

**max_drop_ratio**
    | Maximal ratio of positions that can be dropped for each mtype (due to failure to pick an morphology).
    | Optional, if not provided, defaults to 0.0 (i.e., no position dropping allowed).


.. _ref-phase-assign-emodels:

assign_emodels
--------------

Add *me_combo* property to *Cells*. If **emodel_release** is not specified in ``MANIFEST.yaml`` then
this phase is skipped and the final circuit is not guaranteed to run a simulation.

Handled by `BrainBuilder`_: ``brainbuilder cells assign-emodels``.

Parameters
~~~~~~~~~~

**morphdb**
    Path to ``extNeuronDB.dat``.


.. _ref-phase-provide-me-info:

provide_me_info
---------------

Provide *Cells* with MorphoElectrical info and saves them as Sonata nodes.

Handled by `BrainBuilder`_: ``brainbuilder sonata provide-me-info``.

Parameters
~~~~~~~~~~

**mecombo-info**
    Path to TSV file with ME-combo table".

**model-type**
    Sonata nodes 'model_type' property to set on the output Sonata nodes.

.. _ref-phase-targetgen:

targetgen
---------

Generate *start.target* file.
Handled by `BrainBuilder`_: ``brainbuilder targets from-input``.

Targets generated by default:

* `All`
* `Excitatory` / `Inhibitory`
* `X` for each value `X` of ``mtype`` property
* `X` for each value `X` of ``etype`` property

If **targets** parameter is not specified, following targets are added for backwards compatibility:

* `Layer<X>` for each value `X` of ``layer`` property
* `mc<X>_Column` for each value `X` of ``hypercolumn`` property (if present in *Cells*)

Parameters
~~~~~~~~~~

**targets**
    :ref:`Target definitions <ref-bioname-targets>` file to use for generating ``start.target``.

    Should be located in ``bioname`` folder.

**allow_empty**
    Allow query-based targets to resolve to empty GID set.

    Optional; if omitted, defaults to *false*.


.. _ref-phase-touchdetector:

touchdetector
-------------

Detect touches between neurites using `TouchDetector`_.

.. tip::

    Recommended Slurm allocation (time limit and number of tasks depends on circuit size):

    ::

        -A <proj> -p prod --constraint=cpu -n<tasks> --time <time>

.. warning::

    Unlike nost other phases, ``TouchDetector`` is stateful: i.e., during the run it writes checkpoints to the disk, and automatically resumes from those on restart.

    While it saves a lot of computational time in regular cases when resume from checkpoint is desirable, beware to clean up ``connectome/touches`` folder when you restart `TouchDetector` knowing some input (including `TouchDetector` version itself) has changed.


.. _ref-phase-touch2parquet:

touch2parquet
-------------

Convert touches to Parquet format (to use as input for `Spykfunc`_).

.. tip::

    We use MPI-enabled version of the converter; thus it is beneficial to configure an allocation with multiple tasks.
    For instance, the `salloc` key could include:

    ::

        -A <proj> -p prod --constraint=cpu -n200 --time <time>

    as described in `touch2parquet salloc recommendation`_.

.. _ref-phase-spykfunc_s2f:

spykfunc_s2f
------------

Prune touches and convert them into synapses (S2F) using the `Spark Functionalizer`.

.. note::

    Unlike most other phases, pseudo-random generator seed for ``spykfunc_s2f`` phase is not specified in ``MANIFEST.yaml``, but taken from ``builderRecipeAllPathways.xml`` recipe (``synapseSeed`` attribute of ``<Seeds>`` element).

.. tip::

    Recommended Slurm allocation (time limit and number of nodes depend on circuit size):

    ::

        -A <proj> -p prod --constraint=nvme -N<nodes> --exclusive --mem 0 --time <time>

To provide additional arguments to ``sm_run``, put those to the :ref:`cluster config <ref-cluster-config>`.
For instance, to disable HDFS mode:

::

    spykfunc_s2f:
        salloc: ...
        sm_run: '-H'

Please refer to the `Spykfunc`_ documentation for the details.

.. note::

   An experimental feature exists to control which filters are used.
   They can be specified with the key 'filters' with a list of filter names in the spykfunc_s2\* stanza in the ``MANIFEST.yaml``.
   See `FUNCZ-208 <https://bbpteam.epfl.ch/project/issues/browse/FUNCZ-208>`_ for more details


.. _ref-phase-spykfunc_s2s:

spykfunc_s2s
------------

Analogous to ``spykfunc_s2f``, but does not prune touches.

.. _ref-phase-parquet2syn2:

parquet2syn2
------------

Convert the `Spykfunc`_ output to SYN2 format.

.. tip::

    We use MPI-enabled version of the converter; thus it is beneficial to configure an allocation with multiple tasks.


.. _ref-phase-subcellular:

subcellular
-----------

Assign gene expressions / protein concentrations to cells.
Handled by `BrainBuilder`_: ``brainbuilder assign``.

Configuration
~~~~~~~~~~~~~~

Since this phase uses the ``entity_management`` package to draw data from Nexus, it is
mandatory to set correctly your Nexus environment variables:

-  NEXUS_TOKEN to "Bearer XXX" with XXX your nexus token from the explorer's `copy token` facility
-  NEXUS_ORG to "ngv" to be able to work inside the ngv project

.. tip::
    To do so with bash just do:

    .. code:: bash

        export NEXUS_TOKEN="Bearer <my_copied_token>"
        export NEXUS_ORG="ngv"

Parameters
~~~~~~~~~~

From now on, the data parameters are directly drawn from Nexus. The data are stored in the
``synprot`` domain (this will change in the future).

.. warning::
    These data should have been uploaded in Nexus using the ``subcellular-querier``
    package. This process ensures that all data are compliant with the dedicated
    ``brainbuilder`` app.

    See: https://bbpteam.epfl.ch/documentation/subcellular-querier-0.0.3/index.html

To retrieve data from nexus, just provide the name of the nexus instance. The code will
automatically look into the correct schemas and download the attachment file.

**transcriptome**
    A Nexus *transcriptomeexperiment* instance with a CSV attachment file containing all the data
    related to gene expressions. The attachment file is formatted as follow.

    The first 10 rows should be ``tissue``, ``group #``, ``total mRNA mol``, ``well``, ``sex``,
    ``age``, ``diameter``, ``cell_id``, ``level1class``, ``level2class`` for each cells.
    Each column of this first table should be the corresponding values for all cells.

    The rows from 12 to the end should contain the corresponding gene expressions for each cells.

    The exact formatting must be:

    +----------+------------------+-------------------+-------------------+
    |          | tissue	          |   sscortex        |  sscortex         |
    +----------+------------------+-------------------+-------------------+
    |          |  group #         |   1               |  4                |
    +----------+------------------+-------------------+-------------------+
    |          |  total mRNA mol  |   21580           |  7267             |
    +----------+------------------+-------------------+-------------------+
    |          |  well            |   11              |  89               |
    +----------+------------------+-------------------+-------------------+
    |          |  sex             |   1               |  -1               |
    +----------+------------------+-------------------+-------------------+
    |          |  age             |   21              |  23               |
    +----------+------------------+-------------------+-------------------+
    |          |  diameter        |   0               |  10.8             |
    +----------+------------------+-------------------+-------------------+
    |          |  cell_id         |   1772071015_C02  |  1772071041_A12   |
    +----------+------------------+-------------------+-------------------+
    |          |  level1class     |   interneurons    |  oligodendrocytes |
    +----------+------------------+-------------------+-------------------+
    |          |  level2class     |   Int10           |  Oligo5           |
    +----------+------------------+-------------------+-------------------+
    |          |                  |                   |                   |
    +----------+------------------+-------------------+-------------------+
    | Tspan12  |        1         |        0          |         0         |
    +----------+------------------+-------------------+-------------------+
    | Tshz1    |        1         |        3          |         1         |
    +----------+------------------+-------------------+-------------------+
    | Fnbp1l   |        1         |        3          |         1         |
    +----------+------------------+-------------------+-------------------+
    | Adamts15 |        1         |        1          |         0         |
    +----------+------------------+-------------------+-------------------+

See:
https://bbp-nexus.epfl.ch/staging/explorer/ngv/synprot/transcriptomeexperiment/v0.1.0/550179e8-496a-44e7-be74-0fc2cc8f3c52
for a complete example.

**mtype-taxonomy**
    A *mtypetaxonomy* Nexus instance with a tsv attachment file containing the mapping mtypes
    to their morph class (Interneuron / Pyramidal) and synapse class (Excitatory / Inhibitory).

    For instance:

    +-----------+-----------+-----------+
    |  mtype    |   mClass  |   sClass  |
    +===========+===========+===========+
    |  L23_NGC  |   INT     |    INH    |
    +-----------+-----------+-----------+
    |  L23_SBC  |   INT     |    INH    |
    +-----------+-----------+-----------+
    |  L2_IPC   |   PYR     |    EXC    |
    +-----------+-----------+-----------+

    See:
    https://bbp-nexus.epfl.ch/staging/explorer/ngv/synprot/mtypetaxonomy/v0.1.0/f5c1beac-3245-48e6-8336-c2189a1c37be
    for a complete example.

**cell-proteins**
    A *cellproteinconcexperiment* Nexus instance with a tsv attachment file containing the
    concentration of each gene in each organelle.

    Columns correspond to the different organelle and rows to the different genes. The values
    are the concentrations in [nM] (nanomoles / litre) of each gene in each organelle as
    a floating point.

    As of today, the mandatory columns to provide are:

    - Lead gene name
    - Canonical lead protein ID
    - Majority protein IDs
    - Protein names
    - Median cellular concentration [nM]
    - Median Cytosol concentration [nM]
    - Median nuclear concentration [nM]
    - Median ER concentration [nM]
    - Median Endosome concentration [nM]
    - Median Golgi apparatus concentration [nM]
    - Median Lysosome concentration [nM]
    - Median Mitochondrion concentration [nM]
    - Median Peroxisome concentration [nM]
    - Median Plasma membrane concentration [nM]
    - Median Cytosol concentration [nM].1

    See:
    https://bbp-nexus.epfl.ch/staging/explorer/ngv/synprot/cellproteinconcexperiment/v0.1.5/fcb284f3-6143-46a6-a34a-3cd8ea7277ba
    for a complete example.

**synapse-proteins**
    A *synapticproteinconcexperiment* Nexus instance with a tsv attachment file containing the
    concentration of each gene inside the different kind of synapses.

    The attachment file must contain at least four columns:

    - gene names Linerson
    - PSD excitatory, #/um^2
    - PSD inhibitory, #/um^2
    - Presynaptic terminals, nM

    Rows correspond to the gene name and concentrations.

    Example:

    +-----------------------+---------------------------+--------------------------+-----------------------------+
    |  gene names Linerson  |   PSD excitatory, #/um^2  |  PSD inhibitory, #/um^2  | Presynaptic terminals, nM   |
    +=======================+===========================+==========================+=============================+
    |        Camk2a         |            24570          |             0            |               71950         |
    +-----------------------+---------------------------+--------------------------+-----------------------------+
    |        Camk2b         |             5730          |             0            |               17150         |
    +-----------------------+---------------------------+--------------------------+-----------------------------+


**seed**
    Pseudo-random generator seed.

Intermediate files
~~~~~~~~~~~~~~~~~~

Intermediate files will be created in a subcellular directory.
These HDF5 files will be used to create the `subcellular.h5` final file.


.. _BrainBuilder: https://bbpteam.epfl.ch/documentation/projects/brainbuilder
.. _placement_algorithm: https://bbpteam.epfl.ch/documentation/projects/placement-algorithm
.. _Spykfunc: https://bbpteam.epfl.ch/documentation/projects/spykfunc
.. _TouchDetector: https://bbpteam.epfl.ch/documentation/projects/TouchDetector
.. _touch2parquet salloc recommendation: https://bbpteam.epfl.ch/project/issues/browse/FUNCZ-215?focusedCommentId=90821
