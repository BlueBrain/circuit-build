.. _ref-ngv:

Neuronal-Glio-Vascular circuits
===============================

.. _ref-ngv-definition:

What is an NGV circuit?
-----------------------

The NGV acronym is used for circuits comprised of neurons, glia, and cerebral vasculature.
These are circuits that extend the regular neuronal circuits with additional entities.
The three populations form pairwise connections resulting in the following networks:

* synaptic (neurons - neurons)
* neuroglial (neurons - glia)
* glial (glia - glia)
* gliovascular (glia - vasculature)

.. _ref-ngv-trigger:

How to trigger an NGV build?
----------------------------

In order to build an NGV circuit, the respective ``ngv`` rule needs to be used in the `circuit-build` cli as follows:

 .. code-block:: bash

    circuit-build run --bioname path/to/bioname --cluster-config path/to/cluster/config --directory build ngv

Executing the ``ngv`` rule alone is not sufficient to launch an NGV build and it will result in a missing rule exception.
In conjunction with the rule, the optional ``ngv`` section needs to be present in the bioname's ``MANIFEST.yaml``.
Without the latter the ngv-related rules are disabled.

Overview of the ngv ``MANIFEST.yaml`` layout:

.. code-block:: yaml

    common:
      # ... neuronal build common ...

    # ... neuronal build parameters ...

    ngv:
      common:
        # ... ngv build common ...

      # ... ngv build parameters ...

Finally, the bioname, datasets, and parameters required for an NGV build will be described in the following sections.

.. _ref-ngv-standalone-vs-full:

Standalone vs. Full build
-------------------------

Two options are available in building an NGV circuit:
* link an existing neuronal circuit
* build a neuronal-glio-vascular circuit from scratch.

This is determined by the inclusion or not of the subsection `base_circuit` in the ``MANIFEST.yaml`` respectively as shown below:

.. code-block:: yaml

    ngv:
      common:
        base_circuit:
            config: path/to/neuronal/sonata/config
            node_population_name: neuronal-node-population-name
            edge_population_name: neuronal-edge-population-name

Upon inclusion of the `base_circuit` entry, the neuronal circuit populations and config need to be specified so that the linking is successful.
The snakemake workflow will change its targets to the provided paths, avoiding running the rules that generates them.
Paths can be either absolute or relative to the bioname's directory.

.. warning::

    If the atlas used for the NGV build (specified under ngv[common][atlas]) is not the same as the one used for the neuronal build, it needs to be ensured that they are co-localized in order to prevent errors that will arise from misaligned volumes.

.. note::

   Node and Edge population names are mandatory in order to uniquely specify the populations that will be used.


Although most of the circuit components are mandatory when extracting the paths, spatial indices are not. If no synapse spatial index is present in the config, the respective rule will be executed to compute it.


Bioname
-------

The files required for the NGV bioname are listed in the table below.
Depending if the build is standalone (neuronal circuit already exists and it's linked) or full a different set of files is required.

.. list-table:: NGV Bioname Files
    :header-rows: 1

    * - Filename
      - Standalone
      - Full
    * - MANIFEST.yaml
      - X
      - X
    * - astrocyte_gap_junction_recipe.xml
      - X
      - X
    * - tns_parameters.json
      - X
      - X
    * - tns_distributions.json
      - X
      - X
    * - tns_context.json
      - X
      - X
    * - builderConnectivityRecipeAllPathways.xml
      -
      - X
    * - builderRecipeAllPathways.xml
      -
      - X
    * - cell_composition.yaml
      -
      - X
    * - mini_frequencies.tsv
      -
      - X
    * - mtype_taxonomy.tsv
      -
      - X
    * - neurondb-axon.dat
      -
      - X
    * - placement_rules.xml
      -
      - X
    * - protocol_config.yaml
      -
      - X
    * - targets.yaml
      -
      - X
    * - tmd_distributions.json
      -
      - X
    * - tmd_parameters.json
      -
      - X



.. _ref-ngv-manifest-yaml:

MANIFEST.yaml
~~~~~~~~~~~~~

The main configuration for the ``MANIFEST.yaml`` is identical to the regular configuration for the neuronal circuit building (see :ref:`ref-manifest-yaml`).

The NGV configuration resides entirely under the section `ngv` and it includes its own common and ngv rules configurations.

The main configuration for the `ngv` building is comprised of:

* atlas space
* vasculature geometry
* individual task parameters

.. literalinclude:: ../../tests/functional/ngv-standalone/bioname/MANIFEST.yaml
    :language: yaml

The vasculature needs to be provided in two different forms as listed above.
The skeleton is a graph, similar to that of the cell morphologies (see `specification <https://morphology-documentation.readthedocs.io/en/latest/h5-vasc-graph.html>`_), whereas the surface mesh is a triangular surface mesh stored in the wavefront `.obj` file format.

.. warning::

    Please ensure that the skeleton and surface mesh correspond to the same vascular geometry.  Otherwise, running an ngv build with mismatching skeleton and surface geometries may result in erroneous behavior and possibly crashes.

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/common

astrocyte_gap_junction_recipe.xml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

XML file defining the glial gap junction connectivity.
Used in glialglial connectivity phase by `Touchdetector`_.

Further documentation of the recipe is available in `Circuit Documentation <https://sonata-extension.readthedocs.io/en/latest/recipe.html>`_

tns_parameters.json + tns_distributions.json + tns_context.json
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configuration files for the topological synthesis of astrocytic morphologies.


NGV Phases
----------

.. _ref-phase-ngv-config:

**ngv_config**
~~~~~~~~~~~~~~

Generate a SONATA config for the NGV circuit.

.. _ref-phase-build-sonata-vasculature:

**build_sonata_vasculature**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert the hdf5 vascular skeleton into a SONATA node population, which is required for generating edge populations between the vasculature and other node populations, like astrocytes.

For more details on the SONATA representation of the vascular geometry, see the `vascular SONATA specification  <https://sonata-extension.readthedocs.io/en/latest/sonata_tech.html#fields-for-vasculature-population-model-type-vasculature>`_.

.. _ref-phase-place-glia:

**place_glia**
~~~~~~~~~~~~~~

Create a glia node population with positions and properties.


.. note::
    Orientations are not stored for astrocytes because they are grown embedded in space, not placed and then rotated.

Properties assigned (in addition to position):

* radius
* morphology
* mtype

.. note::
    Astrocytic placement is performed avoiding somata intersections with other astrocytic somata or the vascular geometry.

Parameters

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/cell_placement

.. _ref-phase-assign-glia-emodels:

**assign_glia_emodels**
~~~~~~~~~~~~~~~~~~~~~~~

Add ``model_template`` property to the glial population.

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/assign_emodels

.. _ref-phase-finalize-glia:

**finalize_glia**
~~~~~~~~~~~~~~~~~

Combine the intermediate files from :ref:`ref-phase-place-glia` and :ref:`ref-phase-assign-glia-emodels` into a finalized SONATA node population file.

.. _ref-phase-microdomains:

**build_glia_microdomains**
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate the anatomically exclusive territories (microdomains) of protoplasmic astrocytes.

They are modeled as a partition of the 3D space into convex tiling polygons.
Their geometry is generated using the Laguerre distance, which combines the astrocytic soma positions and radii.
This geometrical abstraction generates bounding volumes, establishing the reachable region for each astrocyte.

Regular tiling is converted to overlapping by uniformly scaling the domains until a 5% overlap is achieved.

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/microdomains

.. _ref-phase-gliovascular-connectivity:

**build_gliovascular_connectivity**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The gliovascular connectivity is established in three steps:

* Distribute potential targets on the vasculature skeleton graph with a frequency determined by the ``linear_density`` parameter in units of points per micron.

* For each astrocyte find the contained potential targets within its domain and select a subset of the targets based on the ``reachout_strategy`` and ``endfeet_distribution`` (number of endfeet per astrocyte).

* Find where the rays from the astrocyte soma centers to the skeleton medial points intersect the surface of the vasculature. These will become the final endfeet starting points on the surface of the vasculature.

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/gliovascular_connectivity

By default the ``maximum_reachout`` strategy is used, which minimizes the distance of the target to the astrocyte, maximizes it to nearby endfeet targets, and prioritizes the targeting of different branches if present.

.. note::
    For the calculation of the intersections with the vascular surface, the skeleton graph is used with each segment represented as a truncated cone. The triangular surface mesh is not used at this step to avoid erroneous behavior in the case that the mesh does not faithfully represent the surface of the vasculature.

.. _ref-phase-neuroglial-connectivity:

**build_neuroglial_connectivity**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Associate neuronal synapses with each astrocyte. Here the synapses that each astrocyte can encapsulate is determined.

.. note::

    In this step astrocytic morphologies have not been created yet. The association is performed using the geometrical abstraction of each cell's bounding volume (microdomain).

.. _ref-phase-endfeet-meshes:

**build_endfeet_surface_meshes**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Grow the meshes of the endfeet on the surface of the vasculature. The fast marching method (fmm) algorithm is used for this phase.

Using the endfeet target points generated in :ref:`ref-phase-gliovascular-connectivity`, the endfeet area is grown isotropically across the vessel surface until it collides with another endfoot area or reaches a maximum radius (``fmm_cutoff_radius``).

The growth is considered competitive because all the endfeet are growing simultaneously restricting the area they are grown into from neighboring endfeet.

After the simulation has converged, the overshoot surfaces are pruned so that they match the experimental distribution of endfeet areas, defined by the ``area_distribution`` parameter.

The last step consists of assigning a thickness to the 2D endfeet surfaces grown on the surface of the vasculature, drawn by the ``thickness_distribution`` parameter.

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/endfeet_surface_meshes

A separate HDF5 file is generated for storing the geometry of the endfeet meshes.
See the `endfeet meshes specification <https://sonata-extension.readthedocs.io/en/latest/endfeet_meshes.html>`_ for more details on the outputted data.

**synthesize_glia**
~~~~~~~~~~~~~~~~~~~

Grow astrocytic morphologies embedded in space, using the connectivities from the previous steps.

.. jsonschema:: ../../circuit_build/snakemake/schemas/MANIFEST.yaml#/properties/ngv/properties/synthesis

**finalize_gliovascular_connectivity**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add morphology specific properties to the gliovascular edge population.
The grown morphology of the astrocyte is required for this phase.

* astrocyte_section_id
* endfoot_compartment_length
* endfoot_compartment_diameter
* endfoot_compartment_perimeter

See the `enfoot edge population type <https://sonata-extension.readthedocs.io/en/latest/sonata_tech.html#fields-for-endfoot-connection-type-edges>`_ for a full
description of all the properties.


**finalize_neuroglial_connectivity**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add morphology specific properties to the neuroglial edge population.
The grown morphology of the astrocyte is required for this phase.

* astrocyte_section_id
* astrocyte_segment_id
* astrocyte_segment_offset
* astrocyte_section_pos
* astrocyte_center_x
* astrocyte_center_y
* astrocyte_center_z

See the `enfoot synapse_astrocyte population type <https://sonata-extension.readthedocs.io/en/latest/sonata_tech.html#fields-for-synapse-astrocyte-connection-type-edges>`_ for a full description of all the properties.

.. _ref-phase-glial-gap-junctions:

**glial_gap_junctions**
~~~~~~~~~~~~~~~~~~~~~~~

Estimate touches between neighboring astrocytes using the ``touchdetector`` and the ``glial_gap_junction_recipe.xml`` configuration.

**glialglial_connectivity**
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert touchdetector's touches from :ref:`ref-phase-glial-gap-junctions` to a SONATA edge population.

**ngv**
~~~~~~~

Create an NGV circuit, executing all the phases above plus the ref:`ref-phase-functional` neuronal phase if the `base_circuit` entry is not defined in the `MANIFEST.yaml` (See
:ref:`ref-ngv-standalone-vs-full`).


.. _TouchDetector: https://bbpteam.epfl.ch/documentation/projects/TouchDetector/latest/
