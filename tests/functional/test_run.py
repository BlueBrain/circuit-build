import json
import shutil
import subprocess
import tempfile
import voxcell
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

import bluepysnap
import h5py
import pytest
from assertions import assert_node_population_morphologies_accessible
from click.testing import CliRunner
from utils import TEST_PROJ_TINY, cwd, edit_yaml, load_yaml

from circuit_build.cli import run
from circuit_build.constants import INDEX_SUCCESS_FILE


def _assert_git_initialized(path):
    result = subprocess.run(["git", "status"], cwd=path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _assert_git_not_initialized(path):
    result = subprocess.run(["git", "status"], cwd=path, capture_output=True, text=True)
    assert result.returncode != 0
    assert "not a git repository" in result.stderr.lower()


def _initialize_git(path):
    subprocess.run(["git", "init"], cwd=path, capture_output=True, text=True, check=True)


def test_place_cells__region_regex(tmp_path):
    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path):
        data_copy_dir = tmp_path / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)

        with edit_yaml(data_copy_dir / "MANIFEST.yaml") as manifest:
            manifest["common"]["region"] = "@mc2_Column|mc2_Column"

        args = [
            "--bioname",
            str(data_copy_dir),
            "--cluster-config",
            str(data_copy_dir / "cluster.yaml"),
        ]

        runner = CliRunner()
        result = runner.invoke(run, args + ["place_cells"])

        pop = voxcell.CellCollection.load_sonata(tmp_path / "auxiliary/circuit.somata.h5")

        assert pop.properties.region.unique().tolist() == ["L3", "L5"]


def test_functional_all(tmp_path):
    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path):
        data_copy_dir = tmp_path / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)

        manifest = load_yaml(data_copy_dir / "MANIFEST.yaml")
        node_population_name = manifest["common"]["node_population_name"]
        edge_population_name = manifest["common"]["edge_population_name"]

        args = [
            "--bioname",
            str(data_copy_dir),
            "--cluster-config",
            str(data_copy_dir / "cluster.yaml"),
        ]
        runner = CliRunner()
        result = runner.invoke(
            run,
            args + ["functional", "spatial_index_segment", "spatial_index_synapse"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        assert tmp_path.joinpath("sonata/node_sets.json").stat().st_size > 100
        assert tmp_path.joinpath("sonata/circuit_config.json").stat().st_size > 100

        index_file_path = (
            f"sonata/networks/nodes/{node_population_name}/"
            f"spatial_segment_index/{INDEX_SUCCESS_FILE}"
        )
        assert tmp_path.joinpath(index_file_path).stat().st_size > 100
        index_file_path = (
            f"sonata/networks/edges/functional/{edge_population_name}/"
            f"spatial_synapse_index/{INDEX_SUCCESS_FILE}"
        )
        assert tmp_path.joinpath(index_file_path).stat().st_size > 100

        nodes_file = (tmp_path / f"sonata/networks/nodes/{node_population_name}/nodes.h5").resolve()
        assert nodes_file.stat().st_size > 100
        with h5py.File(nodes_file, "r") as h5f:
            assert f"/nodes/{node_population_name}" in h5f

        edges_file = (
            tmp_path / f"sonata/networks/edges/functional/{edge_population_name}/edges.h5"
        ).resolve()
        assert edges_file.stat().st_size > 100
        # test output from choose_morphologies
        assert Path("auxiliary/morphologies.tsv").stat().st_size > 100
        # test output from synthesize_morphologies
        assert Path("auxiliary/circuit.morphologies.h5").stat().st_size > 100
        with h5py.File(edges_file, "r") as h5f:
            assert f"/edges/{edge_population_name}" in h5f
            assert (
                node_population_name
                == h5f[f"/edges/{edge_population_name}/source_node_id"].attrs["node_population"]
            )
            assert (
                node_population_name
                == h5f[f"/edges/{edge_population_name}/target_node_id"].attrs["node_population"]
            )
        with tmp_path.joinpath("sonata/circuit_config.json").open("r") as f:
            config = json.load(f)
            assert (
                config["networks"]["nodes"][0]["nodes_file"]
                == f"$BASE_DIR/networks/nodes/{node_population_name}/nodes.h5"
            )
            assert (
                config["networks"]["edges"][0]["edges_file"]
                == f"$BASE_DIR/networks/edges/functional/{edge_population_name}/edges.h5"
            )

        circuit = bluepysnap.Circuit(tmp_path / "sonata/circuit_config.json")
        assert_node_population_morphologies_accessible(
            circuit,
            population_name=node_population_name,
            extensions=["asc", "h5"],
        )


def test_no_emodel(tmp_path):
    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path):
        data_copy_dir = tmp_path / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        with edit_yaml(data_copy_dir / "MANIFEST.yaml") as manifest:
            del manifest["common"]["emodel_release"]
        args = [
            "--bioname",
            str(data_copy_dir),
            "--cluster-config",
            str(data_copy_dir / "cluster.yaml"),
        ]

        runner = CliRunner()
        result = runner.invoke(run, args + ["assign_emodels"], catch_exceptions=False)
        assert result.exit_code == 0
        assert tmp_path.joinpath("auxiliary", "circuit.h5").stat().st_size > 100


def test_custom_module(tmp_path, caplog, capfd, snakemake_args):
    with cwd(tmp_path):
        args = snakemake_args + ["-m", "brainbuilder:invalid_module1:invalid_module_path"]
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(
            run, args + [f"{tmp_path}/auxiliary/circuit.somata.h5"], catch_exceptions=False
        )

        captured = capfd.readouterr()
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "Snakemake process failed" in caplog.text
        # the stderr of the subprocess is available in captured.err and not result.stderr
        assert "Unable to locate a modulefile for 'invalid_module1'" in captured.err


def test_bioname_no_git(tmp_path, caplog, capfd):
    """This test verifies that bioname is checked to be under git."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        _assert_git_not_initialized(path=data_copy_dir)

        args = [
            "--bioname",
            str(data_copy_dir),
            "--cluster-config",
            str(data_copy_dir / "cluster.yaml"),
        ]
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(run, args + ["init_cells"], catch_exceptions=False)

        captured = capfd.readouterr()
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "Snakemake process failed" in caplog.text
        # the stderr of the subprocess is available in captured.err and not result.stderr
        assert f"{str(data_copy_dir)} must be under git" in captured.err


def test_bioname_ignore_git_if_isolated_phase(tmp_path):
    """This test verifies that the git check is disabled if env var ISOLATED_PHASE=True"""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        _assert_git_not_initialized(path=data_copy_dir)

        with patch.dict("os.environ", ISOLATED_PHASE="True"):
            args = [
                "--bioname",
                str(data_copy_dir),
                "--cluster-config",
                str(data_copy_dir / "cluster.yaml"),
            ]
            runner = CliRunner(mix_stderr=False)

            result = runner.invoke(run, args + ["init_cells"], catch_exceptions=False)
            assert result.exit_code == 0


def test_bioname_with_git(tmp_path):
    """This test verifies that bioname is valid when initialized with ``git init``."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        _assert_git_not_initialized(path=data_copy_dir)
        _initialize_git(path=data_copy_dir)
        _assert_git_initialized(path=data_copy_dir)

        args = [
            "--bioname",
            str(data_copy_dir),
            "--cluster-config",
            str(data_copy_dir / "cluster.yaml"),
        ]
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(run, args + ["init_cells"], catch_exceptions=False)

        assert result.exit_code == 0


def test_snakemake_bioname_no_git(tmp_path, snakefile):
    """This test verifies that bioname is checked to be under git when called via `snakemake`."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        _assert_git_not_initialized(path=data_copy_dir)

        args = [
            "--jobs",
            "8",
            "-p",
            "--config",
            f"bioname={data_copy_dir}",
            f"cluster_config={data_dir / 'cluster.yaml'}",
        ]
        cmd = ["snakemake", "--snakefile", snakefile] + args

        with pytest.raises(CalledProcessError) as exc_info:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        # the expected message is not contained in str(exception), but it's found in the stderr
        assert f"{str(data_copy_dir)} must be under git" in exc_info.value.stderr


def test_snakemake_bioname_with_git(tmp_path, snakefile):
    """This test verifies that bioname is valid when initialized with ``git init``."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        _assert_git_not_initialized(path=data_copy_dir)
        _initialize_git(path=data_copy_dir)
        _assert_git_initialized(path=data_copy_dir)

        args = [
            "--jobs",
            "8",
            "-p",
            "--config",
            f"bioname={data_copy_dir}",
            f"cluster_config={data_dir / 'cluster.yaml'}",
        ]
        cmd = ["snakemake", "--snakefile", snakefile] + args

        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0, result.stderr


def test_isolated_phase(tmp_path, snakefile):
    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path):
        data_copy_dir = Path(tmp_path) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)

        with edit_yaml(data_copy_dir / "MANIFEST.yaml") as manifest:
            del manifest["common"]["morph_release"]

        with patch.dict("os.environ", ISOLATED_PHASE="True"):
            args = [
                "--jobs",
                "8",
                "-p",
                "--config",
                f"bioname={data_copy_dir}",
                f"cluster_config={data_dir / 'cluster.yaml'}",
            ]
            cmd = ["snakemake", "--snakefile", snakefile] + args + ["--", "place_cells"]

            result = subprocess.run(cmd, capture_output=False, text=True)

            assert result.returncode == 0, result.stderr
