"""Constants."""
PACKAGE_NAME = "circuit_build"
SCHEMAS_DIR = "snakemake/schemas"

INDEX_SUCCESS_FILE = "meta_data.json"
SPACK_MODULEPATH = "/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta"
NIX_MODULEPATH = (
    "/nix/var/nix/profiles/per-user/modules/bb5-x86_64/modules-all/release/share/modulefiles/"
)
APPTAINER_MODULEPATH = SPACK_MODULEPATH
APPTAINER_MODULES = ["archive/2022-11", "singularityce/3.10.0"]
APPTAINER_EXECUTABLE = "singularity"
APPTAINER_OPTIONS = "--cleanenv --containall --bind $TMPDIR:/tmp,/gpfs/bbp.cscs.ch/project"
APPTAINER_IMAGEPATH = "/gpfs/bbp.cscs.ch/ssd/containers"

ENV_FILE = "environments.yaml"  # in bioname
ENV_TYPE_MODULE = "MODULE"
ENV_TYPE_APPTAINER = "APPTAINER"
ENV_TYPE_VENV = "VENV"

ENV_VARS_NEURON_DEFAULT = {
    "NEURON_MODULE_OPTIONS": "-nogui",
}
ENV_VARS_DASK_DEFAULT = {
    "DASK_TEMPORARY_DIRECTORY": "${{TMPDIR:-/tmp/$USER}}",  # Temporary directory for local storage
    "DASK_DISTRIBUTED__LOGGING__DISTRIBUTED": "info",
    "DASK_DISTRIBUTED__WORKER__USE_FILE_LOCKING": "False",
    "DASK_DISTRIBUTED__WORKER__MEMORY__TARGET": "False",  # don't spill to disk
    "DASK_DISTRIBUTED__WORKER__MEMORY__SPILL": "False",  # don't spill to disk
    "DASK_DISTRIBUTED__WORKER__MEMORY__PAUSE": "0.80",  # pause execution at 80% memory use
    "DASK_DISTRIBUTED__WORKER__MEMORY__TERMINATE": "0.95",  # restart the worker at 95% use
    "DASK_DISTRIBUTED__WORKER__MULTIPROCESSING_METHOD": "spawn",
    "DASK_DISTRIBUTED__WORKER__DAEMON": "True",
    "DASK_DISTRIBUTED__ADMIN__TICK__LIMIT": "3h",  # Time allowed before triggering a warning
    # Reduce dask profile memory usage/leak (see https://github.com/dask/distributed/issues/4091)
    "DASK_DISTRIBUTED__WORKER__PROFILE__INTERVAL": "10000ms",  # Time between profiling queries
    "DASK_DISTRIBUTED__WORKER__PROFILE__CYCLE": "1000000ms",  # Time between starting new profile
    "DASK_DISTRIBUTED__COMM__TIMEOUTS__TCP": "200000ms",  # Time for handshake
    "DASK_DISTRIBUTED__COMM__TIMEOUTS__CONNECT": "200000ms",  # Time for handshake
}

ENV_CONFIG = {
    "brainbuilder": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-11", "brainbuilder/0.19.0"],
    },
    "spatialindexer": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "spatial-index/2.1.0"],
    },
    "parquet-converters": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "parquet-converters/0.8.0"],
    },
    "placement-algorithm": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-11", "placement-algorithm/2.4.0"],
    },
    "spykfunc": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "spykfunc/0.18.1"],
    },
    "touchdetector": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-08", "touchdetector/6.0.2"],
    },
    "region-grower": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-10", "py-region-grower/1.2.8"],
        "env_vars": {
            **ENV_VARS_NEURON_DEFAULT,
            **ENV_VARS_DASK_DEFAULT,
        },
    },
    "bluepyemodel": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": [
            "archive/2021-09",
            "py-bluepyemodel/0.0.5",
            "py-bglibpy/4.4.36",
            "neurodamus-neocortex/1.4-3.3.2",
        ],
        "env_vars": {
            **ENV_VARS_NEURON_DEFAULT,
            **ENV_VARS_DASK_DEFAULT,
        },
    },
    "ngv": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "py-archngv/3.0.2"],
    },
    "synthesize-glia": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "py-archngv/3.0.2", "py-mpi4py/3.1.4"],
        "env_vars": {
            **ENV_VARS_DASK_DEFAULT,
            "DASK_DISTRIBUTED__ADMIN__TICK__LIMIT": "1h",
        },
    },
    "ngv-touchdetector": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-08", "py-archngv/3.0.2", "touchdetector/6.0.2"],
    },
    "ngv-pytouchreader": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "py-archngv/3.0.2"],
    },
    "ngv-prepare-tetrahedral": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "py-archngv/3.0.2"],
    },
    "ngv-build-tetrahedral": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "gmsh/4.10.3"],
    },
    "ngv-refine-tetrahedral": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-06", "gmsh/4.10.3"],
    },
}
