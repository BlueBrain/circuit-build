from datetime import datetime
from unittest.mock import mock_open, patch

import pytest
from click.testing import CliRunner

from circuit_build.cli import run, snakefile_path

from utils import TEST_DATA_DIR, SNAKEMAKE_ARGS, SNAKEFILE


@patch('circuit_build.cli.Path.mkdir')
@patch('circuit_build.cli.Path.open', new_callable=mock_open)
@patch('circuit_build.cli.datetime')
@patch('circuit_build.cli.subprocess.run')
def test_ok(run_mock, datetime_mock, open_mock, mkdir_mock):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = '20210421T123456'
    runner = CliRunner()

    result = runner.invoke(run, SNAKEMAKE_ARGS, catch_exceptions=False)

    assert run_mock.call_count == 1
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 0
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml'),
    ]


@patch('circuit_build.cli.Path.mkdir')
@patch('circuit_build.cli.Path.open', new_callable=mock_open)
@patch('circuit_build.cli.datetime')
@patch('circuit_build.cli.subprocess.run')
def test_ok_with_summary(run_mock, datetime_mock, open_mock, mkdir_mock):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = '20210421T123456'
    runner = CliRunner()

    result = runner.invoke(run, SNAKEMAKE_ARGS + ['--with-summary'], catch_exceptions=False)

    assert run_mock.call_count == 2
    assert open_mock.call_count == 1
    assert mkdir_mock.call_count == 1
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml'),
    ]
    args = run_mock.call_args_list[1][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml'),
        '--detailed-summary',
    ]


@patch('circuit_build.cli.Path.mkdir')
@patch('circuit_build.cli.Path.open', new_callable=mock_open)
@patch('circuit_build.cli.datetime')
@patch('circuit_build.cli.subprocess.run')
def test_ok_with_report(run_mock, datetime_mock, open_mock, mkdir_mock):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = '20210421T123456'
    runner = CliRunner()

    result = runner.invoke(run, SNAKEMAKE_ARGS + ['--with-report'], catch_exceptions=False)

    assert run_mock.call_count == 2
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 1
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml'),
    ]
    args = run_mock.call_args_list[1][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml'),
        '--report', f'logs/{expected_timestamp}/report.html',
    ]


def test_config_is_set_already():
    runner = CliRunner()
    expected_match = 'snakemake `--config` option is not allowed'
    with pytest.raises(AssertionError, match=expected_match):
        runner.invoke(run, SNAKEMAKE_ARGS + ['--config', 'a=b'], catch_exceptions=False)


@patch('circuit_build.cli.Path.mkdir')
@patch('circuit_build.cli.Path.open', new_callable=mock_open)
@patch('circuit_build.cli.datetime')
@patch('circuit_build.cli.subprocess.run')
def test_printshellcmds_is_not_set(run_mock, datetime_mock, open_mock, mkdir_mock):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = '20210421T123456'
    runner = CliRunner()
    args = ['--bioname', str(TEST_DATA_DIR), '-u', str(TEST_DATA_DIR / 'cluster.yaml')]

    result = runner.invoke(run, args, catch_exceptions=False)

    assert run_mock.call_count == 1
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 0
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml')]


@patch('circuit_build.cli.Path.mkdir')
@patch('circuit_build.cli.Path.open', new_callable=mock_open)
@patch('circuit_build.cli.datetime')
@patch('circuit_build.cli.subprocess.run')
def test_modules(run_mock, datetime_mock, open_mock, mkdir_mock):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = '20210421T123456'
    runner = CliRunner()
    custom_module1 = 'custom_module1:module1,module2/0.1'
    custom_module2 = 'custom_module2:module1/0.2:/nix/modulefiles/'
    args = ['--bioname', str(TEST_DATA_DIR),
            '-u', str(TEST_DATA_DIR / 'cluster.yaml'),
            '-m', custom_module1, '-m', custom_module2]

    result = runner.invoke(run, args, catch_exceptions=False)

    assert run_mock.call_count == 1
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 0
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        'snakemake', '--jobs', '8', '--printshellcmds',
        '--config', f'bioname={TEST_DATA_DIR}',
        f'timestamp={expected_timestamp}',
        f'modules=["{custom_module1}", "{custom_module2}"]',
        '--snakefile', SNAKEFILE,
        '--cluster-config', str(TEST_DATA_DIR / 'cluster.yaml'),
    ]


def test_snakefile_path():
    runner = CliRunner()
    result = runner.invoke(snakefile_path, catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == SNAKEFILE
