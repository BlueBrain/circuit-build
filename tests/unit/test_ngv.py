import os
import re
import json
import shutil
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock

import pytest

from circuit_build import ngv as test_module
from circuit_build.ngv import BaseConfigKeys

DATA_DIR = Path(__file__).parent / "data/circuit"


@pytest.fixture
def node_population_name():
    """Node population name used in test data nodes."""
    return "All"


@pytest.fixture
def edge_population_name():
    """Node population name used in test data edges."""
    return "All"


@pytest.fixture
def nodes_file():
    """Path to test nodes."""
    return str(DATA_DIR / "nodes.h5")


@pytest.fixture
def edges_file():
    """Path to test edges."""
    return str(DATA_DIR / "edges.h5")


@pytest.fixture
def morphologies_dir():
    """Path to test morphologies dir."""
    return str(DATA_DIR / "morphologies")


@pytest.fixture
def spatial_synapse_index_dir():
    """Path to spatial index for synapses dir."""
    return str(DATA_DIR / "spatial_synapse_index")


@pytest.fixture
def spatial_segment_index_dir():
    """path to spatial index for neuronal segments dir."""
    return str(DATA_DIR / "spatial_segment_index")


@pytest.fixture
def hoc_dir():
    """Path to hoc dir."""
    return str(DATA_DIR / "hoc")


@pytest.fixture
def circuit_config_file__wout_indices(
    tmp_path,
    nodes_file,
    hoc_dir,
    edges_file,
    node_population_name,
    edge_population_name,
    morphologies_dir,
):
    """Create circuit config without spatial indices."""
    config = {
        "manifest": {"$BASE_DIR": "."},
        "components": {"morphologies_dir": str(morphologies_dir)},
        "networks": {
            "nodes": [
                {
                    "nodes_file": str(nodes_file),
                    "populations": {
                        node_population_name: {"biophysical_neuron_models_dir": str(hoc_dir)}
                    },
                }
            ],
            "edges": [{"edges_file": str(edges_file), "populations": {edge_population_name: {}}}],
        },
    }
    path = tmp_path / "circuit_config__wout_indices.json"
    Path(path).write_text(json.dumps(config))
    return path


@pytest.fixture
def circuit_config_file__with_indices(
    tmp_path,
    nodes_file,
    hoc_dir,
    edges_file,
    node_population_name,
    edge_population_name,
    morphologies_dir,
    spatial_synapse_index_dir,
    spatial_segment_index_dir,
):
    """Create a base config with a path to  neuronal circuit config, with spatial indices."""
    config = {
        "manifest": {"$BASE_DIR": "."},
        "components": {"morphologies_dir": str(morphologies_dir)},
        "networks": {
            "nodes": [
                {
                    "nodes_file": str(nodes_file),
                    "populations": {
                        node_population_name: {
                            "biophysical_neuron_models_dir": str(hoc_dir),
                            "spatial_segment_index_dir": str(spatial_segment_index_dir),
                        }
                    },
                }
            ],
            "edges": [
                {
                    "edges_file": str(edges_file),
                    "populations": {
                        edge_population_name: {
                            "spatial_synapse_index_dir": str(spatial_synapse_index_dir),
                        }
                    },
                }
            ],
        },
    }
    path = tmp_path / "circuit_config__with_indices.json"
    Path(path).write_text(json.dumps(config))
    return path


@pytest.fixture
def circuit_config_file__alternate_morphologies(
    tmp_path,
    nodes_file,
    node_population_name,
    edges_file,
    edge_population_name,
    morphologies_dir,
    hoc_dir,
):
    config = {
        "manifest": {"$BASE_DIR": "."},
        "networks": {
            "nodes": [
                {
                    "nodes_file": str(nodes_file),
                    "populations": {
                        node_population_name: {
                            "biophysical_neuron_models_dir": str(hoc_dir),
                            "alternate_morphologies": {
                                "h5v1": str(morphologies_dir),
                                "asc": str(morphologies_dir),
                            },
                        },
                    },
                }
            ],
            "edges": [{"edges_file": str(edges_file), "populations": {edge_population_name: {}}}],
        },
    }
    path = tmp_path / "circuit_config__alternate_morphologies.json"
    Path(path).write_text(json.dumps(config))
    return path


@pytest.fixture
def circuit_dir(tmp_path):
    """Directory for local copy of circuit components."""
    directory = tmp_path / "circuit"
    directory.mkdir()
    return directory


@pytest.fixture
def circuit_config_file__relative_paths(
    circuit_dir,
    nodes_file,
    hoc_dir,
    edges_file,
    node_population_name,
    edge_population_name,
    morphologies_dir,
):
    shutil.copyfile(nodes_file, circuit_dir / "nodes.h5")
    shutil.copyfile(edges_file, circuit_dir / "edges.h5")

    shutil.copytree(morphologies_dir, circuit_dir / "morphologies")
    shutil.copytree(hoc_dir, circuit_dir / "hoc")

    config = {
        "manifest": {"$BASE_DIR": "."},
        "components": {"morphologies_dir": "$BASE_DIR/morphologies"},
        "networks": {
            "nodes": [
                {
                    "nodes_file": "$BASE_DIR/nodes.h5",
                    "populations": {
                        node_population_name: {"biophysical_neuron_models_dir": "$BASE_DIR/hoc"}
                    },
                }
            ],
            "edges": [
                {"edges_file": "$BASE_DIR/edges.h5", "populations": {edge_population_name: {}}}
            ],
        },
    }
    path = circuit_dir / "circuit_config__relative_paths.json"
    Path(path).write_text(json.dumps(config))
    return path


@pytest.fixture
def base_config__wout_indices(
    circuit_config_file__wout_indices, node_population_name, edge_population_name
):
    """Create a base config with a path to a neuronal circuit config, without spatial indices."""
    return {
        BaseConfigKeys.CONFIG: str(circuit_config_file__wout_indices),
        BaseConfigKeys.NODE_POPULATION_NAME: node_population_name,
        BaseConfigKeys.EDGE_POPULATION_NAME: edge_population_name,
    }


@pytest.fixture
def base_config__alternate_morphologies(
    circuit_config_file__alternate_morphologies,
    node_population_name,
    edge_population_name,
):
    """Create a base config with a path to a neuronal circuit config, with alternate morphologies."""
    return {
        BaseConfigKeys.CONFIG: str(circuit_config_file__alternate_morphologies),
        BaseConfigKeys.NODE_POPULATION_NAME: node_population_name,
        BaseConfigKeys.EDGE_POPULATION_NAME: edge_population_name,
    }


@pytest.fixture
def mock_context(tmp_path):
    """Mock circuit-build context with temporary path destinations."""
    mock = Mock()
    mock.nodes_neurons_file = str(tmp_path / "nodes.h5")
    mock.SYNTHESIZE_MORPH_DIR = str(tmp_path / "morphologies")
    mock.edges_neurons_neurons_file = lambda _: str(tmp_path / "edgs.h5")
    mock.edges_spatial_index_dir = str(tmp_path / "edges_spatial_index")
    mock.nodes_spatial_index_dir = str(tmp_path / "nodes_spatial_index")
    mock.paths.bioname_dir = str(tmp_path)
    mock.EMODEL_RELEASE_HOC = str(tmp_path / "hoc")
    return mock


@pytest.fixture
def base_config__relative_paths(
    circuit_config_file__relative_paths,
    node_population_name,
    edge_population_name,
):
    """Copy files and create a local config with only relative paths."""
    return {
        "config": str(circuit_config_file__relative_paths),
        "node_population_name": node_population_name,
        "edge_population_name": edge_population_name,
    }


@pytest.fixture
def base_config__with_indices(
    circuit_config_file__with_indices,
    nodes_file,
    edges_file,
    node_population_name,
    edge_population_name,
    morphologies_dir,
    spatial_synapse_index_dir,
    spatial_segment_index_dir,
):
    """Create a base config with a path to a neuronal circuit config, with spatial indices."""
    return {
        BaseConfigKeys.CONFIG: str(circuit_config_file__with_indices),
        BaseConfigKeys.NODE_POPULATION_NAME: node_population_name,
        BaseConfigKeys.EDGE_POPULATION_NAME: edge_population_name,
    }


def test_stage_ngv_base_circuit__wout_indices(
    base_config__wout_indices,
    mock_context,
    nodes_file,
    edges_file,
    morphologies_dir,
    spatial_synapse_index_dir,
    spatial_segment_index_dir,
):
    """Test staging of neuronal base circuit when a path to a config is passed, without spatial indices."""

    test_module.stage_ngv_base_circuit(base_config__wout_indices, mock_context)

    assert Path(mock_context.nodes_neurons_file).resolve() == Path(nodes_file)
    assert Path(mock_context.SYNTHESIZE_MORPH_DIR).resolve() == Path(morphologies_dir)
    assert Path(mock_context.edges_neurons_neurons_file("functional")).resolve() == Path(edges_file)
    assert not Path(mock_context.edges_spatial_index_dir).exists()
    assert not Path(mock_context.nodes_spatial_index_dir).exists()


def test_stage_ngv_base_circuit__with_indices(
    base_config__with_indices,
    mock_context,
    nodes_file,
    edges_file,
    morphologies_dir,
    spatial_synapse_index_dir,
    spatial_segment_index_dir,
):
    """Test staging of neuronal base circuit when a path to a config is passed, with spatial indices."""
    test_module.stage_ngv_base_circuit(base_config__with_indices, mock_context)

    assert Path(mock_context.nodes_neurons_file).resolve() == Path(nodes_file)
    assert Path(mock_context.SYNTHESIZE_MORPH_DIR).resolve() == Path(morphologies_dir)
    assert Path(mock_context.edges_neurons_neurons_file("functional")).resolve() == Path(edges_file)

    assert Path(mock_context.edges_spatial_index_dir).resolve() == Path(spatial_synapse_index_dir)
    assert Path(mock_context.nodes_spatial_index_dir).resolve() == Path(spatial_segment_index_dir)


def test_stage_ngv_base_circuit__alternative_morphologies(
    base_config__alternate_morphologies,
    mock_context,
    nodes_file,
    edges_file,
    morphologies_dir,
    spatial_synapse_index_dir,
    spatial_segment_index_dir,
):
    """Test staging of neuronal base circuit when a path to a config is passed, with alternate morphologies."""
    test_module.stage_ngv_base_circuit(base_config__alternate_morphologies, mock_context)

    assert Path(mock_context.nodes_neurons_file).resolve() == Path(nodes_file)
    assert Path(mock_context.SYNTHESIZE_MORPH_DIR).resolve() == Path(morphologies_dir)
    assert Path(mock_context.edges_neurons_neurons_file("functional")).resolve() == Path(edges_file)
    assert not Path(mock_context.edges_spatial_index_dir).exists()
    assert not Path(mock_context.nodes_spatial_index_dir).exists()


def test_stage_ngv_base_circuit__relative_paths(
    base_config__relative_paths,
    circuit_dir,
    mock_context,
    spatial_synapse_index_dir,
    spatial_segment_index_dir,
):
    """Test staging of neuronal base circuit when a path to a config is passed, with relative paths."""

    test_module.stage_ngv_base_circuit(base_config__relative_paths, mock_context)

    # Remember that circuit components have been copied to the temp circuit_dir directory and links point to that now
    assert Path(mock_context.nodes_neurons_file).resolve() == circuit_dir / "nodes.h5"
    assert Path(mock_context.SYNTHESIZE_MORPH_DIR).resolve() == circuit_dir / "morphologies"
    assert (
        Path(mock_context.edges_neurons_neurons_file("functional")).resolve()
        == circuit_dir / "edges.h5"
    )
    assert not Path(mock_context.edges_spatial_index_dir).exists()
    assert not Path(mock_context.nodes_spatial_index_dir).exists()


def test_stage_path__raises():
    """Test that nonexisting source path raises an error."""
    with pytest.raises(RuntimeError, match="Source path foo/bar.txt does not exist."):
        test_module._stage_path("foo/bar.txt", "None")


def test_stage_path__existing_target(tmp_path):
    """Test that staging raises an error if the target exists and it's not a symlink."""
    source = tmp_path / "foo.txt"
    source.touch()

    target = tmp_path / "bar.txt"
    target.touch()

    with pytest.raises(RuntimeError, match=f"Target {target} exists and is not a symbolic link."):
        test_module._stage_path(source, target)


def test_stage_path(tmp_path):
    """Test that symlinks to target files or directories are created."""
    source = tmp_path / "foo.txt"
    source.touch()

    target = tmp_path / "bar.txt"

    # test staging file
    test_module._stage_path(source, target)
    assert target.resolve() == source

    source = tmp_path / "foo"
    source.mkdir()

    target = tmp_path / "bar"

    # test staging directory
    test_module._stage_path(source, target)
    assert target.resolve() == source


def test_stage_path__unlink_existing(tmp_path):
    """Test that existing symlinks to target files or directories are removed."""
    source = tmp_path / "foo.txt"
    source.touch()

    target = tmp_path / "bar.txt"
    os.symlink(source, target)

    # test staging file
    test_module._stage_path(source, target)

    assert target.resolve() == source

    source = tmp_path / "foo"
    source.mkdir()

    target = tmp_path / "bar"
    os.symlink(source, target)

    # test staging directory
    test_module._stage_path(source, target)

    assert target.resolve() == source


def test_get_existing_path(tmp_path):

    dct = {"foo": "bar"}
    key = "foo"

    res = test_module._get_existing_path(dct, "NAN", raise_if_no_entry=False)
    assert res is None

    expected_str = "Key 'NAN' not in population properties: {'foo': 'bar'}"
    with pytest.raises(
        RuntimeError,
        match=re.escape(expected_str),
    ):
        test_module._get_existing_path(dct, "NAN", raise_if_no_entry=True)

    # entry in dict, not existing: raise in all cases
    with pytest.raises(FileNotFoundError, match="Path bar was not found."):
        test_module._get_existing_path(dct, key, raise_if_no_entry=False)

    with pytest.raises(FileNotFoundError, match="Path bar was not found."):
        test_module._get_existing_path(dct, key, raise_if_no_entry=True)

    foo = tmp_path / "foo.txt"
    foo.touch()

    dct = {"foo": str(foo)}

    # if key in dict and path exists, return entry
    res = test_module._get_existing_path(dct, key)
    assert res == foo


def test_get_components(
    tmp_path,
    circuit_config_file__wout_indices,
    node_population_name,
    edge_population_name,
    nodes_file,
    edges_file,
    morphologies_dir,
):

    # node and edge population name entries are mandatory
    expected_str = "Minimum ngv base circuit entries"
    with pytest.raises(RuntimeError, match=expected_str):
        test_module._get_components({})

    with pytest.raises(RuntimeError, match=expected_str):
        test_module._get_components({"node_population_name": "All"})

    with pytest.raises(RuntimeError, match=expected_str):
        test_module._get_components({"edge_population_name": "All"})

    base_config = {
        "node_population_name": "foo",
        "edge_population_name": edge_population_name,
        "config": circuit_config_file__wout_indices,
    }

    expected_str = "Node population name 'foo' not in node population names.\nExisting node population names: ['All']"
    with pytest.raises(RuntimeError, match=re.escape(expected_str)):
        test_module._get_components(base_config)

    base_config = {
        "node_population_name": node_population_name,
        "edge_population_name": "foo",
        "config": circuit_config_file__wout_indices,
    }

    expected_str = "Edge population name 'foo' not in edge population names.\nExisting edge population names: ['All']"
    with pytest.raises(RuntimeError, match=re.escape(expected_str)):
        test_module._get_components(base_config)

    base_config = {
        "node_population_name": node_population_name,
        "edge_population_name": edge_population_name,
        "config": circuit_config_file__wout_indices,
    }

    res = test_module._get_components(base_config)

    assert res.nodes_file == Path(nodes_file)
    assert res.edges_file == Path(edges_file)
    assert res.morphologies_dir == Path(morphologies_dir)
    assert res.synapse_index_dir is None
    assert res.segment_index_dir is None
