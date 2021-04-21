Changelog
=========

Version 3.2.0 (2021-04-21)
--------------------------
- 'node_population_name' and 'edge_population_name' are mandatory properties
- improve logging [NSETM-1428]

Version 3.1.3 (2021-01-15)
--------------------------
- Use Sonata nodes for CellLibraryFile of generated CircuitConfig files
- add a new property 'node_population_name' to 'common' of MANIFEST.yaml to specify name of nodes
  population to produce
- Require bioname folder to be under git
- add a new property 'edge_population_name' to 'common' of MANIFEST.yaml to specify name of edges
  population to produce
- rename 'edges.sonata' to 'edges.h5' in all rules of Snakefile

Version 3.1.2 (2020-10-02)
--------------------------
- Update parquet-converters module to 0.5.7
- Add DAG images to the documentation

Version 3.1.1 (2020-09-02)
--------------------------
- Fix snakemake files packaging

Version 3.1.0 (2020-08-21)
--------------------------
- Update documentation about the change from MVD3 to Sonata
- Introduce a new option `-m` for custom modules

Version 3.0.1 (2020-08-19)
--------------------------
- Fix 'circuitconfig_nrn' when no 'emodel_release'

Version 3.0.0 (2020-07-28)
--------------------------

- Wrap project into a python package
- Add local tests
- Drop separate Jenkins plan for tests
- Add a possibility to build circuits without emodels

Version 2.0.6 (2020-07-09)
--------------------------

- Changed `.mvd3` to `sonata` for the circuit building. SONATA now is the default circuit.
- Added `functional_sonata` to tests
- Added .tox for documentation building
- Changed modules versions to: parquet-converters/0.5.5, spykfunc/0.15.6, synapsetool/0.5.9, touchdetector/5.4.0
- Fixed write_network_config for sonata rules

Version 2.0.1 (2019-08-23)
--------------------------

- Add mini-frequency assignment
- add 2019-07 spack module path so "touchdetector/5.1.0"
- s2f/s2s experimental filters
