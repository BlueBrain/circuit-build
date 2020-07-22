from pathlib import Path
import os
import tempfile
from contextlib import contextmanager

TEST_DIR = Path(__file__).resolve().parent
TEST_DATA_DIR = TEST_DIR / 'proj66-tiny'
SNAKE_FILE = TEST_DIR.parent / 'snakemake' / 'Snakefile'
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
