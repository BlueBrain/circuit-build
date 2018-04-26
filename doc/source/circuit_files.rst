.. _ref-circuit-files:

What constitues a circuit release?
==================================

A typical circuit release folder would look like:

::

    CircuitConfig
    circuit.mvd3
    connectome/
      functional/
        nrn.h5
        nrn_efferent.h5
        nrn_positions.h5
        nrn_positions_efferent.h5
        nrn_summary.h5
        start.target
        SYNAPSE_index.dat
        SYNAPSE_index.idx
        SYNAPSE_payload.dat
    start.target
    SEGMENT_index.dat
    SEGMENT_index.idx
    SEGMENT_payload.dat

.. note::
  All of these files are normally produced as a part of circuit build pipeline.

  We'd recommend to avoid modifying them manually unless REALLY required.

**CircuitConfig**
  `BlueConfig <https://bbpteam.epfl.ch/documentation/Circuit%20Documentation-0.0.1/blueconfig.html>`_ file defining "static" part of the circuit (path to cell / synapse collection, morphology release etc), e.g.:

  ::

    Run Default
    {
      CircuitPath /gpfs/bbp.cscs.ch/project/proj64/circuits/test3
      nrnPath /gpfs/bbp.cscs.ch/project/proj64/circuits/test3/connectome/functional
      MorphologyPath /gpfs/bbp.cscs.ch/project/proj59/entities/morphologies/2017.10.31
      METypePath /gpfs/bbp.cscs.ch/project/proj64/entities/emodels/2017.11.03/hoc
      MEComboInfoFile /gpfs/bbp.cscs.ch/project/proj64/entities/emodels/2017.11.03/mecombo_emodel.tsv
      CellLibraryFile circuit.mvd3
      BioName /gpfs/bbp.cscs.ch/project/proj64/circuits/test3/bioname/
      Atlas http://voxels.nexus.apps.bbp.epfl.ch/api/analytics/atlas/releases/77831ACA-6198-4AA0-82EF-D0475A4E0647
    }


**circuit.mvd3**
  `MVD3 <https://bbpteam.epfl.ch/documentation/Circuit%20Documentation-0.0.1/mvd3.html>`_ file with cell properties.

**nrn*.h5**
  `NRN <https://bbpteam.epfl.ch/project/spaces/pages/viewpage.action?pageId=10919530>`_ files with synapse properties.

**start.target**
  Text file defining cell *targets* (i.e. named collections of cell GIDs), e.g.:

  ::

    Target Cell All
    {
      SLM_PPA SO_BP
    }

    Target Cell SLM_PPA
    {
      a1 a2 a42
    }


**[SEGMENT|SYNAPSE]_[index|payload]**
  Segment / synapse `spatial index <https://bbpteam.epfl.ch/project/spaces/display/BBPDIAS/BBP-DIAS+Spatial+Indexing+of+Microcircuits>`_


Experimental
------------

**transcriptome.h5**

HDF5 defining *gene expression* for each cell.

The file layout is:

::

  \cells
  -- expressions [N x 1, int32]
  \library
  -- genes [M x 1, string]
  -- expressions [K x M, float32]

where

  * ``N`` is the number of cells in the circuit (GIDs are assumed to be numbers from ``1`` to ``N``)
  * ``M`` is the number of genes in each gene expression
  * ``K`` is the number of available gene expression vectors (multiple cells are sharing same gene expression vector at the moment)

``/library/expressions`` is the matrix of all unique gene expressions; and ``library/genes`` are gene names corresponding to ``/library/expressions`` columns.

``/cells/expressions`` contains row indices ``/library/expressions`` corresponding to each GID (``\cells/expressions[0]`` corresponds to GID=1, ``\cells/expressions[1]`` to GID=2, etc.)