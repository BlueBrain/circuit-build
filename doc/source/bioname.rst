.. _ref-bioname:

Bioname: circuit build recipes
==============================

The following parts should define a *reproducible* circuit release:
 * `bioname`, a folder with recipe files specifying me-type composition, mtype density profiles, connectome parameters etc.
 * external `entities`, like morphology release or electrical model release
 * workflow definition, at the moment based on `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_

Eventually `bioname` and `entities` would become `Nexus`-stored entities in a strict sense (i.e.
validated against some schema, immutable, accessible by URL). At the moment these are files
stored at specified paths on GPFS. Since version 3.1.3 `bioname` **must be under GIT version
control.**

Let us describe the contents of `bioname` in more detail now. For a full example of `bioname` see
also: :ref:`ref-faq-bioname`


Bioname
-------

We address the folder for storing circuit build recipes as circuit `bioname`.

Absolute path to this folder is put to CircuitConfig *BioName* attribute.

In particular, the following files should be placed there:

* ``MANIFEST.yaml``
* ``cell_composition.yaml``
* ``mtype_taxonomy.tsv``
* ``extNeuronDB.dat``
* ``placement_rules.xml``
* ``builder[Connectivity]RecipeAllPathways.xml``

Optionally, `bioname` can also contain YAML files with cell target definitions. If used, these should be referenced from :ref:`ref-phase-targetgen` section in ``MANIFEST.yaml``.


MANIFEST.yaml
~~~~~~~~~~~~~

This is the main configuration for the circuit build defining:

* atlas space
* morphology release
* electrical model release
* S/W modules version
* individual task parameters

It starts with a `common` section:

.. code-block:: yaml

    common:
        atlas: http://voxels.nexus.apps.bbp.epfl.ch/api/analytics/atlas/releases/77831ACA-6198-4AA0-82EF-D0475A4E0647
        region: 'SSp-ll'
        mask: 'left-hemisphere'
        morph_release: /gpfs/bbp.cscs.ch/project/proj59/entities/morphologies/2017.10.31
        emodel_release: /gpfs/bbp.cscs.ch/project/proj64/entities/emodels/2017.11.03
        node_population_name: 'All'
        edge_population_name: 'All'

and follows with separate sections for each phase.

We'll provide a short description for each of the `common` values here.
Please refer to :ref:`ref-phases` for each phase config description.

**atlas**
    Atlas URL in VoxelBrain or local folder path.

**region**
    Optional Parameter.

    Defines the Atlas Region to populate (must be a subset of the atlas).

    If omitted, the region mask is not applied.

**mask**
    Optional Parameter.

    Defines a volumetric mask to populate (must be a subset of the atlas).

    | If provided, looks for the corresponding dataset in the atlas.
    | Could be used both with or without **region** (in the former case, two masks are intersected).

    If omitted, the volumetric mask is not applied.

**morph_release**
    Path to morphology release folder.
    It should contain:

    * ``h5v1`` folder with morphologies in H5v1 format
    * ``ascii`` folder with morphologies in ASC format
    * ``annotations.json`` file with compacted annotations used for placement, created with `compact-annotations` in the `placement-algorithm` module

.. tip::

  Since `morph_release` entity is not properly formalized yet, different tools might have different opinion how ``h5v1`` folder should be named. To be on a safe side, we recommend providing also ``h5`` and ``v1`` *aliases* in addition to ``h5v1``.


**emodel_release**
    Path to emodel release folder. It should contain:

    * ``hoc`` folder with model HOC templates
    * ``mecombo_emodel.tsv`` file with *me_combo* parameters


**node_population_name**
    Name of Sonata nodes population to produce. It *should* follow the naming guidelines in the
    `documentation <https://bbpteam.epfl.ch/documentation/projects/Circuit%20Documentation/latest/sonata_population.html#nodes>`_.
    Additionally this name will be used for the parent folder of the produced Sonata nodes file under
    `sonata/networks/nodes/` folder.


**edge_population_name**
    Name of Sonata edges population to produce. It *should* follow the naming guidelines in the
    `documentation. <https://bbpteam.epfl.ch/documentation/projects/Circuit%20Documentation/latest/sonata_population.html#edges>`_.
    Additionally this name will be used for the parent folder of the produced Sonata nodes file under
    `sonata/networks/edges/` folder.


An example of full ``MANIFEST.yaml``:

.. literalinclude:: ../../tests/proj66-tiny/MANIFEST.yaml
   :language: yaml

If **emodel_release** is not specified then the circuit will be built without emodels. It is strongly
recommended to always specify this property.

cell_composition.yaml
~~~~~~~~~~~~~~~~~~~~~
YAML file which defines which mtypes are used, their density and associated etypes.

.. note::

  We are versioning the YAML schema used, to provide minimal software / recipe compatibility check here. Once the recipe schema stabilizes and becomes an "entity", it would be checked more rigorously.

  At the moment we are at version 2.0; please specify this on top of YAML file with ``version: 2.0`` element.

How the recipe is organized:

* cell composition is represented as "flat" collection of cell groups within root ``neurons`` element
* each cell group should have ``mtype``, ``etype`` and ``layer`` traits, which should correspond to those used in the morphology release
* each of the "traits" can be either a single value or 'value -> probability' mapping (probabilities should sum up to 1.0)
* at the moment mappings are used mostly for defining etypes for each group
* location is prescribed with two required attributes: ``density`` and ``region``
* ``region`` is used for building region mask based on ``brain_regions`` atlas dataset + region hierarchy, by matching against region *acronym*. If ``region`` starts with '@' it is interpreted as regular expression (for instance, ``@1$`` stands for "acronym ends with '1'")
* ``density`` could be either a scalar value or a reference to atlas dataset encoded as ``{<dataset-name}``
* if ``density`` is a scalar value, region mask defines where to apply this constant density
* otherwise, if ``density`` is a volumetric dataset, all values outside of region mask are set to 0
* cell groups are built independent of each other (and thus are cumulative)

Example:

.. code-block:: yaml

    version: v2.0
    neurons:

      - density: '{L23_MC}'
        region: '@3$'
        traits:
          layer: 3
          mtype: L23_MC
          etype:
            bAC: 0.7
            bNAC: 0.3
          ...

      - density: 10000
        ...


Used in :ref:`ref-phase-place-cells` phase.


mtype_taxonomy.tsv
~~~~~~~~~~~~~~~~~~

A tab-separated file mapping mtypes to their morph class (Interneuron / Pyramidal) and synapse class (Excitatory / Inhibitory).

Example:
::

    mtype       mClass  sClass
    L23_NGC     INT     INH
    L23_SBC     INT     INH
    L2_IPC      PYR     EXC

Used in :ref:`ref-phase-place-cells` phase.


extNeuronDB.dat
~~~~~~~~~~~~~~~

A tab-separated file storing a table with `morphology`, `region`, `mtype`, `etype`, `me-combo` combinations.

Should be compatible with morphology and emodel releases used; most often is a subset of a similar file produced as a part of emodel release (i.e. the output of BluePyMM).

Example:
::

  C230998A-I3           2 L23_BP bAC bAC_L23BTC_L23_BP_2_C230998A-I3
  C230998A-I3_-_Clone_0 2 L23_BP bAC bAC_L23BTC_L23_BP_2_C230998A-I3_-_Clone_0

If emodel release is not yet available, one can obtain a stub version of `extNeuronDB.dat` from morphology release `neuronDB.dat` file and cell composition recipe:

.. code-block:: bash

  $ pip install -i https://bbpteam.epfl.ch/repository/devpi/simple/ nse-tools
  $ stub-extneurondb -r <path recipe> <path neuronDB.dat> -o extNeuronDB.dat

This will create `extNeuronDB.dat` in the current folder with all possible me-type combinations being assigned `N/A` me_combo.

Used in :ref:`ref-phase-choose-morphologies` and :ref:`ref-phase-assign-emodels` phases.


placement_rules.xml
~~~~~~~~~~~~~~~~~~~

An XML file defining how to use morphology annotations for scoring morphology placement.

Used in :ref:`ref-phase-choose-morphologies` phase.


builderRecipeAllPathways.xml + builderConnectivityRecipeAllPathways.xml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This pair used to fully defined the circuit composition; now it is still relevant for building the connectome, **but no longer for defining cell composition**.

.. warning::
    Although ``<column>`` and ``<NeuronTypes>`` sections of ``builderRecipeAllPathways.xml`` are not used anymore for defining cell composition, they still have to be specified for ``builderRecipeAllPathways.xml`` consumers to work properly. MType names should be consistent with that actually used in cell composition.

    We apologize for this inconvenience that is due to ongoing transition from column-based circuit building to atlas-based one.

Used in :ref:`ref-phase-touchdetector`, :ref:`ref-phase-spykfunc_s2f` and :ref:`ref-phase-spykfunc_s2s` phases.
Further documentation of the recipe is available in `Circuit Documentation <https://bbpteam.epfl.ch/documentation/projects/Circuit%20Documentation/latest/recipe.html>`_


.. _ref-bioname-targets:

Target definitions (YAML)
~~~~~~~~~~~~~~~~~~~~~~~~~

Custom targets to be added to the circuit. During circuit build, they are resolved into named GID sets stored in ``start.target``.

At the moment we support only query-based target definitions. These should be defined inside ``targets/query_based`` section as mappings with `BluePy-like <https://bbpteam.epfl.ch/documentation/bluepy-0.13.5/circuit.html#cells-get>`_ cell property filters.

Example:

.. literalinclude:: ../../tests/proj66-tiny/targets.yaml
   :language: yaml

.. note::
  These query-based target definitions can be considered a stepping stone towards *node sets files* which would define cell subsets in the forthcoming `SONATA <https://github.com/AllenInstitute/sonata/blob/master/docs/SONATA_DEVELOPER_GUIDE.md>`_ circuit format.
