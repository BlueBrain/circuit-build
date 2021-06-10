import logging
import os.path
import subprocess
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict

import jsonschema
import yaml

import snakemake

logger = logging.getLogger(__name__)


class Config:
    def __init__(self, config):
        self._config = config

    def get(self, keys, *, default=None):
        """Return the value from the configuration for the given key.

        Args:
            keys (list, tuple, str): keys in hierarchical order (e.g. ['common', 'atlas']).
            default: value to return if the key is not found or None.
        """
        conf = self._config
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            if conf is None:
                break
            conf = conf.get(k)
        if conf is None:
            logger.info("Get %s -> %s [default]", keys, default)
            return default
        logger.info("Get %s -> %s", keys, conf)
        return conf


class Context:
    def __init__(self, *, workflow: snakemake.Workflow, config: Dict, cluster_config: Dict):
        self.workflow = workflow
        self.conf = Config(config=config)
        self.cluster_config = cluster_config
        self.BIONAME = str(Path(self.conf.get("bioname", default="bioname")).expanduser().resolve())

        # Load MANIFEST.yaml into workflow config
        self.workflow.configfile(self.bioname_path("MANIFEST.yaml"))
        # Validate the merged configuration
        self.validate_config(config)

        self.CIRCUIT_DIR = "."
        self.BUILDER_RECIPE = self.bioname_path("builderRecipeAllPathways.xml")
        self.MORPHDB = self.bioname_path("extNeuronDB.dat")

        self.ATLAS = self.conf.get(["common", "atlas"])
        self.ATLAS_CACHE_DIR = ".atlas"

        self.NODE_POPULATION_NAME = self.validate_node_population_name(
            self.conf.get(["common", "node_population_name"])
        )
        self.EDGE_POPULATION_NAME = self.validate_edge_population_name(
            self.conf.get(["common", "edge_population_name"])
        )
        self.MORPH_RELEASE = self.conf.get(["common", "morph_release"])
        self.EMODEL_RELEASE = self.conf.get(["common", "emodel_release"])
        self.EMODEL_RELEASE_MECOMBO = None
        self.EMODEL_RELEASE_HOC = None
        if self.EMODEL_RELEASE:
            self.EMODEL_RELEASE_MECOMBO = os.path.join(self.EMODEL_RELEASE, "mecombo_emodel.tsv")
            self.EMODEL_RELEASE_HOC = os.path.join(self.EMODEL_RELEASE, "hoc")
            if not os.path.exists(self.EMODEL_RELEASE_MECOMBO) or not os.path.exists(
                self.EMODEL_RELEASE_HOC
            ):
                raise ValueError(
                    f"{self.EMODEL_RELEASE} must contain 'mecombo_emodel.tsv' file and 'hoc' folder"
                )

        self.LOGS_DIR = "logs"

        self.NODESETS_FILE = "node_sets.json"

        self.TOUCHES_DIR = "connectome/touches"
        self.CONNECTOME_FUNCTIONAL_DIR = "connectome/functional"
        self.CONNECTOME_STRUCTURAL_DIR = "connectome/structural"

        self.SPACK_MODULEPATH = "/gpfs/bbp.cscs.ch/ssd/apps/hpc/jenkins/modules/all"
        self.NIX_MODULEPATH = "/nix/var/nix/profiles/per-user/modules/bb5-x86_64/modules-all/release/share/modulefiles/"

        self.MODULES = self.build_modules(
            {
                "brainbuilder": (
                    self.SPACK_MODULEPATH,
                    ["archive/2020-08", "brainbuilder/0.14.0"],
                ),
                "flatindexer": (
                    self.NIX_MODULEPATH,
                    ["nix/hpc/flatindexer/1.8.12"],
                ),
                "jinja2": (
                    self.SPACK_MODULEPATH,
                    ["archive/2020-02", "python-dev/0.3"],
                ),
                "parquet-converters": (
                    self.SPACK_MODULEPATH,
                    ["archive/2020-09", "parquet-converters/0.5.7"],
                ),
                "placement-algorithm": (
                    self.SPACK_MODULEPATH,
                    ["archive/2020-08", "placement-algorithm/2.1.0"],
                ),
                "spykfunc": (
                    self.SPACK_MODULEPATH,
                    ["archive/2020-06", "spykfunc/0.15.6"],
                ),
                "synapsetool": (
                    self.SPACK_MODULEPATH,
                    ["archive/2020-05", "synapsetool/0.5.9"],
                ),
                "touchdetector": (
                    self.SPACK_MODULEPATH,
                    ["archive/2021-04", "touchdetector/5.6.0", "hpe-mpi"],
                ),
            }
        )

    def bioname_path(self, filename):
        return str(Path(self.BIONAME, filename))

    @staticmethod
    def format_if(template, value, func=None):
        """Return the template formatted, or empty string if value is None."""
        func = func or (lambda x: x)
        return template.format(func(value)) if value is not None else ""

    @staticmethod
    def escape_single_quotes(value):
        return value.replace("'", "'\\''")

    def log_path(self, name, _now=datetime.now()):
        timestamp = self.conf.get("timestamp", default=_now.strftime("%Y%m%dT%H%M%S"))
        path = os.path.abspath(os.path.join(self.LOGS_DIR, timestamp, f"{name}.log"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    @staticmethod
    def redirect_to_file(cmd, filename="{log}"):
        if os.getenv("LOG_ALL_TO_STDERR") == "true":
            # redirect logs to stderr instead of files
            return f"( {cmd} ) 1>&2"
        else:
            # else redirect to file
            return f"( {cmd} ) >{filename} 2>&1"

    def template_path(self, name):
        return os.path.join(self.workflow.basedir, "templates", name)

    def check_git_info(self, path):
        """Check that bioname is under git control and log git info."""
        cmd = """
            set -e
            echo "### Bioname info\n"
            echo "path: $(realpath .)"
            echo "date: $(date +'%Y-%m-%dT%H:%M:%S%z')"
            echo "user: $(whoami)"
            echo "host: $(hostname)"
            echo "circuit-build version: $(circuit-build --version)"
            echo "snakemake version: $(snakemake --version)"
            echo "git tag: $(git describe --always)"
            set -x
            git --no-pager diff
            git --no-pager diff --staged
            """
        cmd = self.redirect_to_file(cmd, filename=self.log_path("git_info"))
        cwd = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            subprocess.run(cmd, shell=True, check=True, cwd=cwd)
        except subprocess.CalledProcessError:
            raise RuntimeError(f"bioname folder: {path} must be under git (version control system)")

    def validate_config(self, config):
        with Path(self.workflow.basedir, "schemas/MANIFEST.yaml").open() as schema_fd:
            jsonschema.validate(instance=config, schema=yaml.safe_load(schema_fd))

    @staticmethod
    def validate_node_population_name(name):
        doc_url = "https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/bioname.html#manifest-yaml"
        allowed_parts = {"ncx", "neocortex", "hippocampus", "thalamus", "mousify"}
        allowed_types = {"neurons", "astrocytes", "projections"}
        msg = (
            '"node_population_name" in MANIFEST.yaml must exist and should fit the pattern: "<part>_<type>",'
            f"see {doc_url} for details"
        )

        if name is None:
            raise ValueError(msg)
        name_parts = name.split("_")
        if len(name_parts) != 2:
            warnings.warn(msg)
        elif name_parts[0] not in allowed_parts or name_parts[1] not in allowed_types:
            warnings.warn(msg)

        return name

    @staticmethod
    def validate_edge_population_name(name):
        doc_url = "https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/bioname.html#manifest-yaml"
        allowed_connection = {"electrical", "chemical_synapse", "synapse_astrocyte", "endfoot"}
        msg = (
            '"edge_population_name" in MANIFEST.yaml must exist and should fit the pattern: '
            f'"<source_population>__<target_population>__<connection>", see {doc_url} for details'
        )

        if name is None:
            raise ValueError(msg)
        name_parts = name.split("__")
        if (len(name_parts) not in [2, 3]) or (name_parts[-1] not in allowed_connection):
            warnings.warn(msg)

        return name

    def build_modules(self, modules):
        custom_modules = self.conf.get("modules")
        if custom_modules:
            # Custom modules can be configured using one of:
            # - configuration file MANIFEST.yaml -> list of strings from yaml
            # - command line parameter --config -> list of strings from json for backward compatibility
            for module in custom_modules:
                parts = module.split(":")
                assert 2 <= len(parts) <= 3, "Invalid custom spack module description " + module
                module_name = parts[0]
                assert module_name in modules, (
                    "Unknown spack module: "
                    + module_name
                    + ", known modules are: "
                    + ",".join(modules.keys())
                )
                module_list = parts[1].split(",")
                if len(parts) == 3:
                    module_path = parts[2]
                    modules[module_name] = (module_path, module_list)
                else:
                    modules[module_name] = (self.SPACK_MODULEPATH, module_list)
        return modules

    def bbp_env(self, module_env, command, slurm_env=None, skip_srun=False):
        result = " ".join(map(str, command))

        if slurm_env and self.cluster_config:
            if slurm_env not in self.cluster_config:
                slurm_env = "__default__"
            slurm_config = self.cluster_config[slurm_env]
            result = "salloc -J {jobname} {alloc} {srun} sh -c '{cmd}'".format(
                jobname=slurm_config.get("jobname", "cbuild"),
                alloc=slurm_config["salloc"],
                srun=("" if skip_srun else "srun"),
                cmd=self.escape_single_quotes(result),
            )
            # set the environment variables if needed
            env_vars = slurm_config.get("env_vars")
            if env_vars:
                result = "env {} {}".format(
                    " ".join(f"{k}={v}" for k, v in env_vars.items()),
                    result,
                )

        if module_env:
            modulepath, modules = self.MODULES[module_env]
            result = " && ".join(
                [
                    ". /etc/profile.d/modules.sh",
                    "module purge",
                    f"export MODULEPATH={modulepath}",
                    f"module load {' '.join(modules)}",
                    f"echo MODULEPATH={modulepath}",
                    "module list",
                    result,
                ]
            )

        return self.redirect_to_file(result)

    @staticmethod
    def spatial_index_files(prefix):
        return [
            f"{prefix}_{filename}"
            for filename in [
                "index.dat",
                "index.idx",
                "payload.dat",
            ]
        ]

    def build_circuit_config(self, nrn_path, cell_library_file):
        return self.bbp_env(
            "jinja2",
            [
                "jinja2 --strict",
                f"-D CIRCUIT_PATH={os.path.abspath(self.CIRCUIT_DIR)}",
                f"-D NRN_PATH={os.path.abspath(nrn_path)}",
                f"-D MORPH_PATH={self.MORPH_RELEASE}",
                f"-D ME_TYPE_PATH={self.EMODEL_RELEASE_HOC or 'SPECIFY_ME'}",
                self.format_if("-D ME_COMBO_INFO_PATH={}", self.EMODEL_RELEASE_MECOMBO),
                f"-D BIONAME={self.BIONAME}",
                f"-D ATLAS={self.ATLAS}",
                f"-D CELL_LIBRARY_FILE={cell_library_file}",
                self.template_path("CircuitConfig.j2"),
                "> {output}",
            ],
        )

    def get_targetgen_config(self, key, default_value=None):
        old = self.conf.get("targetgen_mvd3", default={})
        new = self.conf.get("targetgen", default={})
        if old and not new:
            logger.warning('"targetgen_mvd3" should be replaced by "targetgen" in MANIFEST.yaml')
            new = old
        return new.get(key, default_value)

    def write_network_config(self, connectome_dir):
        return self.bbp_env(
            "brainbuilder",
            [
                "brainbuilder sonata network-config",
                "--base-dir",
                "'.'",
                "--morph-dir",
                "components/morphologies",
                "--emodel-dir",
                "components/biophysical_neuron_models",
                "--nodes-dir",
                "networks/nodes",
                "--nodes",
                self.NODE_POPULATION_NAME,
                "--node-sets",
                self.NODESETS_FILE,
                "--edges-dir",
                f"networks/edges/{connectome_dir}",
                "--edges",
                self.EDGE_POPULATION_NAME,
                "-o {output}",
            ],
        )

    def run_spykfunc(self, rule, connectome_dir):
        assert rule in (
            "spykfunc_s2s",
            "spykfunc_s2f",
        ), "Unknown rule calling run_spykfunc"

        mode = None
        filters = self.conf.get([rule, "filters"], default=[])
        assert " " not in filters, "Filters cannot have spaces"

        if filters:
            mode = f"--filters {','.join(filters)}"

            # https://bbpteam.epfl.ch/project/issues/browse/FUNCZ-208?focusedCommentId=89736&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-89736
            if rule == "spykfunc_s2s":
                for filter_rule in (
                    "BoutonDistance",
                    "SynapseProperties",
                ):
                    assert filter_rule in filters, f"s2s should have rule {filter_rule}"
            elif rule == "spykfunc_s2f":
                for filter_rule in (
                    "BoutonDistance",
                    "TouchRules",
                    "ReduceAndCut",
                    "SynapseProperties",
                ):
                    assert filter_rule in filters, f"s2f should have rule {filter_rule}"
        elif rule == "spykfunc_s2s":
            mode = "--s2s"
        elif rule == "spykfunc_s2f":
            mode = "--s2f"

        output_dir = os.path.join(connectome_dir, "spykfunc")
        cmd = self.bbp_env(
            "spykfunc",
            [
                "env",
                "SPARK_USER=$(whoami)",
                "sm_run",
                self.cluster_config.get(rule, {}).get("sm_run", ""),
                f"-w {os.path.join(output_dir, '.sm_run')}",
                "spykfunc",
                mode,
                "--output-order post",
                f"--output-dir {output_dir}",
                "--spark-property spark.master=spark://$(srun sh -c '[ $SLURM_PROCID -eq 0 ] && hostname || true' | tail -n 1):7077",
            ]
            + [f"--spark-property {p}" for p in self.conf.get([rule, "spark_property"], default=[])]
            + [
                "--from",
                os.path.abspath("{input[neurons]}"),
                self.NODE_POPULATION_NAME,
                "--to",
                os.path.abspath("{input[neurons]}"),
                self.NODE_POPULATION_NAME,
                self.BUILDER_RECIPE,
                self.MORPH_RELEASE + "/h5v1/",
                "--parquet",
                os.path.abspath("{input[touches]}/*.parquet"),
            ],
            slurm_env=rule,
            skip_srun=True,
        )
        return cmd
