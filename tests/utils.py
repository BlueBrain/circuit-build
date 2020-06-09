from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
TEST_DATA_DIR = TEST_DIR / 'proj66-tiny'
SNAKE_FILE = TEST_DIR.parent / 'snakemake' / 'Snakefile'
SNAKEMAKE_ARGS = [
    '-p', '-j8',
    '--snakefile', str(SNAKE_FILE),
    '--cluster-config', TEST_DATA_DIR / 'cluster.yaml',
    '--config', 'bioname=' + str(TEST_DATA_DIR)
]
