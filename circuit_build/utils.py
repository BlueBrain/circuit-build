"""Common utilities."""

import importlib.resources
import logging
import os
import shlex
import traceback
from contextlib import contextmanager

import yaml

from circuit_build.constants import PACKAGE_NAME, SCHEMAS_DIR

L = logging.getLogger(__name__)


def load_yaml(filepath):
    """Load from YAML file."""
    with open(filepath, "r", encoding="utf-8") as fd:
        return yaml.safe_load(fd)


def dump_yaml(filepath, data, sort_keys=False):
    """Dump to YAML file."""
    with open(filepath, "w", encoding="utf-8") as fd:
        return yaml.safe_dump(data, fd, sort_keys=sort_keys)


def if_then_else(condition, true_value, false_value):
    """Return ``true_value`` if condition, else ``false_value``.

    This can be used in Snakefile for better formatting.
    """
    return true_value if condition else false_value


def format_if(template, value, func=None):
    """Return the template formatted, or empty string if value is None."""
    func = func or (lambda x: x)
    return template.format(shlex.quote(str(func(value)))) if value is not None else ""


def format_dict_to_list(template, values):
    """Return a list of templates formatted with keys and values from the given dict of values.

    Args:
        template (str): template to be formatted with keys and values. It should contain
            `key` and `value` variables, for example: "--atlas-property {key} {value}".
        values (dict): dict of keys and values to be used to format the template.

    Returns:
        list of strings obtained after formatting template with each key and value.
    """
    return [template.format(key=k, value=v) for k, v in values.items()]


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


def read_schema(schema_name):
    """Load a schema and return the result as a dictionary."""
    resource = importlib.resources.files(PACKAGE_NAME) / SCHEMAS_DIR / schema_name
    content = resource.read_text()
    return yaml.safe_load(content)


def clean_slurm_env():
    """Remove PMI/SLURM variables that can cause issues when launching other slurm jobs.

    These variable are unset because launching slurm jobs from a node
    allocated using salloc may fail with the error:
        srun: fatal: SLURM_MEM_PER_CPU, SLURM_MEM_PER_GPU, and SLURM_MEM_PER_NODE
        are mutually exclusive.

    Copied from:
    https://bbpgitlab.epfl.ch/nse/connectome-tools/-/blob/d311b4b7/connectome_tools/utils.py#L208
    """
    for key in os.environ:
        if key.startswith(("PMI_", "SLURM_")) and not key.endswith(("_ACCOUNT", "_PARTITION")):
            L.debug("Deleting env variable %s", key)
            del os.environ[key]
