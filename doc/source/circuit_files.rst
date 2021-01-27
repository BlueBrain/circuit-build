.. _ref-circuit-files:

What constitutes a circuit release?
===================================

Expected data
-------------

A typical circuit release folder would look like:

::

    CircuitConfig
    CircuitConfig_base
    CircuitConfig_nrn
    circuit.h5 or circuit.mvd3
    sonata/
      networks/
        nodes/
          <nodes Sonata population name, by default 'All'>/
            nodes.h5
        edges/
          functional/
            <edges Sonata population name, by default 'All'>/
              edges.h5
    connectome/
      functional/
        edges.h5
        nrn.h5
        start.target
        SYNAPSE_index.dat
        SYNAPSE_index.idx
        SYNAPSE_payload.dat
        spykfunc
    start.target
    morphologies.tsv
    SEGMENT_index.dat
    SEGMENT_index.idx
    SEGMENT_payload.dat

.. note::
  All of these files are normally produced as a part of circuit build pipeline.

  We'd recommend to avoid modifying them manually unless REALLY required.

**CircuitConfig**

`BlueConfig`_ file defining "static" part of the circuit (path to cell / synapse collection,
morphology release etc). An example:

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

**CircuitConfig_base**

Variation of `CircuitConfig` for a circuit without connectome.

**CircuitConfig_nrn**

Variation of `CircuitConfig` for a functional circuit.

**circuit.h5** or **circuit.mvd3**

File with cell properties either in `SONATA`_ or `MVD3`_ format. Such file file does not contain
morpho-electrical cell properties.

**nodes.h5** from sonata/

File with cell properties in `SONATA`_ format including morpho-electrical data

**edges.h5** from sonata/

File with synapse properties in `SONATA`_ format

**edges.h5** from connectome/

It is a symlink to `edges.h5` from sonata/

**nrn.h5** from connectome/

File with synapse properties in `NRN`_ format

**start.target** from connectome/

A symlink to the same file the root folder

**[SEGMENT]_[index|payload]** from connectome/

Segment `spatial index`_

**spykfunc** from connectome/

Auxiliary folder for temporary system files

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


**morphologies.tsv**

Auxiliary file for building cells properties file

**[SYNAPSE]_[index|payload]**
  Synapse `spatial index`_


Experimental
------------

**subcellular.h5**

`PyTables <https://www.pytables.org/>`_ HDF5 file storing gene expressions and protein concentrations associated with each cell.
It has ``\library`` group with a collection of gene expressions / protein concentrations "types"; and ``\cells`` table assigning those to each cell GID.

``cells`` library has four columns:

- ``gid`` for cell GID
- ``gene_expressions`` with UUID of one of the tables from ``/library/gene_expressions``
- ``cell_proteins`` with UUID of one of the tables from ``/library/cell_proteins``
- ``synapse_proteins`` with UUID of one of the tables from ``/library/synapse_proteins``

Each row corresponds to a different GID.

For instance, one row from ``/cells`` table can look like:

+-----+------------------+--------------------------------------+-------------------------------------+
| gid | gene_expressions | cell_proteins                        | synapse_proteins                    |
+=====+==================+======================================+=====================================+
| 1   | a00062           | 24329084-c0a5-4d7b-975d-0c621a46fa95 |f0199090-ff1f-4fd9-a084-db3c41f54b92 |
+-----+------------------+--------------------------------------+-------------------------------------+

Please refer to :ref:`subcellular phase <ref-phase-subcellular>` for the description of ``/library`` content.


.. _BlueConfig: https://bbpteam.epfl.ch/documentation/Circuit%20Documentation-0.0.1/blueconfig.html
.. _SONATA: https://github.com/AllenInstitute/sonata/blob/master/docs/SONATA_DEVELOPER_GUIDE.md
.. _MVD3: https://bbpteam.epfl.ch/documentation/Circuit%20Documentation-0.0.1/mvd3.html
.. _NRN: https://bbpteam.epfl.ch/project/spaces/pages/viewpage.action?pageId=10919530
.. _spatial index: https://bbpteam.epfl.ch/project/spaces/display/BBPDIAS/BBP-DIAS+Spatial+Indexing+of+Microcircuits
