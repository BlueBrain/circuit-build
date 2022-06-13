import json
import shutil
from pathlib import Path

import h5py
from click.testing import CliRunner
from utils import TEST_PROJ_SYNTH, cwd, load_yaml

from circuit_build.cli import run


def test_synthesis(tmp_path):

    data_dir = TEST_PROJ_SYNTH

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
            args + ["functional"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        assert tmp_path.joinpath("CircuitConfig").stat().st_size > 100
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
        assert Path("auxiliary/axon-morphologies.tsv").stat().st_size > 100
        # test output from synthesize_morphologies
        assert Path("auxiliary/circuit.synthesized_morphologies.h5").stat().st_size > 100
        assert Path("auxiliary/circuit.ais_scales.h5").stat().st_size > 100

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
