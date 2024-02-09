from datetime import datetime
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from click.testing import CliRunner
from utils import TEST_PROJ_TINY

from circuit_build import cli as test_module


@patch("circuit_build.cli.Path.mkdir")
@patch("circuit_build.cli.Path.open", new_callable=mock_open)
@patch("circuit_build.cli.datetime")
@patch("circuit_build.cli.subprocess.run")
def test_ok(run_mock, datetime_mock, open_mock, mkdir_mock, snakefile, snakemake_args):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = "20210421T123456"
    runner = CliRunner()

    result = runner.invoke(test_module.run, snakemake_args, catch_exceptions=False)

    assert run_mock.call_count == 1
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 0
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        "--jobs",
        "8",
        "--printshellcmds",
    ]


@patch("circuit_build.cli.Path.mkdir")
@patch("circuit_build.cli.Path.open", new_callable=mock_open)
@patch("circuit_build.cli.datetime")
@patch("circuit_build.cli.subprocess.run")
def test_ok_with_summary(run_mock, datetime_mock, open_mock, mkdir_mock, snakefile, snakemake_args):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = "20210421T123456"
    runner = CliRunner()

    result = runner.invoke(
        test_module.run, snakemake_args + ["--with-summary"], catch_exceptions=False
    )

    assert run_mock.call_count == 2
    assert open_mock.call_count == 1
    assert mkdir_mock.call_count == 1
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        "--jobs",
        "8",
        "--printshellcmds",
    ]
    args = run_mock.call_args_list[1][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        "skip_check_git=1",
        "--jobs",
        "8",
        "--printshellcmds",
        "--detailed-summary",
    ]


@patch("circuit_build.cli.Path.mkdir")
@patch("circuit_build.cli.Path.open", new_callable=mock_open)
@patch("circuit_build.cli.datetime")
@patch("circuit_build.cli.subprocess.run")
def test_ok_with_report(run_mock, datetime_mock, open_mock, mkdir_mock, snakefile, snakemake_args):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = "20210421T123456"
    runner = CliRunner()

    result = runner.invoke(
        test_module.run, snakemake_args + ["--with-report"], catch_exceptions=False
    )

    assert run_mock.call_count == 2
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 1
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        "--jobs",
        "8",
        "--printshellcmds",
    ]
    args = run_mock.call_args_list[1][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        "skip_check_git=1",
        "--jobs",
        "8",
        "--printshellcmds",
        "--report",
        f"logs/{expected_timestamp}/report.html",
    ]


def test_config_is_set_already(snakemake_args):
    runner = CliRunner()
    expected_match = "snakemake `--config` option is not allowed"
    with pytest.raises(AssertionError, match=expected_match):
        runner.invoke(test_module.run, snakemake_args + ["--config", "a=b"], catch_exceptions=False)


@patch("circuit_build.cli.Path.mkdir")
@patch("circuit_build.cli.Path.open", new_callable=mock_open)
@patch("circuit_build.cli.datetime")
@patch("circuit_build.cli.subprocess.run")
def test_printshellcmds_is_not_set(run_mock, datetime_mock, open_mock, mkdir_mock, snakefile):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = "20210421T123456"
    runner = CliRunner()
    args = [
        "--bioname",
        str(TEST_PROJ_TINY),
        "--cluster-config",
        str(TEST_PROJ_TINY / "cluster.yaml"),
    ]

    result = runner.invoke(test_module.run, args, catch_exceptions=False)

    assert run_mock.call_count == 1
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 0
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        "--jobs",
        "8",
        "--printshellcmds",
    ]


@patch("circuit_build.cli.Path.mkdir")
@patch("circuit_build.cli.Path.open", new_callable=mock_open)
@patch("circuit_build.cli.datetime")
@patch("circuit_build.cli.subprocess.run")
def test_modules(run_mock, datetime_mock, open_mock, mkdir_mock, snakefile):
    run_mock.return_value.returncode = 0
    datetime_mock.now.return_value = datetime(2021, 4, 21, 12, 34, 56)
    expected_timestamp = "20210421T123456"
    runner = CliRunner()
    custom_module1 = "custom_module1:module1,module2/0.1"
    custom_module2 = "custom_module2:module1/0.2:/nix/modulefiles/"
    args = [
        "--bioname",
        str(TEST_PROJ_TINY),
        "--cluster-config",
        str(TEST_PROJ_TINY / "cluster.yaml"),
        "-m",
        custom_module1,
        "-m",
        custom_module2,
    ]

    result = runner.invoke(test_module.run, args, catch_exceptions=False)

    assert run_mock.call_count == 1
    assert open_mock.call_count == 0
    assert mkdir_mock.call_count == 0
    assert result.exit_code == 0
    args = run_mock.call_args_list[0][0][0]
    assert args == [
        "snakemake",
        "--snakefile",
        snakefile,
        "--directory",
        ".",
        "--config",
        f"bioname={TEST_PROJ_TINY}",
        f"timestamp={expected_timestamp}",
        f"cluster_config={TEST_PROJ_TINY / 'cluster.yaml'}",
        f'modules=["{custom_module1}","{custom_module2}"]',
        "--jobs",
        "8",
        "--printshellcmds",
    ]


def test_snakefile_none():
    with test_module._snakefile(None) as result:
        assert isinstance(result, Path)
        assert result.name == "Snakefile"


def test_snakefile_custom(tmp_path):
    snakefile = tmp_path / "Custom"
    snakefile.touch()
    with test_module._snakefile(snakefile) as result:
        assert isinstance(result, Path)
        assert result == snakefile


def test_snakefile_missing(tmp_path):
    snakefile = tmp_path / "Custom"
    with pytest.raises(RuntimeError, match="Snakefile .* does not exist!"):
        with test_module._snakefile(snakefile):
            pass
