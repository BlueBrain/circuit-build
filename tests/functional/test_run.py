import json
import shutil
import subprocess
import bluepysnap
import tempfile
from pathlib import Path
from subprocess import CalledProcessError

import h5py
import pytest
from click.testing import CliRunner
from utils import SNAKEFILE, SNAKEMAKE_ARGS, TEST_PROJ_TINY, cwd, edit_yaml, load_yaml
from assertions import assert_node_population_morphologies_accessible
from circuit_build.cli import run


def test_functional_all(tmp_path):

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path):

        data_copy_dir = tmp_path / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)

        manifest = load_yaml(data_copy_dir / "MANIFEST.yaml")
        node_population_name = manifest["common"]["node_population_name"]
        edge_population_name = manifest["common"]["edge_population_name"]

        args = ["--bioname", str(data_copy_dir), "-u", str(data_copy_dir / "cluster.yaml")]
        runner = CliRunner()
        result = runner.invoke(
            run,
            args + ["functional", "spatial_index_segment"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        assert tmp_path.joinpath("CircuitConfig").stat().st_size > 100
        assert tmp_path.joinpath("circuit.mvd3").stat().st_size > 100
        assert tmp_path.joinpath("sonata/node_sets.json").stat().st_size > 100
        assert tmp_path.joinpath("sonata/circuit_config.json").stat().st_size > 100
        assert tmp_path.joinpath("start.target").stat().st_size > 100

        nodes_file = (tmp_path / f"sonata/networks/nodes/{node_population_name}/nodes.h5").resolve()
        assert f"CellLibraryFile {nodes_file}" in (tmp_path / "CircuitConfig").open().read()
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

        assert_node_population_morphologies_accessible(
            circuit=bluepysnap.Circuit(tmp_path / "sonata/circuit_config.json"),
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
        args = ["--bioname", str(data_copy_dir), "-u", str(data_copy_dir / "cluster.yaml")]

        runner = CliRunner()
        result = runner.invoke(run, args + ["assign_emodels"], catch_exceptions=False)
        assert result.exit_code == 0
        assert tmp_path.joinpath("circuit.h5").stat().st_size > 100


def test_custom_module(tmp_path, caplog, capfd):

    with cwd(tmp_path):
        args = SNAKEMAKE_ARGS + ["-m", "brainbuilder:invalid_module1:invalid_module_path"]
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


def test_no_git_bioname(tmp_path, caplog, capfd):
    """This test verifies that bioname is checked to be under git."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        args = ["--bioname", str(data_copy_dir), "-u", str(data_copy_dir / "cluster.yaml")]
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(run, args, catch_exceptions=False)

        captured = capfd.readouterr()
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert "Snakemake process failed" in caplog.text
        # the stderr of the subprocess is available in captured.err and not result.stderr
        assert f"{str(data_copy_dir)} must be under git" in captured.err


def test_snakemake_circuit_config(tmp_path):
    """This test verifies that building can happen via `snakemake`,
    and `CircuitConfig.j2` is accessible in this case."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path):
        args = [
            "--jobs",
            "8",
            "-p",
            "--config",
            f"bioname={data_dir}",
            "-u",
            str(data_dir / "cluster.yaml"),
        ]
        cmd = ["snakemake", "--snakefile", SNAKEFILE] + args + ["CircuitConfig_base"]
        result = subprocess.run(cmd, check=True)

        assert result.returncode == 0
        assert tmp_path.joinpath("CircuitConfig_base").stat().st_size > 100
        assert f"CellLibraryFile circuit.mvd3" in (tmp_path / "CircuitConfig_base").open().read()


def test_snakemake_no_git_bioname(tmp_path):
    """This test verifies that bioname is checked to be under git when called via `snakemake`."""

    data_dir = TEST_PROJ_TINY

    with cwd(tmp_path), tempfile.TemporaryDirectory() as data_copy_dir:
        # data_copy_dir must not be under git control
        data_copy_dir = Path(data_copy_dir) / data_dir.name
        shutil.copytree(data_dir, data_copy_dir)
        args = [
            "--jobs",
            "8",
            "-p",
            "--config",
            f"bioname={data_copy_dir}",
            "-u",
            str(data_dir / "cluster.yaml"),
        ]
        cmd = ["snakemake", "--snakefile", SNAKEFILE] + args + ["CircuitConfig_base"]

        with pytest.raises(CalledProcessError) as exc_info:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        # the expected message is not contained in str(exception), but it's found in the stderr
        assert f"{str(data_copy_dir)} must be under git" in exc_info.value.stderr
