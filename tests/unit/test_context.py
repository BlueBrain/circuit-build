import json
import shutil
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from utils import (
    TEST_NGV_FULL,
    TEST_NGV_STANDALONE,
    TEST_PROJ_SYNTH,
    TEST_PROJ_TINY,
    cwd,
    edit_yaml,
)

from circuit_build import context as test_module
from circuit_build.constants import ENV_CONFIG
from circuit_build.utils import dump_yaml, load_yaml


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
    config = load_yaml(bioname / "MANIFEST.yaml")
    config["bioname"] = str(bioname)
    config["cluster_config"] = str(bioname / "cluster.yaml")
    return test_module.Context(config=config)


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


def test_context_load_env_config_default():
    bioname = TEST_PROJ_TINY
    ctx = _get_context(bioname)
    result = ctx.load_env_config()
    expected = ENV_CONFIG
    assert result == expected


def test_context_load_env_config_with_custom_modules(tmp_path):
    bioname = shutil.copytree(TEST_PROJ_TINY, tmp_path / "bioname")
    with edit_yaml(bioname / "MANIFEST.yaml") as manifest:
        del manifest["common"]["emodel_release"]
        manifest["modules"] = ["brainbuilder:archive/2020-08,brainbuilder/0.14.0"]

    ctx = _get_context(bioname)
    result = ctx.load_env_config()
    expected = deepcopy(ENV_CONFIG)
    expected["brainbuilder"]["modules"] = ["archive/2020-08", "brainbuilder/0.14.0"]
    assert result == expected


def test_context_load_env_config_with_custom_env_vars(tmp_path):
    bioname = shutil.copytree(TEST_PROJ_TINY, tmp_path / "bioname")
    environments = {
        "version": 1,
        "env_config": {
            "emodel-generalisation": {
                "env_vars": {
                    "MY_NEW_VAR": "MY_NEW_VALUE",
                    "NEURON_MODULE_OPTIONS": "OVERRIDDEN",
                }
            },
        },
    }
    dump_yaml(bioname / "environments.yaml", environments)

    ctx = _get_context(bioname)
    result = ctx.load_env_config()
    expected = deepcopy(ENV_CONFIG)
    assert "MY_NEW_VAR" not in expected["emodel-generalisation"]["env_vars"]
    assert expected["emodel-generalisation"]["env_vars"]["NEURON_MODULE_OPTIONS"] != "OVERRIDDEN"
    expected["emodel-generalisation"]["env_vars"]["MY_NEW_VAR"] = "MY_NEW_VALUE"
    expected["emodel-generalisation"]["env_vars"]["NEURON_MODULE_OPTIONS"] = "OVERRIDDEN"
    assert result == expected


def test_context_is_isolated_phase():
    bioname = TEST_PROJ_TINY
    ctx = _get_context(bioname)

    assert not ctx.is_isolated_phase()

    with patch.dict("os.environ", ISOLATED_PHASE="True"):
        assert ctx.is_isolated_phase()


@pytest.mark.parametrize("is_partial_config", [False, True])
def test_write_network_config__release(tmp_path, is_partial_config):
    circuit_dir = tmp_path / "test_write_network_config__release"
    circuit_dir.mkdir()

    bioname = TEST_PROJ_TINY

    with cwd(circuit_dir):
        ctx = _get_context(bioname)

        filepath = circuit_dir / "circuit_config.json"

        res = ctx.write_network_config(
            connectome_dir="functional", output_file=filepath, is_partial_config=is_partial_config
        )

        with open(filepath, "r", encoding="utf-8") as fd:
            config = json.load(fd)

    assert config == {
        "version": 2,
        **({"metadata": {"status": "partial"}} if is_partial_config else {}),
        "manifest": {"$BASE_DIR": "."},
        "node_sets_file": "$BASE_DIR/sonata/node_sets.json",
        "networks": {
            "nodes": [
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/nodes.h5",
                    "populations": {
                        "neocortex_neurons": {
                            "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_segment_index",
                            "type": "biophysical",
                            "alternate_morphologies": {
                                "h5v1": "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16/h5v1",
                                "neurolucida-asc": "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16/ascii",
                            },
                            "biophysical_neuron_models_dir": "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/hoc",
                            "provenance": {
                                "bioname_dir": f"{bioname}",
                            },
                        }
                    },
                }
            ],
            "edges": [
                {
                    "edges_file": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/edges.h5",
                    "populations": {
                        "neocortex_neurons__chemical_synapse": {
                            "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/spatial_synapse_index",
                            "type": "chemical",
                            "provenance": {
                                "bioname_dir": f"{bioname}",
                            },
                        }
                    },
                }
            ],
        },
    }


@pytest.mark.parametrize("is_partial_config", [False, True])
def test_write_network_config__synthesis(tmp_path, is_partial_config):
    circuit_dir = tmp_path / "test_write_network_config__synthesis"
    circuit_dir.mkdir()

    bioname = TEST_PROJ_SYNTH

    with cwd(circuit_dir):
        ctx = _get_context(bioname)

        filepath = circuit_dir / "circuit_config.json"

        res = ctx.write_network_config(
            connectome_dir="functional", output_file=filepath, is_partial_config=is_partial_config
        )

        with open(filepath, "r", encoding="utf-8") as fd:
            config = json.load(fd)

    assert config == {
        "version": 2,
        **({"metadata": {"status": "partial"}} if is_partial_config else {}),
        "manifest": {"$BASE_DIR": "."},
        "node_sets_file": "$BASE_DIR/sonata/node_sets.json",
        "networks": {
            "nodes": [
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/nodes.h5",
                    "populations": {
                        "neocortex_neurons": {
                            "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_segment_index",
                            "type": "biophysical",
                            "alternate_morphologies": {
                                "h5v1": "$BASE_DIR/morphologies/neocortex_neurons",
                                "neurolucida-asc": "$BASE_DIR/morphologies/neocortex_neurons",
                            },
                            "biophysical_neuron_models_dir": "$BASE_DIR/hoc_files",
                            "provenance": {
                                "bioname_dir": f"{bioname}",
                            },
                        }
                    },
                }
            ],
            "edges": [
                {
                    "edges_file": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/edges.h5",
                    "populations": {
                        "neocortex_neurons__chemical_synapse": {
                            "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/spatial_synapse_index",
                            "type": "chemical",
                            "provenance": {
                                "bioname_dir": f"{bioname}",
                            },
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
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/All/nodes.h5",
            "populations": {
                "All": {
                    "type": "biophysical",
                    "biophysical_neuron_models_dir": "$BASE_DIR/hoc_files",
                    "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/All/spatial_segment_index",
                    "alternate_morphologies": {
                        "neurolucida-asc": "$BASE_DIR/morphologies/All",
                        "h5v1": "$BASE_DIR/morphologies/All",
                    },
                    "provenance": {
                        "bioname_dir": f"{bioname}",
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
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
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
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                }
            },
        },
    ]
    assert config["networks"]["edges"] == [
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/functional/All/edges.h5",
            "populations": {
                "All": {
                    "type": "chemical",
                    "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/functional/All/spatial_synapse_index",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                }
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/neuroglial/edges.h5",
            "populations": {
                "neuroglial": {
                    "type": "synapse_astrocyte",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                },
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/glialglial/edges.h5",
            "populations": {
                "glialglial": {
                    "type": "glialglial",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                },
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/gliovascular/edges.h5",
            "populations": {
                "gliovascular": {
                    "type": "endfoot",
                    "endfeet_meshes_file": "$BASE_DIR/sonata/networks/edges/gliovascular/endfeet_meshes.h5",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
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

        ctx.write_network_ngv_config(output_file=filepath)

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
                    "biophysical_neuron_models_dir": "$BASE_DIR/hoc_files",
                    "spatial_segment_index_dir": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/spatial_segment_index",
                    "alternate_morphologies": {
                        "neurolucida-asc": "$BASE_DIR/morphologies/neocortex_neurons",
                        "h5v1": "$BASE_DIR/morphologies/neocortex_neurons",
                    },
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                },
            },
        },
        {
            "nodes_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/nodes.h5",
            "populations": {
                "astrocytes": {
                    "type": "astrocyte",
                    "alternate_morphologies": {"h5v1": "$BASE_DIR/morphologies/astrocytes/h5"},
                    "microdomains_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/microdomains.h5",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
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
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
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
                    "spatial_synapse_index_dir": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/spatial_synapse_index",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                }
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/neuroglial/edges.h5",
            "populations": {
                "neuroglial": {
                    "type": "synapse_astrocyte",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                },
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/glialglial/edges.h5",
            "populations": {
                "glialglial": {
                    "type": "glialglial",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                },
            },
        },
        {
            "edges_file": "$BASE_DIR/sonata/networks/edges/gliovascular/edges.h5",
            "populations": {
                "gliovascular": {
                    "type": "endfoot",
                    "endfeet_meshes_file": "$BASE_DIR/sonata/networks/edges/gliovascular/endfeet_meshes.h5",
                    "provenance": {
                        "bioname_dir": f"{bioname}",
                    },
                }
            },
        },
    ]


def test_provenance():
    context = _get_context(TEST_PROJ_TINY)
    assert context.provenance() == {"provenance": {"bioname_dir": context.paths.bioname_dir}}
