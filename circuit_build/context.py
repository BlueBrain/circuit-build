"""Context used in Snakefile."""
import logging
import os.path
import subprocess
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict

import snakemake

from circuit_build.commands import build_command, load_legacy_env_config
from circuit_build.constants import ENV_CONFIG, ENV_FILE, INDEX_FILES
from circuit_build.utils import dump_yaml, load_yaml, redirect_to_file, render_template
from circuit_build.validators import (
    validate_config,
    validate_edge_population_name,
    validate_node_population_name,
)

logger = logging.getLogger(__name__)


class Config:
    """Configuration class."""

    def __init__(self, config):
        """Initialize the object.

        Args:
            config (dict): configuration dict.

        """
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
    """Context class."""

    def __init__(self, *, workflow: snakemake.Workflow, config: Dict, cluster_config: Dict):
        """Initialize the object.

        Args:
            workflow: workflow object provided by snakemake.
            config: configuration dict.
            cluster_config: cluster config dict.
        """
        self.workflow = workflow
        self.conf = Config(config=config)
        self.cluster_config = cluster_config
        self.BIONAME = str(Path(self.conf.get("bioname", default="bioname")).expanduser().resolve())

        # Load MANIFEST.yaml into workflow config
        self.workflow.configfile(self.bioname_path("MANIFEST.yaml"))
        # Validate the merged configuration and the cluster configuration
        validate_config(config, "MANIFEST.yaml")
        validate_config(cluster_config, "cluster.yaml")

        self.CIRCUIT_DIR = "."
        self.BUILDER_RECIPE = self.bioname_path("builderRecipeAllPathways.xml")
        self.MORPHDB = self.bioname_path("extNeuronDB.dat")
        self.SYNTHESIZE_PROTOCOL_CONFIG = self.bioname_path("protocol_config.yaml")

        self.SYNTHESIZE = self.conf.get(["common", "synthesis"], default=False)
        self.SYNTHESIZE_MORPH_DIR = str(Path("morphologies").resolve())
        self.SYNTHESIZE_MORPHDB = self.bioname_path("neurondb-axon.dat")
        self.PARTITION = self.if_synthesis(self.conf.get(["common", "partition"]), [])

        self.ATLAS = self.conf.get(["common", "atlas"])
        self.ATLAS_CACHE_DIR = ".atlas"

        self.NODE_POPULATION_NAME = validate_node_population_name(
            self.conf.get(["common", "node_population_name"])
        )
        self.EDGE_POPULATION_NAME = validate_edge_population_name(
            self.conf.get(["common", "edge_population_name"])
        )
        self.MORPH_RELEASE = self.conf.get(["common", "morph_release"])
        self.EMODEL_RELEASE = self.if_synthesis("", self.conf.get(["common", "emodel_release"]))
        self.SYNTHESIZE_EMODEL_RELEASE = self.if_synthesis(
            self.conf.get(["common", "synthesize_emodel_release"]), ""
        )
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
        self.TOUCHES_GLIA_DIR = "connectome/astrocytes/touches"
        self.CONNECTOME_FUNCTIONAL_DIR = "connectome/functional"
        self.CONNECTOME_STRUCTURAL_DIR = "connectome/structural"
        self.ENV_CONFIG = self.load_env_config()

    def bioname_path(self, filename):
        """Return the bioname path."""
        return str(Path(self.BIONAME, filename))

    def if_synthesis(self, true_value, false_value):
        """Return ``true_value`` if synthesis is enabled, else ``false_value``."""
        return true_value if self.SYNTHESIZE else false_value

    def if_partition(self, true_value, false_value):
        """Return ``true_value`` if partitions are enabled, else ``false_value``."""
        return true_value if self.PARTITION else false_value

    def partition_wildcard(self):
        """Return the partition wildcard to be used in snakemake commands."""
        return self.if_partition("_{partition}", "")

    def log_path(self, name, _now=datetime.now()):
        """Return the path to the logfile for a given rule, and create the dir if needed."""
        timestamp = self.conf.get("timestamp", default=_now.strftime("%Y%m%dT%H%M%S"))
        path = os.path.abspath(os.path.join(self.LOGS_DIR, timestamp, f"{name}.log"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def check_git(self, path):
        """Log some information and raise an exception if bioname is not under git control."""
        if self.conf.get("skip_check_git"):
            # should be skipped when circuit-build is run with --with-summary or --with-report
            return
        # strip away any git credentials added by the CI from `git remote get-url origin`
        cmd = """
            set -e +x
            echo "### Environment info"
            echo "date: $(date +'%Y-%m-%dT%H:%M:%S%z')"
            echo "user: $(whoami)"
            echo "host: $(hostname)"
            echo "circuit-build version: $(circuit-build --version)"
            echo "snakemake version: $(snakemake --version)"
            echo "bioname path: $(realpath .)"
            MD5SUM=$(which md5sum 2>/dev/null || which md5 2>/dev/null)
            [[ -n $MD5SUM ]] && find . -maxdepth 1 -type f | xargs $MD5SUM
            echo "### Git info"
            set -x
            git remote get-url origin | sed 's#://[^/@]*@#://#' || true
            git rev-parse --abbrev-ref HEAD
            git rev-parse HEAD
            git describe --abbrev --dirty --always --tags
            git --no-pager diff
            git --no-pager diff --staged
            """
        cmd = redirect_to_file(cmd, filename=self.log_path("git_info"))
        path = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            subprocess.run(cmd, shell=True, check=True, cwd=path)
        except subprocess.CalledProcessError as ex:
            raise RuntimeError(
                f"bioname folder: {path} must be under git (version control system)"
            ) from ex

    def load_env_config(self):
        """Load the environment configuration."""
        config = deepcopy(ENV_CONFIG)
        custom_modules = self.conf.get("modules", default=[])
        if custom_modules:
            logger.info("Loading custom modules (deprecated, use environments.yaml")
            config.update(load_legacy_env_config(custom_modules))
        custom_env_file = self.bioname_path(ENV_FILE)
        if os.path.exists(custom_env_file):
            logger.info("Loading custom environments")
            custom_env = load_yaml(custom_env_file)
            # validate the custom configuration
            validate_config(custom_env, "environments.yaml")
            config.update(custom_env["env_config"])
        # validate the final configuration
        validate_config({"env_config": config}, "environments.yaml")
        return config

    def dump_env_config(self):
        """Write the environment configuration into the log directory."""
        dump_yaml(self.log_path("environments"), data=self.ENV_CONFIG)

    def bbp_env(self, module_env, command, slurm_env=None, skip_srun=False):
        """Wrap and return the command string to be executed."""
        return build_command(
            cmd=command,
            env_config=self.ENV_CONFIG,
            env_name=module_env,
            cluster_config=self.cluster_config,
            slurm_env=slurm_env,
            skip_srun=skip_srun,
        )

    @staticmethod
    def spatial_index_files(prefix):
        """Return the list of files used for spatial index."""
        return [f"{prefix}_{filename}" for filename in INDEX_FILES]

    def build_circuit_config(self, nrn_path, cell_library_file):
        """Return the BBP circuit configuration as a string."""
        return render_template(
            "CircuitConfig.j2",
            CIRCUIT_PATH=os.path.abspath(self.CIRCUIT_DIR),
            NRN_PATH=os.path.abspath(nrn_path),
            MORPH_PATH=self.if_synthesis(self.SYNTHESIZE_MORPH_DIR, self.MORPH_RELEASE),
            ME_TYPE_PATH=self.EMODEL_RELEASE_HOC or "SPECIFY_ME",
            ME_COMBO_INFO_PATH=self.EMODEL_RELEASE_MECOMBO if self.EMODEL_RELEASE_MECOMBO else None,
            BIONAME=self.BIONAME,
            ATLAS=self.ATLAS,
            CELL_LIBRARY_FILE=cell_library_file,
        )

    def write_network_config(self, connectome_dir):
        """Return the SONATA circuit configuration as a string."""
        return render_template(
            "SonataConfig.j2",
            CONNECTOME_DIR=connectome_dir,
            NODESETS_FILE=self.NODESETS_FILE,
            NODE_POPULATION_NAME=self.NODE_POPULATION_NAME,
            EDGE_POPULATION_NAME=self.EDGE_POPULATION_NAME,
            MORPHOLOGIES_DIR=self.if_synthesis(self.SYNTHESIZE_MORPH_DIR, self.MORPH_RELEASE),
            BIOPHYSICAL_NEURON_MODELS_DIR=self.EMODEL_RELEASE_HOC or "",
        )

    def run_spykfunc(self, rule):
        """Return the spykfunc command as a string."""
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
                "USER=$(whoami)",
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
