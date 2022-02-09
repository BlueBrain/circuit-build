"""Common functions used in Snakefile."""
import logging
import os.path
import subprocess
import traceback
import warnings
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict

import jsonschema
import pkg_resources
import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

import snakemake

logger = logging.getLogger(__name__)

SPACK_MODULEPATH = "/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta"
NIX_MODULEPATH = (
    "/nix/var/nix/profiles/per-user/modules/bb5-x86_64/modules-all/release/share/modulefiles/"
)
MODULES = {
    "brainbuilder": (SPACK_MODULEPATH, ["archive/2022-01", "brainbuilder/0.17.0"]),
    "flatindexer": (NIX_MODULEPATH, ["nix/hpc/flatindexer/1.8.12"]),
    "parquet-converters": (SPACK_MODULEPATH, ["archive/2021-10", "parquet-converters/0.7.0"]),
    "placement-algorithm": (SPACK_MODULEPATH, ["archive/2021-12", "placement-algorithm/2.3.0"]),
    "spykfunc": (SPACK_MODULEPATH, ["archive/2021-10", "spykfunc/0.17.1"]),
    "touchdetector": (SPACK_MODULEPATH, ["archive/2021-10", "touchdetector/5.6.1"]),
    "region-grower": (SPACK_MODULEPATH, ["archive/2021-09", "py-region-grower/0.3.0"]),
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


def _render_template(template_name, *args, **kwargs):
    env = Environment(
        loader=PackageLoader("circuit_build", "snakemake/templates"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    template = env.get_template(template_name)
    return template.render(*args, **kwargs)


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
        self.validate_config(config, "MANIFEST.yaml")
        self.validate_config(cluster_config, "cluster.yaml")

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

        self.NODE_POPULATION_NAME = self.validate_node_population_name(
            self.conf.get(["common", "node_population_name"])
        )
        self.EDGE_POPULATION_NAME = self.validate_edge_population_name(
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
        self.CONNECTOME_FUNCTIONAL_DIR = "connectome/functional"
        self.CONNECTOME_STRUCTURAL_DIR = "connectome/structural"
        self.MODULES = self.build_modules(MODULES)

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

    @staticmethod
    @contextmanager
    def write_with_log(out_file, log_file):
        """Context manager used to write to ``out_file``, and log any exception to ``log_file``."""
        with open(log_file, "w", encoding="utf-8") as lf:
            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    yield f
            except BaseException:
                lf.write(traceback.format_exc())
                raise

    @staticmethod
    def format_if(template, value, func=None):
        """Return the template formatted, or empty string if value is None."""
        func = func or (lambda x: x)
        return template.format(func(value)) if value is not None else ""

    @staticmethod
    def escape_single_quotes(value):
        """Return the given string after escaping the single quote character."""
        return value.replace("'", "'\\''")

    def log_path(self, name, _now=datetime.now()):
        """Return the path to the logfile for a given rule, and create the dir if needed."""
        timestamp = self.conf.get("timestamp", default=_now.strftime("%Y%m%dT%H%M%S"))
        path = os.path.abspath(os.path.join(self.LOGS_DIR, timestamp, f"{name}.log"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    @staticmethod
    def redirect_to_file(cmd, filename="{log}"):
        """Return a command string with the right redirection."""
        # very verbose output, but may be useful
        cmd = f"""set -ex; {cmd}"""
        if os.getenv("LOG_ALL_TO_STDERR") == "true":
            # Redirect stdout and stderr to file, and propagate everything to stderr.
            # Calling ``set -o pipefail`` is needed to propagate the exit code through the pipe.
            return f"set -o pipefail; ( {cmd} ) 2>&1 | tee -a {filename} 1>&2"
        # else redirect to file
        return f"( {cmd} ) >{filename} 2>&1"

    @staticmethod
    def template_path(name):
        """Return the template path."""
        return Path(pkg_resources.resource_filename(__name__, "templates")).resolve() / name

    @staticmethod
    def schema_path(name):
        """Return the schema path."""
        return Path(pkg_resources.resource_filename(__name__, "schemas")).resolve() / name

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
        cmd = self.redirect_to_file(cmd, filename=self.log_path("git_info"))
        path = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            subprocess.run(cmd, shell=True, check=True, cwd=path)
        except subprocess.CalledProcessError as ex:
            raise RuntimeError(
                f"bioname folder: {path} must be under git (version control system)"
            ) from ex

    def validate_config(self, config, schema_name):
        """Raise an exception if the configuration is not valid."""
        with self.schema_path(schema_name).open() as schema_fd:
            schema = yaml.safe_load(schema_fd)
        cls = jsonschema.validators.validator_for(schema)
        cls.check_schema(schema)
        validator = cls(schema)
        errors = list(validator.iter_errors(config))
        if errors:
            # Log an error message like the following:
            #  Invalid configuration: MANIFEST.yaml
            #  1: Failed validating root: Additional properties are not allowed ('x' was unexpected)
            #  2: Failed validating root.assign_emodels.seed: 'a' is not of type 'integer'
            msg = "\n".join(
                "{n}: Failed validating {path}: {message}".format(
                    n=n,
                    path=".".join(str(elem) for elem in ["root"] + list(e.absolute_path)),
                    message=e.message,
                )
                for n, e in enumerate(errors, 1)
            )
            logger.error("Invalid configuration: %s\n%s", schema_name, msg)
            raise Exception("Validation error")

    @staticmethod
    def validate_node_population_name(name):
        """Validate the name of the node population."""
        doc_url = "https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/bioname.html#manifest-yaml"
        allowed_parts = {"ncx", "neocortex", "hippocampus", "thalamus", "mousify"}
        allowed_types = {"neurons", "astrocytes", "projections"}
        msg = (
            '"node_population_name" in MANIFEST.yaml must exist and should fit the pattern: '
            f'"<part>_<type>", see {doc_url} for details'
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
        """Validate the name of the edge population."""
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
        """Return the dictionary of modules after overwriting it with the custom modules."""
        custom_modules = self.conf.get("modules")
        if custom_modules:
            # Custom modules can be configured using one of:
            # - configuration file MANIFEST.yaml -> list of str from yaml
            # - command line parameter --config -> list of str from json for backward compatibility
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
        """Wrap and return the command string to be executed."""
        result = " ".join(map(str, command))

        if slurm_env and self.cluster_config:
            if slurm_env in self.cluster_config:
                slurm_config = self.cluster_config[slurm_env]
            else:
                # break only if __default__ is needed and missing
                slurm_config = self.cluster_config["__default__"]
            result = "salloc -J {jobname} {alloc} {srun} sh -c '{cmd}'".format(
                jobname=slurm_config.get("jobname", slurm_env),
                alloc=slurm_config["salloc"],
                srun="" if skip_srun else "srun",
                cmd=self.escape_single_quotes(result),
            )
            # set the environment variables if needed
            env_vars = slurm_config.get("env_vars")
            if env_vars:
                variables = " ".join(f"{k}={v}" for k, v in env_vars.items())
                result = f"env {variables} {result}"

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
        """Return the list of files used for spatial index."""
        return [
            f"{prefix}_{filename}"
            for filename in [
                "index.dat",
                "index.idx",
                "payload.dat",
            ]
        ]

    def build_circuit_config(self, nrn_path, cell_library_file):
        """Return the BBP circuit configuration as a string."""
        return _render_template(
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
        return _render_template(
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
