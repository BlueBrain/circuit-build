from unittest.mock import patch
from click.testing import CliRunner
from nose.tools import assert_raises

from circuit_build.cli import run, snakefile_path

from utils import TEST_DATA_DIR, SNAKEMAKE_ARGS, SNAKEFILE


@patch('subprocess.run')
def test_ok(subprocess_mock):
    runner = CliRunner()
    result = runner.invoke(run, SNAKEMAKE_ARGS, catch_exceptions=False)
    assert subprocess_mock.call_count == 1
    assert result.exit_code == 0
    args = subprocess_mock.call_args[0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


def test_config_is_set_already():
    runner = CliRunner()
    with assert_raises(AssertionError) as err:
        runner.invoke(run, SNAKEMAKE_ARGS + ['--config', 'a=b'], catch_exceptions=False)
    assert err.exception.args[0] == 'snakemake `--config` option is not allowed'


@patch('subprocess.run')
def test_printshellcmds_is_not_set(subprocess_mock):
    runner = CliRunner()
    args = ['--bioname', str(TEST_DATA_DIR), '-u', str(TEST_DATA_DIR / 'cluster.yaml')]
    result = runner.invoke(run, args, catch_exceptions=False)
    assert subprocess_mock.call_count == 1
    assert result.exit_code == 0
    args = subprocess_mock.call_args[0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


@patch('subprocess.run')
def test_modules(subprocess_mock):
    runner = CliRunner()
    custom_module1 = 'custom_module1:module1,module2/0.1'
    custom_module2 = 'custom_module2:module1/0.2:/nix/modulefiles/'
    args = ['--bioname', str(TEST_DATA_DIR),
            '-u', str(TEST_DATA_DIR / 'cluster.yaml'),
            '-m', custom_module1, '-m', custom_module2]
    result = runner.invoke(run, args, catch_exceptions=False)
    assert subprocess_mock.call_count == 1
    assert result.exit_code == 0
    args = subprocess_mock.call_args[0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'modules=["{custom_module1}", "{custom_module2}"]',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


def test_snakefile_path():
    runner = CliRunner()
    result = runner.invoke(snakefile_path, catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == SNAKEFILE
