from pathlib import Path
import pytest

from click.testing import CliRunner

from archngv.app.utils import load_json

from circuit_build.cli import run


TEST_DIR = Path(__file__).resolve().parent

BIONAME_DIR = TEST_DIR / "bioname"
BUILD_DIR = TEST_DIR / "build"
ATLAS_DIR = TEST_DIR / "atlas"


@pytest.fixture(scope="module")
def build_circuit_full():
    """Fixture to build the circuit"""
    assert BIONAME_DIR.exists()

    runner = CliRunner()
    result = runner.invoke(
        run,
        [
            "--bioname",
            str(BIONAME_DIR),
            "-u",
            str(BIONAME_DIR / "cluster.yaml"),
            "--directory",
            str(BUILD_DIR),
            "ngv",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0


def test_build__full_config(build_circuit_full):

    expected_sonata_config = {
        "manifest": {
            "$BASE_DIR": ".",
        },
        "version": 2,
        "node_sets_file": "$BASE_DIR/sonata/node_sets.json",
        "networks": {
            "nodes": [
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/neocortex_neurons/nodes.h5",
                    "populations": {
                        "neocortex_neurons": {
                            "type": "biophysical",
                            "morphologies_dir": "$BASE_DIR/morphologies/neocortex_neurons",
                            "biophysical_neuron_models_dir": "",
                        },
                    },
                },
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/nodes.h5",
                    "populations": {
                        "astrocytes": {
                            "type": "astrocyte",
                            "alternate_morphologies": {
                                "h5v1": "$BASE_DIR/morphologies/astrocytes/h5"
                            },
                            "microdomains_file": "$BASE_DIR/sonata/networks/nodes/astrocytes/microdomains.h5",
                        },
                    },
                },
                {
                    "nodes_file": "$BASE_DIR/sonata/networks/nodes/vasculature/nodes.h5",
                    "populations": {
                        "vasculature": {
                            "type": "vasculature",
                            "vasculature_file": f"{ATLAS_DIR}/vasculature.h5",
                            "vasculature_mesh": f"{ATLAS_DIR}/vasculature.obj",
                        },
                    },
                },
            ],
            "edges": [
                {
                    "edges_file": "$BASE_DIR/sonata/networks/edges/functional/neocortex_neurons__chemical_synapse/edges.h5",
                    "populations": {
                        "neocortex_neurons__chemical_synapse": {"type": "chemical"},
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
            ],
        },
    }

    build_sonata_config = load_json(BUILD_DIR / "ngv_config.json")

    assert build_sonata_config == expected_sonata_config
