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

SPACK_MODULEPATH = "/gpfs/bbp.cscs.ch/ssd/apps/hpc/jenkins/modules/all"
NIX_MODULEPATH = (
    "/nix/var/nix/profiles/per-user/modules/bb5-x86_64/modules-all/release/share/modulefiles/"
)
MODULES = {
    "brainbuilder": (SPACK_MODULEPATH, ["archive/2021-07", "brainbuilder/0.16.1"]),
    "flatindexer": (NIX_MODULEPATH, ["nix/hpc/flatindexer/1.8.12"]),
    "jinja2": (SPACK_MODULEPATH, ["archive/2021-07", "python-dev/0.4"]),
    "parquet-converters": (SPACK_MODULEPATH, ["archive/2021-07", "parquet-converters/0.6.1"]),
    "placement-algorithm": (SPACK_MODULEPATH, ["archive/2021-07", "placement-algorithm/2.1.2"]),
    "region-grower": (SPACK_MODULEPATH, ["archive/2021-07", "py-region-grower/0.2.3"]),
    "spykfunc": (SPACK_MODULEPATH, ["archive/2021-07", "spykfunc/0.16.99"]),
    "touchdetector": (SPACK_MODULEPATH, ["archive/2021-07", "touchdetector/5.6.0"]),
}


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

        self.SYNTHESIZE = self.conf.get(["common", "synthesis"], default=False)
        self.SYNTHESIZE_MORPH_DIR = "morphologies"
        self.SYNTHESIZE_MORPHDB = self.bioname_path("neurondb-axon.dat")
        self.PARTITION = self.if_synthesis(self.conf.get(["common", "partition"]), [])

        self.ATLAS = self.conf.get(["common", "atlas"])
        self.ATLAS_CACHE_DIR = ".atlas"

        self.NODE_POPULATION_NAME = self.validate_node_population_name(
            self.conf.get(["common", "node_population_name"])
        )
        self.EDGE_POPULATION_NAME = self.validate_edge_population_name(
            self.conf.get(["common", "edge_population_name"])
        )
        self.MORPH_RELEASE = self.conf.get(["common", "morph_release"])
        self.EMODEL_RELEASE = self.if_synthesis("", self.conf.get(["common", "emodel_release"]))
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
        self.MODULES = self.build_modules(MODULES)

    def bioname_path(self, filename):
        return str(Path(self.BIONAME, filename))

    def if_synthesis(self, true_value, false_value):
        return true_value if self.SYNTHESIZE else false_value

    def if_partition(self, true_value, false_value):
        return true_value if self.PARTITION else false_value

    def partition_wildcard(self):
        return self.if_partition("_{partition}", "")

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

    def check_git(self, path):
        """Log some information and raise an exception if bioname is not under git control."""
        # note: temporary git remote credentials added by the CI are stripped away if present
        cmd = """
            set -e
            echo "### Environment info"
            echo "date: $(date +'%Y-%m-%dT%H:%M:%S%z')"
            echo "user: $(whoami)"
            echo "host: $(hostname)"
            echo "circuit-build version: $(circuit-build --version)"
            echo "snakemake version: $(snakemake --version)"
            echo "bioname path: $(realpath .)"
            MD5SUM=$(which md5sum 2>/dev/null || which md5 2>/dev/null)
            [[ -n $MD5SUM ]] && $MD5SUM *
            echo "### Git info"
            set -x
            git remote get-url origin | sed 's#://[^/@]*@#://#' || true
            git rev-parse --abbrev-ref HEAD
            git rev-parse HEAD
            git describe --abbrev --dirty --always --tags
            git --no-pager diff
            git --no-pager diff --staged
            """
        cmd = self.redirect_to_file(cmd, filename=self.log_path("git_info"))
        path = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            subprocess.run(cmd, shell=True, check=True, cwd=path)
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
                    modules[module_name] = (SPACK_MODULEPATH, module_list)
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
                f"-D MORPH_PATH={self.if_synthesis(self.SYNTHESIZE_MORPH_DIR, self.MORPH_RELEASE)}",
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

    def run_spykfunc(self, rule):
        rules_conf = {
            "spykfunc_s2s": {
                "mode": "--s2s",
                "filters": {"BoutonDistance", "SynapseProperties"},
            },
            "spykfunc_s2f": {
                "mode": "--s2f",
                "filters": {"BoutonDistance", "TouchRules", "ReduceAndCut", "SynapseProperties"},
            },
        }
        if rule in rules_conf:
            mode = rules_conf[rule]["mode"]
            filters = self.conf.get([rule, "filters"], default=[])
            if filters:
                # https://bbpteam.epfl.ch/project/issues/browse/FUNCZ-208?focusedCommentId=89736&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-89736
                missing_filters = rules_conf[rule]["filters"].difference(filters)
                if missing_filters:
                    raise ValueError(f"{rule} should have filters {missing_filters}")
                if any(" " in f for f in filters):
                    raise ValueError("Filters cannot contain spaces")
                mode = f"--filters {','.join(filters)}"
            extra_args = [
                mode,
                "--output-order post",
                f"--from {Path('{input.neurons}').absolute()} {self.NODE_POPULATION_NAME}",
                f"--to {Path('{input.neurons}').absolute()} {self.NODE_POPULATION_NAME}",
                "--recipe",
                self.BUILDER_RECIPE,
                "--morphologies",
                self.if_synthesis(self.SYNTHESIZE_MORPH_DIR, self.MORPH_RELEASE + "/h5v1/"),
            ] + self.if_partition(
                [
                    f"--from-nodeset {Path('{input.nodesets}').absolute()} {{wildcards.partition}}",
                    f"--to-nodeset {Path('{input.nodesets}').absolute()} {{wildcards.partition}}",
                ],
                [],
            )
        elif rule == "spykfunc_merge":
            extra_args = ["--merge"]
        else:
            raise ValueError(f"Unrecognized rule {rule!r} in run_spykfunc")

        spark_properties = self.conf.get([rule, "spark_property"], default=[])
        cmd = self.bbp_env(
            "spykfunc",
            [
                "env",
                "SPARK_USER=$(whoami)",
                "sm_run",
                self.cluster_config.get(rule, {}).get("sm_run", ""),
                "-w {params.output_dir}/.sm_run",
                "spykfunc",
                "--output-dir {params.output_dir}",
                *[f"--spark-property {p}" for p in spark_properties],
                *extra_args,
                "{params.parquet_dirs}",
            ],
            slurm_env=rule,
            skip_srun=True,
        )
        return cmd
