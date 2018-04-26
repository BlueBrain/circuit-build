.. _ref-bioname:

Bioname: circuit build recipes
==============================

The following parts should define a *reproducible* circuit release:
 * `bioname`, a folder with recipe files specifying me-type composition, mtype density profiles, connectome parameters etc.
 * external `entities`, like morphology release or electrical model release
 * workflow definition, at the moment based on `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_

Eventually `bioname` and `entities` would become `Nexus`-stored entities in a strict sense (i.e. validated against some schema, immutable, accessible by URL). At the moment though these are files stored at specified paths on GPFS.

Let us describe the contents of `bioname` in more detail now.


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


MANIFEST.yaml
~~~~~~~~~~~~~

Main config defining:
 * atlas space
 * morphology release
 * electrical model release
 * S/W modules version
 * individual task parameters

It starts with `common` section:

::

    common:
        atlas: http://voxels.nexus.apps.bbp.epfl.ch/api/analytics/atlas/releases/77831ACA-6198-4AA0-82EF-D0475A4E0647
        region_ids: [120]
        morph_release: /gpfs/bbp.cscs.ch/project/proj59/entities/morphologies/2017.10.31
        emodel_release: /gpfs/bbp.cscs.ch/project/proj64/entities/emodels/2017.11.03
        sw_release: 2018-04-06

and follows with a separate section for each phase.

We'll provide a short description for each of the `common` values here.
Please refer to :ref:`ref-phases` for each phase config description.

**atlas**
    Atlas URL in VoxelBrain or local folder path.

**region_ids**
    Region IDs to populate (to use only subset of the atlas).

    Optional; if omitted all atlas space would be used.

**morph_release**
    Path to morphology release folder.
    It should contain:

      * ``h5v1`` folder with morphologies in H5v1 format
      * ``ascii`` folder with morphologies in ASC format
      * ``annotations`` folder with morphology annotations used for placement

.. tip::

  Since `morph_release` entity is not properly formalized yet, different tools might have different opinion how ``h5v1`` folder should be named. To be on a safe side, we recommend providing also ``h5`` and ``v1`` *aliases* in addition to ``h5v1``.


**emodel_release**
    Path to emodel release folder.
    It should contain:

      * ``hoc`` folder with model HOC templates
      * ``mecombo_emodel.tsv`` file with *me_combo* parameters

**sw_release**
    `BBP archive S/W modules <https://bbpteam.epfl.ch/project/spaces/display/BBPHPC/BBP+ARCHIVE+SOFTWARE+MODULES>`_ to use.

.. tip::
    If `sw_release` is set to `null`, modules available in the current environment would be used. This feature is meant for development purposes; we strongly recommend to use some specific release for the "public" circuits.

An example of full ``MANIFEST.yaml``:

.. literalinclude:: ../../snakemake/examples/sscx/MANIFEST.yaml
   :language: yaml

cell_composition.yaml
~~~~~~~~~~~~~~~~~~~~~
Defines which mtypes are used, their density and associated etypes.

Example:
::

    version: v1.0
    composition:
      <region>:
        <mtype>:
          density: <number|3D-profile>
          etypes:
            <etype1>: e_1
            <etype2>: e_2

where

 * `<region>` is region name ('L1', 'L2'..., 'L6' in case of SSCX);
 * `<mtype>` is mtype name (for example, 'L1_SLAC');
 * `<etype>` one of corresponding etypes (for example, 'bAC').

`etype` proportions `e_k` corresponding to single `mtype` should sum to 1.0.

`density` could be:

 * a number (cell count per mm^3)
 * atlas-defined 3D profile (VoxelBrain atlas layer name in curly braces)
 * locally-defined 3D-profile (path to NRRD file with volumetric data)

.. tip::
    We'd recommend to use local file paths with 3D density profiles for development purpose only; and to use exclusively constants and atlas-defined profiles for "public" circuits.

To specify morphology rotation angles individually per each mtype, please add `rotation` section to YAML root.

For instance,

::

  version: 1.2
  composition:
    ...
  rotation:
    L2:
      L23_MC:
        - ['y', 'uniform', {'low': -3.1416, 'high': 3.1416}]
        - ['x', 'uniform', {'low': -0.7853, 'high': 0.7853}]

would rotate each `(L2, L23_MC)` cell:

  - first by a random uniform angle from :math:`-\pi` to :math:`\pi` around Y-axis
  - then by random uniform angle from :math:`-\pi/4` to :math:`\pi/4` around X-axis

.. note::

  The axis in question here, are _morphology_ axes, not global coordinate system axes.

At the moment two random distributions are supported:

  - `uniform(low, high)`
  - `normal(loc, scale)`

.. note::

  The names for distributions and their parameters are chosen according to `NumPy <https://docs.scipy.org/doc/numpy/reference/routines.random.html>`_ naming style.

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

Used in :ref:`ref-phase-assign-morphologies`, :ref:`ref-phase-assign-emodels`, :ref:`ref-phase-s2f` and :ref:`ref-phase-s2s` phases.


placement_rules.xml
~~~~~~~~~~~~~~~~~~~

An XML file defining how to use morphology annotations for scoring morphology placement.

Used in :ref:`ref-phase-assign-morphologies` phase.


builderRecipeAllPathways.xml + builderConnectivityRecipeAllPathways.xml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This pair used to fully defined the circuit composition; now it is still relevant for building the connectome, **but no longer for defining cell composition**.

.. warning::
    Although ``<column>`` and ``<NeuronTypes>`` sections of ``builderRecipeAllPathways.xml`` are not used anymore for defining cell composition, they still have to be specified for ``builderRecipeAllPathways.xml`` consumers to work properly. MType names should be consistent with that actually used in cell composition.

    We apologize for this inconvenience that is due to ongoing transition from column-based circuit building to atlas-based one.

Used in :ref:`ref-phase-touchdetector`, :ref:`ref-phase-s2f` and :ref:`ref-phase-s2s` phases.
