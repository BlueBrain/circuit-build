import pkg_resources
from unittest.mock import patch
from click.testing import CliRunner
import circuit_build
from circuit_build.cli import run, snakefile_path
from utils import TEST_DATA_DIR, SNAKEMAKE_ARGS

snakefile = pkg_resources.resource_filename(circuit_build.__name__, 'snakemake/Snakefile')


def test_ok():
    with patch('subprocess.run') as subprocess_mock:
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS, catch_exceptions=False)
        assert subprocess_mock.call_count == 1
        assert result.exit_code == 0
        args = subprocess_mock.call_args[0][0]
        assert args == [
            'snakemake', '--jobs', '8', '--printshellcmds',
            '--config', 'bioname=' + str(TEST_DATA_DIR),
            '--snakefile', snakefile,
            '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


def test_config_is_set_already():
    with patch('subprocess.run') as subprocess_mock:
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ['--config', 'a=b'], catch_exceptions=False)
        assert subprocess_mock.call_count == 1
        assert result.exit_code == 0
        args = subprocess_mock.call_args[0][0]
        assert args == [
            'snakemake', '--jobs', '8', '--printshellcmds',
            '--config', 'a=b', 'bioname=' + str(TEST_DATA_DIR),
            '--snakefile', snakefile,
            '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


def test_printshellcmds_is_not_set():
    with patch('subprocess.run') as subprocess_mock:
        runner = CliRunner()
        args = ['--bioname', str(TEST_DATA_DIR), '-u', str(TEST_DATA_DIR / 'cluster.yaml')]
        result = runner.invoke(run, args, catch_exceptions=False)
        assert subprocess_mock.call_count == 1
        assert result.exit_code == 0
        args = subprocess_mock.call_args[0][0]
        assert args == [
            'snakemake', '--jobs', '8', '--printshellcmds',
            '--config', 'bioname=' + str(TEST_DATA_DIR),
            '--snakefile', snakefile,
            '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


def test_snakefile_path():
    runner = CliRunner()
    result = runner.invoke(snakefile_path, catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == snakefile
