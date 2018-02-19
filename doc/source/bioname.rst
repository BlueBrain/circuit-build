.. _ref-bioname:

Bioname: circuit build recipes
==============================

The following parts should define a *reproducible* circuit release:
 * `bioname`, a folder with recipe files specifying me-type composition, mtype density profiles, connectome parameters etc.
 * external `entities`, like morphology release or electrical model release
 * workflow definition, at the moment based on `Snakemake <http://snakemake.readthedocs.io/en/stable/index.html>`_

Eventually `bioname` and `entities` would become `Nexus`-stored entities in a strict sense (i.e. validated against some schema, immutable, accessible by URL). At the moment though these are files stored at specified paths at GPFS.

Let us describe the contents of `bioname` in more detail now.


Bioname
-------

We address a folder for storing circuit build recipes as circuit `bioname`.

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

Example:
::
    common:
        atlas: http://voxels.nexus.apps.bbp.epfl.ch/api/analytics/atlas/releases/77831ACA-6198-4AA0-82EF-D0475A4E0647
        region_ids: [120]
        morph_release: /gpfs/bbp.cscs.ch/project/proj59/entities/morphologies/2017.10.31
        emodel_release: /gpfs/bbp.cscs.ch/project/proj64/entities/emodels/2017.11.03
        sw_release: 2017-11-pre-upgrade

    place_cells:
        density_factor: 1.0
        soma_placement: 'basic'
        assign_column: true
        assign_layer: true
        seed: 0
    ...

We'll provide a short description for each of the *common* values here.
Please refer to :ref:`ref-phases` for each phase config description.

**atlas**
    Atlas URL in VoxelBrain or local folder path.

**region_ids**
    Region IDs to populate (to use only subset of the atlas).

    Optional; if omitted all atlas space would be used.

**morph_release**
    Path to morphology release folder.
    It should contain:
      * ``v1`` folder with morphologies in H5v1 format
      * ``ascii`` folder with morphologies in ASC format
      * ``annotations`` folder with morphology annotations used for placement

**emodel_release**
    Path to emodel release folder.
    It should contain as subfolders:
      * ``hoc`` folder with model HOC templates
      * ``mecombo_emodel.tsv`` file with *me_combo* parameters

**sw_release**
    `BBP archive S/W modules <https://bbpteam.epfl.ch/project/spaces/display/BBPHPC/BBP+ARCHIVE+SOFTWARE+MODULES>`_ to use.

.. tip::
    If `sw_release` is set to `null`, modules available in the current environment would be used. This feature is meant for development purposes; we strongly recommend to use some specific release for the "public" circuits.


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
 * 3D-profile (path to NRRD file with volumetric data aligned with brain region atlas)

.. tip::
    We are going to add support for referencing VoxelBrain-stored 3D density profiles in the recipe.
    We'd recommend to use local file paths with 3D density profiles for development purpose only; and to use exclusively constants and atlas-stored profiles for "public" circuits.

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

Should be compatible with morphology and emodel releases used; most often is a subset of a similar file produced as a part of emodel release.

Example:
::
  C230998A-I3           2 L23_BP bAC bAC_L23BTC_L23_BP_2_C230998A-I3
  C230998A-I3_-_Clone_0 2 L23_BP bAC bAC_L23BTC_L23_BP_2_C230998A-I3_-_Clone_0

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
