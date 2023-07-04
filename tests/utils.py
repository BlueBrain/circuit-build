import os
from contextlib import contextmanager
from pathlib import Path

from circuit_build.utils import dump_yaml, load_yaml

TESTS_DIR = Path(__file__).resolve().parent
UNIT_TESTS_DATA = TESTS_DIR / "unit" / "data"
FUNC_TESTS_DATA = TESTS_DIR / "functional" / "data"
TEST_PROJ_TINY = FUNC_TESTS_DATA / "proj66-tiny"
TEST_PROJ_SYNTH = FUNC_TESTS_DATA / "proj66-tiny-synth"
TEST_NGV_STANDALONE = TESTS_DIR / "functional/ngv-standalone/bioname"
TEST_NGV_FULL = TESTS_DIR / "functional/ngv-full/bioname"


@contextmanager
def cwd(path):
    """Context manager to temporarily change the working directory."""
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)


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
