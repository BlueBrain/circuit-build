"""Constants."""
PACKAGE_NAME = "circuit_build"
TEMPLATES_DIR = "snakemake/templates"
SCHEMAS_DIR = "snakemake/schemas"

SPACK_MODULEPATH = "/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta"
NIX_MODULEPATH = (
    "/nix/var/nix/profiles/per-user/modules/bb5-x86_64/modules-all/release/share/modulefiles/"
)
MODULES = {
    "brainbuilder": (SPACK_MODULEPATH, ["archive/2022-03", "brainbuilder/0.17.0"]),
    "flatindexer": (NIX_MODULEPATH, ["nix/hpc/flatindexer/1.8.12"]),
    "parquet-converters": (SPACK_MODULEPATH, ["archive/2022-03", "parquet-converters/0.7.0"]),
    "placement-algorithm": (SPACK_MODULEPATH, ["archive/2022-03", "placement-algorithm/2.3.0"]),
    "spykfunc": (SPACK_MODULEPATH, ["archive/2022-03", "spykfunc/0.17.1"]),
    "touchdetector": (SPACK_MODULEPATH, ["archive/2022-03", "touchdetector/5.6.1"]),
    "region-grower": (SPACK_MODULEPATH, ["archive/2022-03", "py-region-grower/0.3.0"]),
    "bluepyemodel": (
        SPACK_MODULEPATH,
        [
            "archive/2021-09",
            "py-bluepyemodel/0.0.5",
            "py-bglibpy/4.4.36",
            "neurodamus-neocortex/1.4-3.3.2",
        ],
    ),
}
INDEX_FILES = [
    "index.dat",
    "index.idx",
    "payload.dat",
]
