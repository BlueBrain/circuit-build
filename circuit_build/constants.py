"""Constants."""
PACKAGE_NAME = "circuit_build"
SCHEMAS_DIR = "snakemake/schemas"

INDEX_FILES = ["index.spi", "meta_data.json"]
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

ENV_CONFIG = {
    "brainbuilder": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2023-02", "brainbuilder/0.18.3"],
    },
    "spatialindexer": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-12", "spatial-index/1.1.0"],
    },
    "parquet-converters": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-07", "parquet-converters/0.8.0"],
    },
    "placement-algorithm": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-03", "placement-algorithm/2.3.0"],
    },
    "spykfunc": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-10", "spykfunc/0.17.4"],
    },
    "touchdetector": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-07", "touchdetector/5.7.0"],
    },
    "region-grower": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-03", "py-region-grower/0.3.0"],
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
    },
    "ngv": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-06", "py-archngv/2.0.2"],
    },
    "synthesize-glia": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-06", "py-archngv/2.0.2", "py-mpi4py"],
    },
    "ngv-touchdetector": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-06", "py-archngv/2.0.2", "touchdetector/5.6.1"],
    },
    "ngv-pytouchreader": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-06", "py-archngv/2.0.2"],
    },
}
