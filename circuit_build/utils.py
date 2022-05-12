"""Common utilities."""
import importlib.resources
import os
import traceback
from contextlib import contextmanager

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from circuit_build.constants import PACKAGE_NAME, SCHEMAS_DIR, TEMPLATES_DIR


def load_yaml(filepath):
    """Load from YAML file."""
    with open(filepath, "r", encoding="utf-8") as fd:
        return yaml.safe_load(fd)


def dump_yaml(filepath, data, sort_keys=False):
    """Dump to YAML file."""
    with open(filepath, "w", encoding="utf-8") as fd:
        return yaml.safe_dump(data, fd, sort_keys=sort_keys)


def format_if(template, value, func=None):
    """Return the template formatted, or empty string if value is None."""
    func = func or (lambda x: x)
    return template.format(func(value)) if value is not None else ""


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


def render_template(template_name, *args, **kwargs):
    """Render a template and return the result as a string."""
    env = Environment(
        loader=PackageLoader(PACKAGE_NAME, TEMPLATES_DIR),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    template = env.get_template(template_name)
    return template.render(*args, **kwargs)
