from contextlib import contextmanager
import pkg_resources
from pathlib import Path
import os
import tempfile

import circuit_build

TEST_DIR = Path(__file__).resolve().parent
TEST_DATA_DIR = TEST_DIR / 'proj66-tiny'
SNAKE_FILE = pkg_resources.resource_filename(circuit_build.__name__, 'snakemake/Snakefile')
SNAKEMAKE_ARGS = ['--bioname', str(TEST_DATA_DIR), '-u', str(TEST_DATA_DIR / 'cluster.yaml')]


@contextmanager
def tmp_cwd():
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmpdirname:
        try:
            os.chdir(tmpdirname)
            yield tmpdirname
        finally:
            os.chdir(original_cwd)
