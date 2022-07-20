Changelog
=========

Version 4.1.0
--------------------------

New Features
~~~~~~~~~~~~
- A dynamic config is added to circuit-build [NSETM-1905]
    * The config is generated based on the node and edges passed
    * Absolute paths are used throughout the workflow
    * The auxiliary subfolder holds all intermediate files
    * Morphologies dir is defined per population
    * Connectome dir is defined per population
    * Neuronal raw touches are stored in a raw subdir
- NGV workflow is added to circuit-build [NSETM-1873]
- Add custom environments: MODULE, APPTAINER, VENV.

Improvements
~~~~~~~~~~~~
- Fix sonata config's neuronal morphology directory entries and add a validator for the morphology
  release directory [NSETM-1920]
- Add missing MorphologyType to CircuitConfig [NSETM-1946]
- Convert functional tests into independent gitlab jobs [NSETM-1938]
- Move tests/ to tests/unit and add tests/functional for ngv-standalone [NSETM-1896]
- Internal change, split ``utils.py`` into separate modules.
- Generalize snakemake rules to allow for multiple workflows [NSETM-1878].

Bug Fixes
~~~~~~~~~
- Fix ``check_git`` to consider valid a bioname directory initialized with ``git init``.

Removed
~~~~~~~
- Drop support for Python 3.8, the minimum supported version is Python 3.9.


Version 4.0.1 (2022-04-07)
--------------------------

Improvements
~~~~~~~~~~~~
- Use modules from archive/2022-03 that support Morphology format spec version 1.3 [NSETM-1776].

Used modules
~~~~~~~~~~~~
- archive/2022-03/brainbuilder/0.17.0
- archive/2022-03/parquet-converters/0.7.0
- archive/2022-03/placement-algorithm/2.3.0
- archive/2022-03/spykfunc/0.17.1
- archive/2022-03/touchdetector/5.6.1
- archive/2022-03/py-region-grower/0.3.0
- archive/2021-09/py-bluepyemodel/0.0.5
- nix/hpc/flatindexer/1.8.12


Version 4.0.0 (2022-02-10)
--------------------------

New features
~~~~~~~~~~~~
- Add configuration parameter ``synthesis`` to turn on synthesis [NSETM-1161].
  In particular, these new jobs have been added:

  - ``compute_ais_scales``: ais_scaler computation for synthesis (equivalent of old ModelManagement).
  - ``compute_currents``: current computation (holding and threshold) for synthesis.

- Add configuration parameter ``partition`` to specify the nodesets to be touchdetected and functionalized separately [NSETM-1504].
  It can be used to process separately left and right hemispheres.
- Allow to specify a custom random rotation for morphologies [NSETM-1589].
- Allow to assign  to cells the ``hemisphere`` property from a given volumetric dataset, replacing ``FAST-HEMISPHERE`` [BRBLD-89].
- Add CLI option ``--with-summary`` to save a summary of the workflow in ``logs/<timestamp>/summary.tsv`` [NSETM-1428].
- Add CLI option ``--with-report`` to save a report of the workflow in ``logs/<timestamp>/report.html`` [NSETM-1428].
- Add CLI option ``--directory`` used as base directory for summary and reports, and passed to Snakemake [NSETM-1428].
- Add configuration parameter ``seed`` in ``assign_morphologies`` [NSETM-1641].
  Ensure that it can be optionally defined for: place_cells, choose_morphologies, assign_morphologies, synthesize_morphologies, assign_emodels.
- Allow to specify custom environment variables in ``cluster.yaml`` with ``env_vars``.

Improvements
~~~~~~~~~~~~
- Use nodes.h5 instead of circuit.mvd3 in circuitconfig_structural.
- Add schemas MANIFEST.yaml and cluster.yaml to validate the configuration files and keep the documentation in sync [NSETM-1503, NSETM-1619].
- Split all the job logs in separate files [NSETM-1428].
- Log more git information and the md5 checksum of bioname files [NSETM-1428].
- Use a jinja template to write Sonata config instead of brainbuilder CLI.
- Use jinja to write templates directly without salloc.
- Replace nose with pytest in unit tests, save output to tmptestdir.
- Support nodesets with touchdetector. [NSETM-1384]

Bug Fixes
~~~~~~~~~
- Load templates and schemas from the correct location even in case of custom Snakefile.

Removed
~~~~~~~
- Move to SONATA only:

  - nodes and edges only output in SONATA format, under the `sonata` directory
  - the ``functional`` & ``structural`` rules create a CircuitConfig and start.target files, but with SONATA contents

- The following rules were removed:

  - `functional_nrn`
  - `functional_sonata`
  - `structural_sonata`
  - `circuitconfig_nrn`
  - `sonata_to_nrn`
  - `symlink_sonata_edges`

- Remove Projection section from CircuitConfig because the syntax is not up to date.

Used modules
~~~~~~~~~~~~
- archive/2022-01/brainbuilder/0.17.0
- archive/2021-10/parquet-converters/0.7.0
- archive/2021-12/placement-algorithm/2.3.0
- archive/2021-10/spykfunc/0.17.1
- archive/2021-10/touchdetector/5.6.1
- archive/2021-09/py-region-grower/0.3.0
- archive/2021-09/py-bluepyemodel/0.0.5
- nix/hpc/flatindexer/1.8.12


Version 3.1.4 (2021-05-05)
--------------------------
- ``node_population_name`` and ``edge_population_name`` are mandatory properties in ``MANIFEST.yaml``.

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
