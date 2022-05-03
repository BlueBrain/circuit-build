import os
from contextlib import contextmanager
from pathlib import Path

import pkg_resources
import yaml

import circuit_build

TEST_DIR = Path(__file__).resolve().parent
TEST_DATA_DIR = TEST_DIR / "proj66-tiny"
TEST_DATA_DIR_SYNTH = TEST_DIR / "proj66-tiny-synth"
TEST_DATA_DIR_NGV = TEST_DIR / "ngv"
SNAKEFILE = pkg_resources.resource_filename(circuit_build.__name__, "snakemake/Snakefile")
SNAKEMAKE_ARGS = ["--bioname", str(TEST_DATA_DIR), "-u", str(TEST_DATA_DIR / "cluster.yaml")]


@contextmanager
def cwd(path):
    """Context manager to temporarily change the working directory."""
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)


def load_yaml(filepath):
    """Load from YAML file."""
    with open(filepath, "r", encoding="utf-8") as fd:
        return yaml.safe_load(fd)


def dump_yaml(filepath, data):
    """Dump to YAML file."""
    with open(filepath, "w", encoding="utf-8") as fd:
        return yaml.safe_dump(data, fd)


@contextmanager
def edit_yaml(yaml_file):
    """Context manager within which you can edit a yaml file.

    Args:
        yaml_file (Path): path to a yaml file

    Returns:
        Yields a dict instance of `yaml_file`. This instance will be saved later on the context
            manager leave.
    """
    config = load_yaml(yaml_file)
    try:
        yield config
    finally:
        dump_yaml(yaml_file, config)
