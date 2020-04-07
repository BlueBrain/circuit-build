.. _ref-neocortex:

Neocortex
=========

Neocortex circuit building pipeline has diverged from "master" branch in a number of aspects:

- synthesizing detailed morphologies "on-the-fly"
- using Spark Functionalizer instead of C++ one
- running TouchDetector / Functionalizer region-by-region
- running segment spatial index region-by-region

Temporarily not available:

- electrical models assignment
- synapse spatial index

Circuit data
------------

* detailed morphologies are now generated as a part of circuit build and can be found in ``morphologies`` folder
* connectome is stored in multiple SYN2 files (one per region): ``connectome/functional/{region}/circuit.syn2``
* segment index is also chunked: ``spatial_index/{region}/SEGMENT``.

Snakefile
---------

Please checkout *ncx* branch of ``circuit-build``:

.. code-block:: bash

    $ git clone ssh://bbpcode.epfl.ch/common/circuit-build
    $ git checkout ncx

Bioname
-------

1. ``extNeuronDB.dat`` is no longer used.
Instead, one should provide ``neurondb-axon.dat`` file with a list of morphologies to be used as "axon donors" for synthesized dendritic trees.

2. Synthesis requires two additional files in ``bioname`` folder:

* ``tmd_distributions.json``
* ``tmd_parameters.json``

3. ``choose_morphologies`` and ``assign_morphologies`` phases are removed from ``MANIFEST.yaml`` and ``cluster.yaml``.

:ref:`ref-phase-choose-axons` and :ref:`ref-phase-synthesize-morphologies` phases (see below) replace them.

4. ``builder[Connectivity]RecipeAllPathways.xml`` is provided for every region (see :ref:`ref-chunked-local-connectome`).


place_cells
-----------

``FAST_HEMISPHERE`` special value can be used in place of dataset name when defining :ref:`atlas-based properties <ref-phase-place-cells>`.

Unlike regular atlas-based property, no volumetric dataset would be queried; cell property values would be chosen based on Z-coordinate: ``(z < 5700) ? "left" : "right")``.

.. _ref-phase-choose-axons:

choose_axons
------------

Pick axons for each position using "placement hints" approach.

Parameters
~~~~~~~~~~

**alpha**
    Use `score ** alpha` as morphology choice probability.

**scales**
    | Scaling factors to try for each axon.
    | Optional; if not provided, axons would be checked "as is", with no scaling applied.

**seed**
    Pseudo-random generator seed.


.. _ref-phase-synthesize-morphologies:

synthesize_morphologies
-----------------------

Parameters
~~~~~~~~~~

Synthesize somas and dendritic trees; graft pre-chosen axons.

**max_drop_ratio**
    | Maximal ratio of positions that can be dropped for each mtype (due to failure to pick an axon).
    | Optional, if not provided, defaults to 0.0 (i.e., no position dropping allowed).

**max_files_per_dir**
    | Maximal number of files per folder in hierarchical morphologies folder.
    | Optional, if not provided, defaults to 256.

**seed**
    Pseudo-random generator seed.


.. _ref-chunked-local-connectome:

Chunked local connectome
------------------------

To specify regions for which TouchDetector (and Functionalizer) would be run, please list them in ``touchdetector`` section in ``MANIFEST.yaml`` like in the example below:

::

    touchdetector:
      targets:
        - 'SSp-ll@left'
        - 'SSp-ll@right'
        - ...

Each of these regions should have corresponding ``builder[Connectivity]RecipeAllPathways.xml`` in the ``bioname/functional`` folder:

::

    bioname/functional/<region>/builder[Connectivity]RecipeAllPathways.xml
    bioname/functional/<region>/builderRecipeAllPathways.xml

.. warning::

    | In case you opt to use symlinks for sharing common ``builderRecipeAllPathways.xml`` between regions, we recommend to avoid placing ``builderConnectivityRecipeAllPathways.xml`` near that one, to avoid surprises with symlinks being resolved.
    | We are working on revising the recipes used by ``TouchDetector`` and ``Functionalizer`` to make managing them less tedious and error-prone.

For each of the regions, the following files would be produced:

::

    connectome/[structural|functional]/<region>/CircuitConfig-[aff|eff]
    connectome/[structural|functional]/<region>/circuit-[aff|eff].syn2
    connectome/[structural|functional]/<region>/edges-[aff|eff].sonata
    sonata/networks/[structural|functional]/<region>.edges-[aff|eff].h5

Each SYN2 and SONATA file has two copies: one sorted by postsynaptic GID (``-aff``); and another sorted by presynaptic GID (``-eff``). ``CircuitConfig-[aff|eff]`` references corresponding ``edges-[aff|eff].sonata`` file as ``nrnPath``; MVD3 is shared between all the "sub-circuits".



Chunked segment index
---------------------

Analogous to local connectome, to specify regions for which FLATIndex would be run, please list them in ``spatial_index_segment`` section in ``MANIFEST.yaml``:

.. code-block:: yaml

    spatial_index_segment:
      targets:
        - 'SSp-ll@left'
        - 'SSp-ll@right'
        - ...

For each of the regions, the following files would be produced:

::

    indices/<region>/SEGMENT_index.dat
    indices/<region>/SEGMENT_index.idx
    indices/<region>/SEGMENT_payload.dat
