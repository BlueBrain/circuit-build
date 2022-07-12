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
from circuit_build.sonata_config import write_config
from circuit_build.utils import dump_yaml, load_yaml, redirect_to_file, render_template
from circuit_build.validators import (
    validate_config,
    validate_edge_population_name,
    validate_morphology_release,
    validate_node_population_name,
)

logger = logging.getLogger(__name__)


def _make_abs(parent_dir, path):
    parent_dir = Path(parent_dir).expanduser().resolve()
    path = Path(path)

    if str(path).startswith("$"):
        return str(path)

    return str(Path(parent_dir, path).resolve())


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


class CircuitPaths:
    """Paths hierarchy for building circuits."""

    def __init__(self, circuit_dir, bioname_dir):
        """Initialize the paths objects.

        Args:
            circuit_dir (str|Path): Relative or absolute path to the working directory.
            bioname_dir (str|Path): Relative or absolute path to the bioname directory.
        """
        self.circuit_dir = Path(circuit_dir).expanduser().resolve()
        self.bioname_dir = Path(bioname_dir).expanduser().resolve()

        self.connectome_dir = Path(self.circuit_dir, "connectome")
        self.morphologies_dir = Path(self.circuit_dir, "morphologies")

        self.sonata_dir = Path(self.circuit_dir, "sonata")
        self.networks_dir = Path(self.sonata_dir, "networks")

        self.nodes_dir = Path(self.networks_dir, "nodes")
        self.edges_dir = Path(self.networks_dir, "edges")

        self.auxiliary_dir = self.circuit_dir / "auxiliary"
        self.logs_dir = self.circuit_dir / "logs"

    def sonata_path(self, filename):
        """Return sonata filepath."""
        return Path(self.circuit_dir, "sonata", filename)

    def bioname_path(self, filename):
        """Return the full path of the given filename in the bioname directory."""
        return self.bioname_dir / filename

    def auxiliary_path(self, path):
        """Return a path relative to the auxiliary dir."""
        return self.auxiliary_dir / path

    def nodes_path(self, population_name, filename):
        """Return nodes population filepath."""
        return Path(self.nodes_dir, population_name, filename)

    def edges_path(self, population_name, filename):
        """Return edges population filepath."""
        return Path(self.edges_dir, population_name, filename)

    def nodes_population_file(self, population_name):
        """Return nodes population nodes.h5 filepath."""
        return self.nodes_path(population_name, "nodes.h5")

    def edges_population_file(self, population_name):
        """Return nodes population edges.h5 filepath."""
        return self.edges_path(population_name, "edges.h5")

    def nodes_population_morphologies_dir(self, population_name):
        """Return nodes population morphology dir."""
        return self.morphologies_dir / population_name

    def edges_population_connectome_path(self, population_name, path):
        """Return edges population connectome dir."""
        return self.connectome_dir / f"{population_name}/{path}"

    def edges_population_touches_dir(self, population_name):
        """Return touches directory for the population with `population_name`."""
        return self.edges_population_connectome_path(population_name, "touches")


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

        self.paths = CircuitPaths(
            circuit_dir=".",
            bioname_dir=self.conf.get("bioname", default="bioname"),
        )

        # Load MANIFEST.yaml into workflow config
        self.workflow.configfile(self.paths.bioname_path("MANIFEST.yaml"))
        # Validate the merged configuration and the cluster configuration
        validate_config(config, "MANIFEST.yaml")
        validate_config(cluster_config, "cluster.yaml")

        self.BUILDER_RECIPE = self.paths.bioname_path("builderRecipeAllPathways.xml")
        self.MORPHDB = self.paths.bioname_path("extNeuronDB.dat")
        self.SYNTHESIZE_PROTOCOL_CONFIG = self.paths.bioname_path("protocol_config.yaml")

        self.SYNTHESIZE = self.conf.get(["common", "synthesis"], default=False)
        self.SYNTHESIZE_MORPH_DIR = self.paths.nodes_population_morphologies_dir(
            self.nodes_neurons_name
        )
        self.SYNTHESIZE_MORPHDB = self.paths.bioname_path("neurondb-axon.dat")
        self.PARTITION = self.if_synthesis(self.conf.get(["common", "partition"]), [])

        self.ATLAS = self.conf.get(["common", "atlas"])
        self.ATLAS_CACHE_DIR = ".atlas"

        self.MORPH_RELEASE = validate_morphology_release(self.conf.get(["common", "morph_release"]))
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

        self.NODESETS_FILE = self.paths.sonata_path("node_sets.json")
        self.ENV_CONFIG = self.load_env_config()

    @property
    def nodes_neurons_name(self):
        """Return neurons node population name."""
        return validate_node_population_name(self.conf.get(["common", "node_population_name"]))

    @property
    def nodes_astrocytes_name(self):
        """Return astrocytes node population name."""
        return self.conf.get(
            ["ngv", "common", "node_populations", "astrocytes"], default="astrocytes"
        )

    @property
    def nodes_vasculature_name(self):
        """Return vasculature node population name."""
        return self.conf.get(
            ["ngv", "common", "node_populations", "vasculature"], default="vasculature"
        )

    @property
    def nodes_neurons_file(self):
        """Return path to neurons nodes file."""
        return self.paths.nodes_population_file(self.nodes_neurons_name)

    @property
    def nodes_astrocytes_file(self):
        """Return path to astrocytes nodes file."""
        return self.paths.nodes_population_file(self.nodes_astrocytes_name)

    @property
    def nodes_vasculature_file(self):
        """Return path to vasculature nodes file."""
        return self.paths.nodes_population_file(self.nodes_vasculature_name)

    @property
    def nodes_astrocytes_morphologies_dir(self):
        """Return directory to astrocytic morphologies."""
        return self.paths.nodes_population_morphologies_dir(f"{self.nodes_astrocytes_name}/h5")

    @property
    def nodes_astrocytes_microdomains_file(self):
        """Return path to astrocytic microdomains file."""
        return self.paths.nodes_path(self.nodes_astrocytes_name, "microdomains.h5")

    @property
    def edges_neurons_neurons_name(self):
        """Return edge population name for neuron-neuron chemical connections."""
        return validate_edge_population_name(self.conf.get(["common", "edge_population_name"]))

    @property
    def edges_neurons_astrocytes_name(self):
        """Return edge population name for synapse_astrocyte connections."""
        return self.conf.get(
            ["ngv", "common", "edge_populations", "neurons_astrocytes"],
            default="neuroglial",
        )

    @property
    def edges_astrocytes_vasculature_name(self):
        """Return edge population name for endfoot connections."""
        return self.conf.get(
            ["ngv", "common", "edge_populations", "astrocytes_vasculature"],
            default="gliovascular",
        )

    @property
    def edges_astrocytes_astrocytes_name(self):
        """Return edge population name for glialglial connections."""
        return self.conf.get(
            ["ngv", "common", "edge_populations", "astrocytes_astrocytes"],
            default="glialglial",
        )

    def edges_neurons_neurons_file(self, connectome_type):
        """Return edges file for chemical connections."""
        return self.paths.edges_path(connectome_type, f"{self.edges_neurons_neurons_name}/edges.h5")

    @property
    def edges_neurons_astrocytes_file(self):
        """Return edges file for synapse_astrocyte connections."""
        return self.paths.edges_population_file(self.edges_neurons_astrocytes_name)

    @property
    def edges_astrocytes_vasculature_file(self):
        """Return edges file for endfoot connections."""
        return self.paths.edges_population_file(self.edges_astrocytes_vasculature_name)

    @property
    def edges_astrocytes_astrocytes_file(self):
        """Return edges file for glialglial connections."""
        return self.paths.edges_population_file(self.edges_astrocytes_astrocytes_name)

    @property
    def edges_astrocytes_vasculature_endfeet_meshes_file(self):
        """Return endfeet meshes file for endfoot connections."""
        return self.paths.edges_path(self.edges_astrocytes_vasculature_name, "endfeet_meshes.h5")

    def tmp_edges_neurons_chemical_connectome_path(self, path):
        """Return path relative to the neuronal chemical connectome directory."""
        return self.paths.edges_population_connectome_path(
            population_name=self.edges_neurons_neurons_name,
            path=path,
        )

    @property
    def tmp_edges_neurons_chemical_touches_dir(self):
        """Return the neuronal chemical touches directory."""
        return self.paths.edges_population_connectome_path(
            population_name=self.edges_neurons_neurons_name,
            path=f"touches{self.partition_wildcard()}/parquet",
        )

    @property
    def tmp_edges_astrocytes_glialglial_touches_dir(self):
        """Return the glialglial touches directory."""
        return self.paths.edges_population_touches_dir(
            population_name=self.edges_astrocytes_vasculature_name
        )

    def if_synthesis(self, true_value, false_value):
        """Return ``true_value`` if synthesis is enabled, else ``false_value``."""
        return true_value if self.SYNTHESIZE else false_value

    def if_partition(self, true_value, false_value):
        """Return ``true_value`` if partitions are enabled, else ``false_value``."""
        return true_value if self.PARTITION else false_value

    def is_ngv_standalone(self):
        """Return true if there is an entry 'base_circuit' in manifest[ngv][common]."""
        return "base_circuit" in self.conf.get(["ngv", "common"], default={})

    def if_ngv_standalone(self, true_value, false_value):
        """Return ``true_value`` if ngv standalone is enabled, else ``false_value``."""
        return true_value if self.is_ngv_standalone() else false_value

    def partition_wildcard(self):
        """Return the partition wildcard to be used in snakemake commands."""
        return self.if_partition("_{partition}", "")

    def log_path(self, name, _now=datetime.now()):
        """Return the path to the logfile for a given rule, and create the dir if needed."""
        timestamp = self.conf.get("timestamp", default=_now.strftime("%Y%m%dT%H%M%S"))
        path = str(self.paths.logs_dir / timestamp / f"{name}.log")
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
        custom_env_file = self.paths.bioname_path(ENV_FILE)
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

    def build_circuit_config(self, nrn_path, cell_library_file, morphology_type):
        """Return the BBP circuit configuration as a string."""
        type_to_subdir = {
            "asc": "ascii",
            "swc": "swc",
            "h5": "h5v1",
        }

        # morphology_type=None is used for the CircuitConfig_base which is needed for the
        # spatial_index_segment, which results in omitting the MorphologyType entry and
        # allow the index to implicity use the subdirectory it needs.
        if self.SYNTHESIZE:
            morphology_path = self.SYNTHESIZE_MORPH_DIR
        elif morphology_type is None:
            morphology_path = self.MORPH_RELEASE
        else:
            morphology_path = Path(self.MORPH_RELEASE, type_to_subdir[morphology_type])

        return render_template(
            "CircuitConfig.j2",
            CIRCUIT_PATH=self.paths.circuit_dir,
            NRN_PATH=os.path.abspath(nrn_path),
            MORPH_PATH=morphology_path,
            MORPH_TYPE=morphology_type,
            ME_TYPE_PATH=self.EMODEL_RELEASE_HOC or "SPECIFY_ME",
            ME_COMBO_INFO_PATH=self.EMODEL_RELEASE_MECOMBO or None,
            BIONAME=self.paths.bioname_dir,
            ATLAS=self.ATLAS,
            CELL_LIBRARY_FILE=cell_library_file,
        )

    def write_network_config(self, connectome_dir, output_file):
        """Return the SONATA circuit configuration for neurons."""
        morphologies_entry = self.if_synthesis(
            {
                "alternate_morphologies": {
                    "h5v1": self.SYNTHESIZE_MORPH_DIR,
                    "neurolucida-asc": self.SYNTHESIZE_MORPH_DIR,
                }
            },
            {
                "alternate_morphologies": {
                    "h5v1": Path(self.MORPH_RELEASE, "h5v1"),
                    "neurolucida-asc": Path(self.MORPH_RELEASE, "ascii"),
                }
            },
        )

        write_config(
            output_file=output_file,
            circuit_dir=self.paths.circuit_dir,
            nodes=[
                {
                    "nodes_file": self.nodes_neurons_file,
                    "population_type": "biophysical",
                    "population_name": self.nodes_neurons_name,
                    **morphologies_entry,
                    "biophysical_neuron_models_dir": self.EMODEL_RELEASE_HOC or "",
                },
            ],
            edges=[
                {
                    "edges_file": self.edges_neurons_neurons_file(connectome_type=connectome_dir),
                    "population_type": "chemical",
                    "population_name": self.edges_neurons_neurons_name,
                },
            ],
            node_sets_file=self.NODESETS_FILE,
        )

    def write_network_ngv_config(self, output_file):
        """Return the SONATA circuit configuration for the neuro-glia-vascular architecture."""
        write_config(
            output_file=output_file,
            circuit_dir=self.paths.circuit_dir,
            nodes=[
                self.if_ngv_standalone(
                    {
                        "nodes_file": _make_abs(
                            self.paths.bioname_dir,
                            self.conf.get(
                                ["ngv", "common", "base_circuit", "nodes_file"], default=""
                            ),
                        ),
                        "population_type": "biophysical",
                        "population_name": self.conf.get(
                            ["ngv", "common", "base_circuit", "node_population_name"]
                        ),
                        "alternate_morphologies": {
                            "h5v1": _make_abs(
                                self.paths.bioname_dir,
                                self.conf.get(
                                    ["ngv", "common", "base_circuit", "morphologies_dir"],
                                    default="",
                                ),
                            ),
                            "neurolucida-asc": _make_abs(
                                self.paths.bioname_dir,
                                self.conf.get(
                                    ["ngv", "common", "base_circuit", "morphologies_dir"],
                                    default="",
                                ),
                            ),
                        },
                        "biophysical_neuron_models_dir": "",
                    },
                    {
                        "nodes_file": self.nodes_neurons_file,
                        "population_type": "biophysical",
                        "population_name": self.nodes_neurons_name,
                        "alternate_morphologies": {
                            "h5v1": self.if_synthesis(
                                self.paths.nodes_population_morphologies_dir(
                                    self.nodes_neurons_name
                                ),
                                Path(self.MORPH_RELEASE, "h5v1"),
                            ),
                            "neurolucida-asc": self.if_synthesis(
                                self.paths.nodes_population_morphologies_dir(
                                    self.nodes_neurons_name
                                ),
                                Path(self.MORPH_RELEASE, "ascii"),
                            ),
                        },
                        "biophysical_neuron_models_dir": self.EMODEL_RELEASE_HOC or "",
                    },
                ),
                {
                    "nodes_file": self.nodes_astrocytes_file,
                    "population_type": "astrocyte",
                    "population_name": self.nodes_astrocytes_name,
                    "morphologies_dir": self.nodes_astrocytes_morphologies_dir,
                    "microdomains_file": self.nodes_astrocytes_microdomains_file,
                },
                {
                    "nodes_file": self.nodes_vasculature_file,
                    "population_type": "vasculature",
                    "population_name": self.nodes_vasculature_name,
                    "vasculature_file": _make_abs(
                        self.paths.bioname_dir, self.conf.get(["ngv", "common", "vasculature"])
                    ),
                    "vasculature_mesh": _make_abs(
                        self.paths.bioname_dir, self.conf.get(["ngv", "common", "vasculature_mesh"])
                    ),
                },
            ],
            edges=[
                self.if_ngv_standalone(
                    {
                        "edges_file": _make_abs(
                            self.paths.bioname_dir,
                            self.conf.get(
                                ["ngv", "common", "base_circuit", "edges_file"], default=""
                            ),
                        ),
                        "population_type": "chemical",
                        "population_name": self.conf.get(
                            ["ngv", "common", "base_circuit", "edge_population_name"]
                        ),
                    },
                    {
                        "edges_file": self.edges_neurons_neurons_file(connectome_type="functional"),
                        "population_type": "chemical",
                        "population_name": self.edges_neurons_neurons_name,
                    },
                ),
                {
                    "edges_file": self.edges_neurons_astrocytes_file,
                    "population_type": "synapse_astrocyte",
                    "population_name": self.edges_neurons_astrocytes_name,
                },
                {
                    "edges_file": self.edges_astrocytes_astrocytes_file,
                    "population_type": "glialglial",
                    "population_name": self.edges_astrocytes_astrocytes_name,
                },
                {
                    "edges_file": self.edges_astrocytes_vasculature_file,
                    "population_type": "endfoot",
                    "population_name": self.edges_astrocytes_vasculature_name,
                    "endfeet_meshes_file": self.edges_astrocytes_vasculature_endfeet_meshes_file,
                },
            ],
            node_sets_file=self.NODESETS_FILE,
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
                f"--from {'{input.neurons}'} {self.nodes_neurons_name}",
                f"--to {'{input.neurons}'} {self.nodes_neurons_name}",
                "--recipe",
                self.BUILDER_RECIPE,
                "--morphologies",
                self.if_synthesis(self.SYNTHESIZE_MORPH_DIR, Path(self.MORPH_RELEASE, "h5v1")),
            ] + self.if_partition(
                [
                    f"--from-nodeset {'{input.nodesets}'} {{wildcards.partition}}",
                    f"--to-nodeset {'{input.nodesets}'} {{wildcards.partition}}",
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
