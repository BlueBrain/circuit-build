.. _ref-atlas:

Volumetric datasets
===================

Circuit building pipeline described here is atlas-based, i.e. it relies on an *atlas* of the brain region to model as one of its inputs.

Atlas is a collection of volumetric datasets stored either at `VoxelBrain <http://voxels.nexus.apps.bbp.epfl.ch/api/analytics/atlas/releases/>`_ atlas catalogue or locally in the file system.

In particular, the following *data_types* are expected to be found in the atlas:

- `brain_regions`, `scalar field <https://bbpteam.epfl.ch/project/spaces/display/NRINF/Scalar+Value+Image>`_ specifying region ID for each voxel
- `hemisphere`, `scalar field <https://bbpteam.epfl.ch/project/spaces/display/NRINF/Scalar+Value+Image>`_ specifying the hemisphere ID for each voxel (0: undefined, 1: right, 2: left)
- `orientation`, `orientation field <https://bbpteam.epfl.ch/project/spaces/display/NRINF/Orientation+Field>`_ defining cell orientation for each voxel in quaternion representation
- `[PH]<X>`, `layer profiles <https://bbpteam.epfl.ch/documentation/projects/placement-algorithm/latest/index.html#ref-data-atlas>`_

.. tip::

    ``tools/check_atlas.py`` script in ``circuit-build`` repo provides an automated way to check if a given VoxelBrain atlas is compatible with circuit building pipeline.

    Please note though, that it does not give 100% guarantee of atlas compatibility.
