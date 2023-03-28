.. _ref-environments:

Environments
============

Most of the rules defined in ``Snakefile`` are executed in an environment where spack modules are loaded before running the commands.

The versions of the modules to be loaded are defined in ``circuit-build``, and may change between different ``circuit-build`` versions.

The current version of circuit build defines these environments:

.. exec_code::

    # hide: start
    from yaml import safe_dump
    from circuit_build.constants import ENV_CONFIG
    print(safe_dump(ENV_CONFIG, sort_keys=False))

In some exceptional cases, it may be desirable to override the modules:

- with a custom module or custom version of the module,
- with a custom Python virtual environment already existing,
- with a custom Apptainer/Singularity image already existing.

You can also specify the key ``env_vars`` to add or override environment variables to be set before running the job.

The environments can be overridden adding an ``environments.yaml`` file in the bioname directory, containing only the environments to be overridden.

The configuration file is validated using this :download:`schema <../../circuit_build/snakemake/schemas/environments.yaml>`.

.. warning::

    Please be aware that only the predefined modules have been tested, and any custom environment may break the rules, or give unexpected results.


Overriding with a custom module
-------------------------------

To use a custom module, you can add an ``environments.yaml`` file with the following content:

.. code-block:: yaml

    version: 1
    env_config:
      brainbuilder:
        env_type: MODULE
        modules:
        - archive/2022-03
        - brainbuilder/0.17.0

If needed, you can specify also the ``modulepath`` as in the following example:

.. code-block:: yaml

    version: 1
    env_config:
      brainbuilder:
        env_type: MODULE
        modulepath: /gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta
        modules:
        - archive/2022-03
        - brainbuilder/0.17.0


Overriding with a custom virtual environment
--------------------------------------------

To use an existing custom virtual environment, you can add an ``environments.yaml`` file with the following content:

.. code-block:: yaml

    version: 1
    env_config:
      brainbuilder:
        env_type: VENV
        path: /absolute/path/to/existing/venv/

The configuration key ``path`` should be set to the directory containing the existing python virtual environment.
Alternatively, it may be set to any existing file, that will be sourced before executing the commands in the rule.

If needed, it's possible to specify some optional keys as in the following example:

.. code-block:: yaml

    version: 1
    env_config:
      brainbuilder:
        env_type: VENV
        path: /absolute/path/to/existing/venv/
        modulepath: /path/to/spack/modules
        modules:
        - archive/2023-02
        - hpe-mpi/2.25.hmpt

.. warning::

    In most cases, you shouldn't load modules that modify PYTHONPATH to avoid issues with conflicting versions of the libraries.


Overriding with a custom Apptainer/Singularity image
----------------------------------------------------

To use a custom Apptainer/Singularity image, you can add an ``environments.yaml`` file with the following content:

.. code-block:: yaml

    version: 1
    env_config:
      brainbuilder:
        env_type: APPTAINER
        image: /path/to/apptainer/image.sif

If needed, it's possible to specify some optional keys as in the following example:

.. code-block:: yaml

    version: 1
    env_config:
      brainbuilder:
        env_type: APPTAINER
        image: /path/to/apptainer/image.sif
        executable: singularity
        options: "--cleanenv --containall --bind $TMPDIR:/tmp,/gpfs/bbp.cscs.ch/project"
        modulepath: /path/to/spack/modules
        modules:
        - archive/2022-06
        - singularityce
