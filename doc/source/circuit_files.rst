.. _ref-circuit-files:

What constitutes a circuit release?
===================================

Expected data
-------------

A typical circuit release folder would look like:

::

    sonata/
      circuit_config.json
      node_sets.json
      networks/
        nodes/
          <nodes Sonata population name, by default 'All'>/
            nodes.h5
        edges/
          functional/
            <edges Sonata population name, by default 'All'>/
              edges.h5
    start.target
    morphologies.tsv

    # the ones below are side-effects of building
    connectome/
      functional/
        spykfunc
    circuit.empty.h5
    circuit.h5
    circuit.morphologies.h5
    circuit.somata.h5

.. note::
  All of these files are normally produced as a part of circuit build pipeline.

  We'd recommend to avoid modifying them manually unless REALLY required.

**nodes.h5**

File with cell properties in `SONATA`_ format including morpho-electrical data

**edges.h5**

File with synapse properties in `SONATA`_ format

**circuit_config.json**

The `SONATA`_ file describing the location of the circuit files.
Roughly equivalent to the legacy CircuitConfig file.

**node_sets.json**
Generated `Node Sets`_ for the `SONATA`_ circuit.
Roughly equivalent to the start.targets file.


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

Auxiliary Data
~~~~~~~~~~~~~~

The following files exist, but they are intermediary results during build:

**circuit.empty.h5**
Empty nodes-like file with generated structure.
Contains the population name.

**circuit.somata.h5**
Nodes-like file with the above, and soma positions set; includes me-type.

**circuit.morphologies.h5**
Nodes-like file with the above, and the names of the places morphologies.

**circuit.h5**

File with cell properties in `SONATA`_ format.
Such file file does not contain morpho-electrical cell properties.

**morphologies.tsv**

Auxiliary file for building cells properties file

**spykfunc** in connectome/

Auxiliary folder for temporary system files


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


.. _BlueConfig: https://sonata-extension.readthedocs.io/en/latest/blueconfig.html
.. _SONATA: https://github.com/AllenInstitute/sonata/blob/master/docs/SONATA_DEVELOPER_GUIDE.md
.. _Node Sets: https://sonata-extension.readthedocs.io/en/latest/sonata_nodeset.html
