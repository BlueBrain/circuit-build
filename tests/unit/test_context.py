import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from circuit_build import context as test_module
from circuit_build.utils import load_yaml

from utils import (
    TEST_PROJ_TINY,
    TEST_PROJ_SYNTH,
    TEST_NGV_STANDALONE,
    TEST_NGV_FULL,
    cwd,
)


@pytest.mark.parametrize(
    "parent_dir, path, expected",
    [
        (".", "$A", "$A"),
        ("/a/b", "c", "/a/b/c"),
        ("/a/b", "/c", "/c"),
        (".", "c", str(Path(".").resolve() / "c")),
        ("..", "c", str(Path(".").resolve().parent / "c")),
        ("a", "c", str(Path(".").resolve() / "a/c")),
        ("a", "/c/d", "/c/d"),
    ],
)
def test_make_abs(parent_dir, path, expected):

    path = test_module._make_abs(parent_dir, path)
    assert path == expected


def _get_context(bioname):
    workflow = Mock()
    cluster_config = load_yaml(bioname / "cluster.yaml")
    config = load_yaml(bioname / "MANIFEST.yaml")
    config["bioname"] = str(bioname)
    return test_module.Context(workflow=workflow, config=config, cluster_config=cluster_config)


@pytest.mark.parametrize(
    "config_dict, keys, default, expected",
    [
        ({}, "key1", None, None),
        ({}, "key1", "value1", "value1"),
        ({}, ["section1", "key1"], None, None),
        ({}, ["section1", "key1"], "value1", "value1"),
        ({"section1": {"key1": "value2"}}, ["section1", "key1"], None, "value2"),
        ({"section1": {"key1": "value2"}}, ["section1", "key1"], "value1", "value2"),
    ],
)
def test_config_get(config_dict, keys, default, expected):
    config = test_module.Config(config_dict)
    result = config.get(keys, default=default)
    assert result == expected


@patch(f"{test_module.__name__}.os.path.exists")
def test_context_init(mocked_path_exists):
    cwd = Path().resolve()
    bioname = TEST_PROJ_TINY
    expected_emodel_release_mecombo = (
        "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/mecombo_emodel.tsv"
    )
    expected_emodel_release_hoc = (
        "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/hoc"
    )
    mocked_existing_paths = {expected_emodel_release_mecombo, expected_emodel_release_hoc}
    mocked_path_exists.side_effect = lambda x: x in mocked_existing_paths

    ctx = _get_context(bioname)

    assert isinstance(ctx, test_module.Context)
    assert ctx.paths.bioname_dir == bioname
    assert ctx.paths.circuit_dir == Path(".").resolve()
    assert ctx.BUILDER_RECIPE == bioname / "builderRecipeAllPathways.xml"
    assert ctx.MORPHDB == bioname / "extNeuronDB.dat"
    assert ctx.SYNTHESIZE_PROTOCOL_CONFIG == bioname / "protocol_config.yaml"
    assert ctx.SYNTHESIZE is False
    assert ctx.SYNTHESIZE_MORPH_DIR == cwd / "morphologies/neocortex_neurons"
    assert ctx.SYNTHESIZE_MORPHDB == bioname / "neurondb-axon.dat"
    assert ctx.PARTITION == []
    assert ctx.ATLAS == "/gpfs/bbp.cscs.ch/project/proj66/entities/dev/atlas/O1-152"
    assert ctx.ATLAS_CACHE_DIR == ".atlas"
    assert ctx.nodes_neurons_name == "neocortex_neurons"
    assert ctx.edges_neurons_neurons_name == "neocortex_neurons__chemical_synapse"
    assert ctx.MORPH_RELEASE == Path(
        "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16"
    )
    assert ctx.EMODEL_RELEASE == "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0"
    assert ctx.SYNTHESIZE_EMODEL_RELEASE == ""
    assert ctx.EMODEL_RELEASE_MECOMBO == expected_emodel_release_mecombo
    assert ctx.EMODEL_RELEASE_HOC == expected_emodel_release_hoc
    assert ctx.paths.logs_dir == cwd / "logs"
    assert ctx.NODESETS_FILE == cwd / "sonata/node_sets.json"


def test_context_is_isolated_phase():

    bioname = TEST_PROJ_TINY
    ctx = _get_context(bioname)

    assert not ctx.is_isolated_phase()

    with patch.dict("os.environ", ISOLATED_PHASE="True"):
        assert ctx.is_isolated_phase()


import json


def test_write_network_config__release(tmp_path):

    circuit_dir = tmp_path / "test_write_network_config__release"
    circuit_dir.mkdir()

    bioname = TEST_PROJ_TINY

    with cwd(circuit_dir):

        ctx = _get_context(bioname)

        filepath = circuit_dir / "circuit_config.json"

        res = ctx.write_network_config(connectome_dir="functional", output_file=filepath)

        with open(filepath, "r", encoding="utf-8") as fd:
            config = json.load(fd)

    assert config == {
        "version": 2,
        "manifest": {"$BASE_DIR": "."},
        "node_sets_file": "$BASE_DIR/sonata/node_sets.json",
        "networks": {
            "nodes": [
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/nodes.h5",
                    "populations": {
                        "neocortex_neurons": {
                            "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_index",
                            "type": "biophysical",
                            "alternate_morphologies": {
                                "h5v1": "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16/h5v1",
                                "neurolucida-asc": "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16/ascii",
                            },
                            "biophysical_neuron_models_dir": "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/hoc",
                        }
                    },
                }
            ],
            "edges": [
                {
                    "edges_file": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/edges.h5",
                    "populations": {
                        "neocortex_neurons__chemical_synapse": {
                            "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/neocortex_neurons__chemical_synapse/spatial_index",
                            "type": "chemical",
                        }
                    },
                }
            ],
        },
    }


def test_write_network_config__synthesis(tmp_path):

    circuit_dir = tmp_path / "test_write_network_config__synthesis"
    circuit_dir.mkdir()

    bioname = TEST_PROJ_SYNTH

    with cwd(circuit_dir):

        ctx = _get_context(bioname)

        filepath = circuit_dir / "circuit_config.json"

        res = ctx.write_network_config(connectome_dir="functional", output_file=filepath)

        with open(filepath, "r", encoding="utf-8") as fd:
            config = json.load(fd)

    assert config == {
        "version": 2,
        "manifest": {"$BASE_DIR": "."},
        "node_sets_file": "$BASE_DIR/sonata/node_sets.json",
        "networks": {
            "nodes": [
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/nodes.h5",
                    "populations": {
                        "neocortex_neurons": {
                            "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_index",
                            "type": "biophysical",
                            "alternate_morphologies": {
                                "h5v1": "$BASE_DIR/morphologies/neocortex_neurons",
                                "neurolucida-asc": "$BASE_DIR/morphologies/neocortex_neurons",
                            },
                            "biophysical_neuron_models_dir": "",
                        }
                    },
                }
            ],
            "edges": [
                {
                    "edges_file": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/edges.h5",
                    "populations": {
                        "neocortex_neurons__chemical_synapse": {
                            "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/neocortex_neurons__chemical_synapse/spatial_index",
                            "type": "chemical",
                        }
                    },
                }
            ],
        },
    }


def test_write_network_config__ngv_standalone(tmp_path):

    circuit_dir = tmp_path / "test_write_network_config__ngv_standalone"
    circuit_dir.mkdir()

    bioname = TEST_NGV_STANDALONE
    data = TEST_NGV_STANDALONE.parent / "data"

    with cwd(circuit_dir):

        ctx = _get_context(bioname)

        filepath = circuit_dir / "circuit_config.json"

        res = ctx.write_network_ngv_config(output_file=filepath)

        with open(filepath, "r", encoding="utf-8") as fd:
            config = json.load(fd)

    assert config["manifest"] == {"$BASE_DIR": "."}
    assert config["node_sets_file"] == "$BASE_DIR/sonata/node_sets.json"
    assert config["networks"]["nodes"] == [
        {
            "nodes_file": f"{data}/circuit/nodes.h5",
            "populations": {
                "All": {
                    "type": "biophysical",
                    "biophysical_neuron_models_dir": "",
                    "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_index",
                    "alternate_morphologies": {
                        "neurolucida-asc": f"{data}/circuit/morphologies",
                        "h5v1": f"{data}/circuit/morphologies",
                    },
                }
            },
        },
        {
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/nodes.h5",
            "populations": {
                "astrocytes": {
                    "type": "astrocyte",
                    "alternate_morphologies": {"h5v1": "$BASE_DIR/morphologies/astrocytes/h5"},
                    "microdomains_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/microdomains.h5",
                }
            },
        },
        {
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/vasculature/nodes.h5",
            "populations": {
                "vasculature": {
                    "type": "vasculature",
                    "vasculature_file": f"{data}/atlas/vasculature.h5",
                    "vasculature_mesh": f"{data}/atlas/vasculature.obj",
                }
            },
        },
    ]
    assert config["networks"]["edges"] == [
        {
            "edges_file": f"{data}/circuit/edges.h5",
            "populations": {
                "All": {
                    "type": "chemical",
                    "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/neocortex_neurons__chemical_synapse/spatial_index",
                }
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/neuroglial/edges.h5",
            "populations": {"neuroglial": {"type": "synapse_astrocyte"}},
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/glialglial/edges.h5",
            "populations": {"glialglial": {"type": "glialglial"}},
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/gliovascular/edges.h5",
            "populations": {
                "gliovascular": {
                    "type": "endfoot",
                    "endfeet_meshes_file": "$BASE_DIR/sonata/networks/edges/gliovascular/endfeet_meshes.h5",
                }
            },
        },
    ]


def test_write_network_config__ngv_full(tmp_path):

    circuit_dir = tmp_path / "test_write_network_config"
    circuit_dir.mkdir()

    bioname = TEST_NGV_FULL
    atlas = TEST_NGV_FULL.parent / "atlas"

    with cwd(circuit_dir):

        ctx = _get_context(bioname)

        filepath = circuit_dir / "circuit_config.json"

        res = ctx.write_network_ngv_config(output_file=filepath)

        with open(filepath, "r", encoding="utf-8") as fd:
            config = json.load(fd)

    assert config["manifest"] == {"$BASE_DIR": "."}
    assert config["node_sets_file"] == "$BASE_DIR/sonata/node_sets.json"
    assert config["networks"]["nodes"] == [
        {
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/nodes.h5",
            "populations": {
                "neocortex_neurons": {
                    "type": "biophysical",
                    "biophysical_neuron_models_dir": "",
                    "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_index",
                    "alternate_morphologies": {
                        "neurolucida-asc": "$BASE_DIR/morphologies/neocortex_neurons",
                        "h5v1": "$BASE_DIR/morphologies/neocortex_neurons",
                    },
                }
            },
        },
        {
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/nodes.h5",
            "populations": {
                "astrocytes": {
                    "type": "astrocyte",
                    "alternate_morphologies": {"h5v1": "$BASE_DIR/morphologies/astrocytes/h5"},
                    "microdomains_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/microdomains.h5",
                }
            },
        },
        {
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/vasculature/nodes.h5",
            "populations": {
                "vasculature": {
                    "type": "vasculature",
                    "vasculature_file": f"{atlas}/vasculature.h5",
                    "vasculature_mesh": f"{atlas}/vasculature.obj",
                }
            },
        },
    ]
    assert config["networks"]["edges"] == [
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/edges.h5",
            "populations": {
                "neocortex_neurons__chemical_synapse": {
                    "type": "chemical",
                    "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/neocortex_neurons__chemical_synapse/spatial_index",
                }
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/neuroglial/edges.h5",
            "populations": {"neuroglial": {"type": "synapse_astrocyte"}},
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/glialglial/edges.h5",
            "populations": {"glialglial": {"type": "glialglial"}},
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/gliovascular/edges.h5",
            "populations": {
                "gliovascular": {
                    "type": "endfoot",
                    "endfeet_meshes_file": "$BASE_DIR/sonata/networks/edges/gliovascular/endfeet_meshes.h5",
                }
            },
        },
    ]
