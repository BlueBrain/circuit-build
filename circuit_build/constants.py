"""Constants."""
PACKAGE_NAME = "circuit_build"
TEMPLATES_DIR = "snakemake/templates"
SCHEMAS_DIR = "snakemake/schemas"

INDEX_FILES = ["index.dat", "index.idx", "payload.dat"]
SPACK_MODULEPATH = "/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta"
NIX_MODULEPATH = (
    "/nix/var/nix/profiles/per-user/modules/bb5-x86_64/modules-all/release/share/modulefiles/"
)
APPTAINER_MODULEPATH = SPACK_MODULEPATH
APPTAINER_MODULES = ["unstable", "singularityce"]
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
        "modules": ["archive/2022-03", "brainbuilder/0.17.0"],
    },
    "flatindexer": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": NIX_MODULEPATH,
        "modules": ["nix/hpc/flatindexer/1.8.12"],
    },
    "parquet-converters": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-03", "parquet-converters/0.7.0"],
    },
    "placement-algorithm": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-03", "placement-algorithm/2.3.0"],
    },
    "spykfunc": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-03", "spykfunc/0.17.1"],
    },
    "touchdetector": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-03", "touchdetector/5.6.1"],
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
        "modules": ["archive/2022-05", "py-archngv/2.0.1"],
    },
    "synthesize-glia": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-05", "py-archngv/2.0.1", "py-mpi4py"],
    },
    "ngv-touchdetector": {
        "env_type": ENV_TYPE_MODULE,
        "modulepath": SPACK_MODULEPATH,
        "modules": ["archive/2022-05", "py-archngv/2.0.1", "touchdetector/5.6.1"],
    },
}
