circuit-build
=============
Tool for building circuits.

It has only been developed and tested on the BB5 cluster, and depends on the tools that are available via modules.
It is possible to install the tools manually, and use the `Environments` to use virtual environments instead.


Installation
============

.. code-block:: bash

    git clone https://github.com/BlueBrain/circuit-build
    cd circuit-build
    pip install -e .

Documentation
=============

It is highly recommended to build the documentation with:

.. code-block:: bash

    cd circuit-build
    tox -edocs

As it contains a comprehensive tutorial and information about the different phases and their configurations.

Acknowledgements
================

The development of this software was supported by funding to the Blue Brain Project, a research
center of the École polytechnique fédérale de Lausanne (EPFL), from the Swiss government’s ETH Board
of the Swiss Federal Institutes of Technology.

For license see LICENSE.txt.

Copyright (c) 2018-2024 Blue Brain Project/EPFL
