import json
import tempfile
from pathlib import Path

import pytest

from circuit_build import sonata_config as tested


def test_render_template_raises__missing_argument():
    with pytest.raises(TypeError, match="Population type 'biophysical' has mismatching arguments."):
        tested._render_template(
            {"nodes_file": "a", "population_type": "biophysical"},
            {"biophysical": tested._nodes_biophysical},
        )


def test_render_template_raises__extra_arguments():
    with pytest.raises(TypeError, match="Population type 'virtual' has mismatching arguments."):
        tested._render_template(
            {"nodes_file": "a", "population_type": "virtual", "invalid_arg": 2},
            {"virtual": tested._nodes_default},
        )


def test_render_template_raises__nonexistent_network_type():
    with pytest.raises(TypeError, match="Population type 'lennon' is not available."):
        tested._render_template(
            {"nodes_file": "a", "population_type": "lennon"}, {"virtual": tested._nodes_default}
        )


def test_nodes_config_template():
    result = tested._nodes_config_template(
        nodes_file="file",
        population_name="name",
        population_type="type",
        extra_entry1="val1",
        extra_entry2="val2",
    )
    assert result == {
        "nodes_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "extra_entry1": "val1",
                "extra_entry2": "val2",
            }
        },
    }


def test_nodes_default():
    result = tested._nodes_default(
        nodes_file="file",
        population_name="name",
        population_type="type",
        spatial_segment_index_dir="path/to/index",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "nodes_file": "file",
        "populations": {
            "name": {
                "spatial_segment_index_dir": "path/to/index",
                "type": "type",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


def test_nodes_biophysical():
    result = tested._nodes_biophysical(
        nodes_file="file",
        population_name="name",
        population_type="type",
        morphologies_dir="morphdir",
        biophysical_neuron_models_dir="biomodir",
        spatial_segment_index_dir="path/to/index",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "nodes_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "spatial_segment_index_dir": "path/to/index",
                "morphologies_dir": "morphdir",
                "biophysical_neuron_models_dir": "biomodir",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


def test_nodes_astrocyte():
    result = tested._nodes_astrocyte(
        nodes_file="file",
        population_name="name",
        population_type="type",
        morphologies_dir="morphdir",
        microdomains_file="mfile",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "nodes_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "alternate_morphologies": {"h5v1": "morphdir"},
                "microdomains_file": "mfile",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


def test_nodes_vasculature():
    result = tested._nodes_vasculature(
        nodes_file="file",
        population_name="name",
        population_type="type",
        vasculature_file="vfile",
        vasculature_mesh="vmesh",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "nodes_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "vasculature_file": "vfile",
                "vasculature_mesh": "vmesh",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


def tested_edges_config_template():
    result = tested._edges_config_template(
        edges_file="file",
        population_name="name",
        population_type="type",
        extra1="e1",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "edges_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "extra1": "e1",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


def tested_edges_default():
    result = tested._edges_default(
        edges_file="file",
        population_name="name",
        population_type="type",
        spatial_synapse_index_dir="path/to/index",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "edges_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "spatial_synapse_index_dir": "path/to/index",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


def tested_edges_endfoot():
    result = tested._edges_endfoot(
        edges_file="file",
        population_name="name",
        population_type="type",
        endfeet_meshes_file="mfile",
        provenance={
            "bioname_dir": "path/to/dir",
        },
    )
    assert result == {
        "edges_file": "file",
        "populations": {
            "name": {
                "type": "type",
                "endfeet_meshes_file": "mfile",
                "provenance": {
                    "bioname_dir": "path/to/dir",
                },
            }
        },
    }


@pytest.mark.parametrize(
    "circuit_dir, base_dir, path, expected",
    [
        ("/a", "/a/b", "$c", "$c"),
        ("/a", "/a/b", "", ""),
        ("/a", "/a/b", "/c/d", "/c/d"),
        ("/a", "/a/b", "/a/b/c", "$BASE_DIR/c"),
        ("/a", "/a/b", "/a/b/c/d", "$BASE_DIR/c/d"),
        ("/a", "/a/b/c", "/a/b/c/d", "$BASE_DIR/d"),
        ("/a", "/a/b", "/a/c/d", "$BASE_DIR/../c/d"),
        ("/a", "/a/b/c", "/a/d", "$BASE_DIR/../../d"),
        ("/a", "/a/b/c", "/a/d", "$BASE_DIR/../../d"),
        ("/a", "/a/b", "./c", "$BASE_DIR/c"),
        ("/a", "/a/b", "c/d", "$BASE_DIR/c/d"),
        ("/a", "/a/b", "../c", "$BASE_DIR/../c"),
    ],
)
def tested_resolve_path(circuit_dir, base_dir, path, expected):
    result = tested._resolve_path(path, Path(circuit_dir), Path(base_dir))
    assert result == expected


def _node_population(circuit_dir, name, kind):
    if kind == "virtual":
        return {
            "nodes_file": f"{circuit_dir}/sonata/networks/nodes/{name}/nodes.h5",
            "population_name": name,
            "population_type": "virtual",
            "spatial_segment_index_dir": "path/to/index",
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    if kind == "biophysical":
        return {
            "nodes_file": f"{circuit_dir}/sonata/networks/nodes/{name}/nodes.h5",
            "population_name": name,
            "population_type": "biophysical",
            "morphologies_dir": f"{circuit_dir}/morphologies/{name}/swc",
            "biophysical_neuron_models_dir": "/path/to/hoc",
            "spatial_segment_index_dir": "path/to/index",
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    if kind == "astrocyte":
        return {
            "nodes_file": f"{circuit_dir}/sonata/networks/nodes/{name}/nodes.h5",
            "population_name": name,
            "population_type": kind,
            "morphologies_dir": f"{circuit_dir}/morphologies/{name}/h5",
            "microdomains_file": f"{circuit_dir}/sonata/networks/nodes/{name}/microdomains.h5",
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    if kind == "vasculature":
        return {
            "nodes_file": f"{circuit_dir}/sonata/networks/nodes/{name}/nodes.h5",
            "population_name": name,
            "population_type": kind,
            "vasculature_file": "path/to/skeleton",
            "vasculature_mesh": "/path/to/mesh",
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    raise KeyError(f"kind {kind} is not registered in _node_population helper.")


def _node_population_expected(name, kind):
    if kind == "virtual":
        return {
            "nodes_file": f"$BASE_DIR/networks/nodes/{name}/nodes.h5",
            "populations": {
                name: {
                    "type": kind,
                    "spatial_segment_index_dir": "$BASE_DIR/path/to/index",
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                }
            },
        }
    if kind == "biophysical":
        return {
            "nodes_file": f"$BASE_DIR/networks/nodes/{name}/nodes.h5",
            "populations": {
                name: {
                    "type": kind,
                    "morphologies_dir": f"$BASE_DIR/../morphologies/{name}/swc",
                    "biophysical_neuron_models_dir": "/path/to/hoc",
                    "spatial_segment_index_dir": "$BASE_DIR/path/to/index",
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                },
            },
        }
    if kind == "astrocyte":
        return {
            "nodes_file": f"$BASE_DIR/networks/nodes/{name}/nodes.h5",
            "populations": {
                name: {
                    "type": kind,
                    "alternate_morphologies": {"h5v1": f"$BASE_DIR/../morphologies/{name}/h5"},
                    "microdomains_file": f"$BASE_DIR/networks/nodes/{name}/microdomains.h5",
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                },
            },
        }
    if kind == "vasculature":
        return {
            "nodes_file": f"$BASE_DIR/networks/nodes/{name}/nodes.h5",
            "populations": {
                name: {
                    "type": kind,
                    "vasculature_file": "$BASE_DIR/path/to/skeleton",
                    "vasculature_mesh": "/path/to/mesh",
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                },
            },
        }
    raise KeyError(f"kind {kind} is not registered in _node_population_expected helper.")


def _edge_population(circuit_dir, name, kind):
    if kind == "chemical":
        return {
            "edges_file": f"{circuit_dir}/sonata/networks/edges/functional/{name}/edges.h5",
            "population_name": name,
            "population_type": kind,
            "spatial_synapse_index_dir": "path/to/index",
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    if kind == "synapse_astrocyte":
        return {
            "edges_file": f"{circuit_dir}/sonata/networks/edges/{name}/edges.h5",
            "population_name": name,
            "population_type": kind,
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    if kind == "endfoot":
        return {
            "edges_file": f"{circuit_dir}/sonata/networks/edges/{name}/edges.h5",
            "population_name": name,
            "population_type": kind,
            "endfeet_meshes_file": f"{circuit_dir}/sonata/networks/edges/{name}/endfeet_meshes.h5",
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }
    if kind == "glialglial":
        return {
            "edges_file": f"{circuit_dir}/sonata/networks/edges/{name}/edges.h5",
            "population_name": name,
            "population_type": kind,
            "provenance": {
                "bioname_dir": "path/to/dir",
            },
        }

    raise KeyError(f"kind {kind} is not registered in _edge_population helper.")


def _edge_population_expected(name, kind):
    if kind == "chemical":
        return {
            "edges_file": f"$BASE_DIR/networks/edges/functional/{name}/edges.h5",
            "populations": {
                name: {
                    "type": kind,
                    "spatial_synapse_index_dir": "$BASE_DIR/path/to/index",
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                }
            },
        }
    if kind == "synapse_astrocyte":
        return {
            "edges_file": f"$BASE_DIR/networks/edges/{name}/edges.h5",
            "populations": {
                name: {
                    "type": kind,
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                },
            },
        }
    if kind == "endfoot":
        return {
            "edges_file": f"$BASE_DIR/networks/edges/{name}/edges.h5",
            "populations": {
                name: {
                    "type": kind,
                    "endfeet_meshes_file": f"$BASE_DIR/networks/edges/{name}/endfeet_meshes.h5",
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                }
            },
        }
    if kind == "glialglial":
        return {
            "edges_file": f"$BASE_DIR/networks/edges/{name}/edges.h5",
            "populations": {
                name: {
                    "type": kind,
                    "provenance": {
                        "bioname_dir": "$BASE_DIR/path/to/dir",
                    },
                },
            },
        }
    raise KeyError(f"kind {kind} is not registered in _edge_population_expected helper.")


def _build_write_load_config(filepath, circuit_dir, nodes, edges, node_sets_file):
    tested.write_config(filepath, circuit_dir, nodes, edges, node_sets_file)

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mock_circuit_dir(tmp_path_factory):
    circuit_dir = tmp_path_factory.mktemp("circuit_dir")
    sonata_dir = circuit_dir / "sonata"
    sonata_dir.mkdir()
    return circuit_dir


def test_write_config__equivalence(mock_circuit_dir):
    filepath1 = mock_circuit_dir / "sonata/test_write_config_1.json"
    filepath2 = mock_circuit_dir / "sonata/test_write_config_2.json"
    circuit_dir = filepath1.resolve().parent.parent

    tested.write_config(
        filepath1,
        circuit_dir,
        nodes=[_node_population(circuit_dir, name="nodeA", kind="biophysical")],
        edges=[_edge_population(circuit_dir, name="nodeA__nodeA__chemical", kind="chemical")],
        node_sets_file=f"{circuit_dir}/sonata/nodesets.json",
    )

    with open(filepath2, mode="w") as out:
        tested.write_config(
            out,
            circuit_dir,
            nodes=[_node_population(circuit_dir, name="nodeA", kind="biophysical")],
            edges=[_edge_population(circuit_dir, name="nodeA__nodeA__chemical", kind="chemical")],
            node_sets_file=f"{circuit_dir}/sonata/nodesets.json",
        )

    with open(filepath1, "r", encoding="utf-8") as f:
        config1 = json.load(f)

    with open(filepath2, "r", encoding="utf-8") as f:
        config2 = json.load(f)

    assert config1 == config2


def test_build_config__1_biophysical_1_chemical(mock_circuit_dir):
    """
    A single biophysical population with chemical synapses
    between neurons of that population
    """
    filepath = mock_circuit_dir / "sonata/config_1_biophysical_1_chemical.json"
    circuit_dir = filepath.resolve().parent.parent

    result = _build_write_load_config(
        filepath,
        circuit_dir,
        nodes=[_node_population(circuit_dir, name="nodeA", kind="biophysical")],
        edges=[_edge_population(circuit_dir, name="nodeA__nodeA__chemical", kind="chemical")],
        node_sets_file=f"{circuit_dir}/sonata/nodesets.json",
    )

    assert result == {
        "version": 2,
        "manifest": {"$BASE_DIR": "."},
        "node_sets_file": "$BASE_DIR/nodesets.json",
        "networks": {
            "nodes": [_node_population_expected(name="nodeA", kind="biophysical")],
            "edges": [_edge_population_expected(name="nodeA__nodeA__chemical", kind="chemical")],
        },
    }


def test_build_config__1_biophysical_1_virtual_2_chemical(mock_circuit_dir):
    """
    1 biophysical population with chemical synapses with itself
    1 virtual population with virtual connections to the biophysical one
    """
    filepath = mock_circuit_dir / "sonata/config_1_biophysical_1_virtual_2_chemical.json"
    circuit_dir = filepath.resolve().parent.parent

    result = _build_write_load_config(
        filepath,
        circuit_dir,
        nodes=[
            _node_population(circuit_dir, name="nodeA", kind="biophysical"),
            _node_population(circuit_dir, name="nodeB", kind="biophysical"),
            _node_population(circuit_dir, name="virtualA", kind="virtual"),
        ],
        edges=[
            _edge_population(circuit_dir, name="nodeA__nodeA__chemical", kind="chemical"),
            _edge_population(circuit_dir, name="virtualA__nodeA__chemical", kind="chemical"),
        ],
        node_sets_file="nodesets_filename",
    )
    assert result == {
        "version": 2,
        "manifest": {
            "$BASE_DIR": ".",
        },
        "node_sets_file": "$BASE_DIR/nodesets_filename",
        "networks": {
            "nodes": [
                _node_population_expected(name="nodeA", kind="biophysical"),
                _node_population_expected(name="nodeB", kind="biophysical"),
                _node_population_expected(name="virtualA", kind="virtual"),
            ],
            "edges": [
                _edge_population_expected(name="nodeA__nodeA__chemical", kind="chemical"),
                _edge_population_expected(name="virtualA__nodeA__chemical", kind="chemical"),
            ],
        },
    }


def test_build_config__2_biophysical_3_chemical(mock_circuit_dir):
    """2 biophysical populations
    3 pairwise connections
    """
    filepath = mock_circuit_dir / "sonata/config_2_biophysical_3_chemical.json"
    circuit_dir = filepath.resolve().parent.parent

    result = _build_write_load_config(
        filepath,
        circuit_dir,
        nodes=[
            _node_population(circuit_dir, name="nodeA", kind="biophysical"),
            _node_population(circuit_dir, name="nodeB", kind="biophysical"),
        ],
        edges=[
            _edge_population(circuit_dir, name="nodeA__nodeA__chemical", kind="chemical"),
            _edge_population(circuit_dir, name="nodeB__nodeB__chemical", kind="chemical"),
            _edge_population(circuit_dir, name="nodeA__nodeB__chemical", kind="chemical"),
            _edge_population(circuit_dir, name="nodeB__nodeA__chemical", kind="chemical"),
        ],
        node_sets_file="nodesets_filename",
    )
    assert result == {
        "version": 2,
        "manifest": {
            "$BASE_DIR": ".",
        },
        "node_sets_file": "$BASE_DIR/nodesets_filename",
        "networks": {
            "nodes": [
                _node_population_expected(name="nodeA", kind="biophysical"),
                _node_population_expected(name="nodeB", kind="biophysical"),
            ],
            "edges": [
                _edge_population_expected(name="nodeA__nodeA__chemical", kind="chemical"),
                _edge_population_expected(name="nodeB__nodeB__chemical", kind="chemical"),
                _edge_population_expected(name="nodeA__nodeB__chemical", kind="chemical"),
                _edge_population_expected(name="nodeB__nodeA__chemical", kind="chemical"),
            ],
        },
    }


def test_build_config__ngv(mock_circuit_dir):
    """
    nodes:
        1 biophysical population
        1 astrocyte population
        1 vasculature population
    edges:
        1 chemical population
        1 synapse_astrocyte population
        1 endfoot population
        1 glialglial population
    """
    filepath = mock_circuit_dir / "sonata/config_ngv.json"
    circuit_dir = filepath.resolve().parent.parent

    result = _build_write_load_config(
        filepath,
        circuit_dir,
        nodes=[
            _node_population(circuit_dir, name="neurons", kind="biophysical"),
            _node_population(circuit_dir, name="astrocytes", kind="astrocyte"),
            _node_population(circuit_dir, name="vasculature", kind="vasculature"),
        ],
        edges=[
            _edge_population(circuit_dir, name="neurons__neurons__chemical", kind="chemical"),
            _edge_population(
                circuit_dir, name="neurons__astrocytes__synapse_astrocyte", kind="synapse_astrocyte"
            ),
            _edge_population(
                circuit_dir, name="astrocytes__vasculature__glialglial", kind="endfoot"
            ),
            _edge_population(
                circuit_dir, name="astrocytes__astrocytes__glialglial", kind="glialglial"
            ),
        ],
        node_sets_file="nodesets_filename",
    )
    assert result == {
        "version": 2,
        "manifest": {
            "$BASE_DIR": ".",
        },
        "node_sets_file": "$BASE_DIR/nodesets_filename",
        "networks": {
            "nodes": [
                _node_population_expected(name="neurons", kind="biophysical"),
                _node_population_expected(name="astrocytes", kind="astrocyte"),
                _node_population_expected(name="vasculature", kind="vasculature"),
            ],
            "edges": [
                _edge_population_expected(name="neurons__neurons__chemical", kind="chemical"),
                _edge_population_expected(
                    name="neurons__astrocytes__synapse_astrocyte", kind="synapse_astrocyte"
                ),
                _edge_population_expected(
                    name="astrocytes__vasculature__glialglial", kind="endfoot"
                ),
                _edge_population_expected(
                    name="astrocytes__astrocytes__glialglial", kind="glialglial"
                ),
            ],
        },
    }
