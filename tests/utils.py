import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pkg_resources
import yaml

import circuit_build

TEST_DIR = Path(__file__).resolve().parent
TEST_DATA_DIR = TEST_DIR / 'proj66-tiny'
TEST_DATA_DIR_SYNTH = TEST_DIR / 'proj66-tiny-synth'
SNAKEFILE = pkg_resources.resource_filename(circuit_build.__name__, 'snakemake/Snakefile')
SNAKEMAKE_ARGS = ['--bioname', str(TEST_DATA_DIR), '-u', str(TEST_DATA_DIR / 'cluster.yaml')]


@contextmanager
def tmp_cwd():
    """Context manager to create a temporary directory and temporarily change the cwd."""
    original_cwd = os.getcwd()
    with tmp_mkdir() as name:
        try:
            os.chdir(name)
            yield name
        finally:
            os.chdir(original_cwd)


@contextmanager
def tmp_mkdir():
    """Context manager to create and return a temporary directory.

    Upon exiting the context, the directory and everything contained in it are removed,
    depending on the value of the environment variable DELETE_TEST_TMP_DIR:
        ALWAYS: always delete (default if the variable is not defined)
        ON_SUCCESS: delete only on success (useful for inspection in case of errors)
        NEVER: never delete (useful for full inspection)
    """
    error = False
    when = os.getenv('DELETE_TEST_TMP_DIR', 'ALWAYS')
    name = tempfile.mkdtemp(dir=TEST_DIR)
    try:
        yield name
    except:
        error = True
        raise
    finally:
        if when == 'ALWAYS' or when == 'ON_SUCCESS' and not error:
            shutil.rmtree(name, ignore_errors=True)


@contextmanager
def edit_yaml(yaml_file):
    """Context manager within which you can edit a yaml file.

    Args:
        yaml_file (Path): path to a yaml file

    Returns:
        Yields a dict instance of `yaml_file`. This instance will be saved later on the context
            manager leave.
    """
    with yaml_file.open('r') as f:
        config = yaml.safe_load(f)
    try:
        yield config
    finally:
        with yaml_file.open('w') as f:
            yaml.safe_dump(config, f)
