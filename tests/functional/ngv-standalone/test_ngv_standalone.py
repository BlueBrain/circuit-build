from pathlib import Path
import subprocess
import jsondiff
import pytest
import traceback

import numpy as np
from numpy import testing as npt
from pandas import testing as pdt
from morph_tool import morphio_diff
from click.testing import CliRunner

import archngv
import morphio
import archngv.testing
from archngv.app.utils import load_json

from morphio.vasculature import Vasculature as mVasculature
from vascpy.point_vasculature import PointVasculature as sVasculature
from circuit_build.cli import run


TEST_DIR = Path(__file__).resolve().parent

BIONAME_DIR = TEST_DIR / "bioname"
BUILD_DIR = TEST_DIR / "build"
DATA_DIR = TEST_DIR / "data"
EXPECTED_DIR = TEST_DIR / "expected"


@pytest.fixture(scope="module")
def build_circuit(worker_id):
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
        catch_exceptions=True,
    )
    assert result.exit_code == 0, "".join(traceback.format_exception(*result.exc_info))


@pytest.fixture(scope="module")
def circuit(build_circuit):
    return archngv.NGVCircuit(BUILD_DIR / "ngv_config.json")


def _get_h5_files(directory):
    return sorted(filepath.name for filepath in Path(directory).glob("*.h5"))


def _filenames_verify_cardinality(actual_directory, expected_directory):
    """Return the expected filenames and check if the produced filenames
    are identical in number and names.
    """
    actual_filenames = _get_h5_files(actual_directory)
    desired_filenames = _get_h5_files(expected_directory)

    npt.assert_equal(
        actual_filenames,
        desired_filenames,
        err_msg=(
            f"Differing output filenames:\n"
            f"Actual  : {sorted(actual_filenames)}\n"
            f"Expected: {sorted(desired_filenames)}"
        ),
    )
    return desired_filenames


def test_build__glia_morphologies(build_circuit):

    filenames = _filenames_verify_cardinality(
        BUILD_DIR / "morphologies", EXPECTED_DIR / "morphologies"
    )
    for filename in filenames:

        diff_result = morphio_diff.diff(
            BUILD_DIR / "morphologies" / filename, EXPECTED_DIR / "morphologies" / filename
        )
        assert not diff_result, diff_result.info


def _h5_compare(actual_filepath, expected_filepath):

    assert actual_filepath.exists()
    assert expected_filepath.exists()

    result = subprocess.run(
        ["h5diff", "-v", "-c", "--delta=1e-5", actual_filepath, expected_filepath],
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout.decode()


@pytest.mark.parametrize(
    "population_filename",
    [
        "glia.h5",
        "vasculature.h5",
    ],
)
def test_build__sonata_nodes(build_circuit, population_filename):

    nodes_path = f"sonata/nodes/{population_filename}"
    _h5_compare(BUILD_DIR / nodes_path, EXPECTED_DIR / nodes_path)


@pytest.mark.parametrize(
    "population_filename",
    [
        "neuroglial.h5",
        "gliovascular.h5",
        "glialglial.h5",
    ],
)
def test_build__sonata_edges(build_circuit, population_filename):

    edges_path = f"sonata/edges/{population_filename}"
    _h5_compare(BUILD_DIR / edges_path, EXPECTED_DIR / edges_path)


def test_build__config(build_circuit):

    expected_sonata_config = {
        "manifest": {
            "$CIRCUIT_DIR": "../",
            "$BUILD_DIR": "$CIRCUIT_DIR/build",
            "$COMPONENT_DIR": "$BUILD_DIR",
            "$NETWORK_DIR": "$BUILD_DIR",
        },
        "networks": {
            "nodes": [
                {
                    "nodes_file": f"{DATA_DIR}/circuit/nodes.h5",
                    "populations": {
                        "All": {
                            "type": "biophysical",
                            "morphologies_dir": f"{DATA_DIR}/circuit/morphologies",
                        },
                    },
                },
                {
                    "nodes_file": "$NETWORK_DIR/sonata/nodes/vasculature.h5",
                    "populations": {
                        "vasculature": {
                            "type": "vasculature",
                            "vasculature_file": f"{DATA_DIR}/atlas/vasculature.h5",
                            "vasculature_mesh": f"{DATA_DIR}/atlas/vasculature.obj",
                        },
                    },
                },
                {
                    "nodes_file": "$NETWORK_DIR/sonata/nodes/glia.h5",
                    "populations": {
                        "astrocytes": {
                            "type": "protoplasmic_astrocytes",
                            "alternate_morphologies": {"h5v1": "$BUILD_DIR/morphologies"},
                            "microdomains_file": "$BUILD_DIR/microdomains.h5",
                        },
                    },
                },
            ],
            "edges": [
                {
                    "edges_file": f"{DATA_DIR}/circuit/edges.h5",
                    "populations": {
                        "All": {"type": "neuronal"},
                    },
                },
                {
                    "edges_file": "$NETWORK_DIR/sonata/edges/neuroglial.h5",
                    "populations": {"neuroglial": {"type": "neuroglial"}},
                },
                {
                    "edges_file": "$NETWORK_DIR/sonata/edges/glialglial.h5",
                    "populations": {"glialglial": {"type": "glialglial"}},
                },
                {
                    "edges_file": "$NETWORK_DIR/sonata/edges/gliovascular.h5",
                    "populations": {
                        "gliovascular": {
                            "type": "gliovascular",
                            "endfeet_meshes": "$BUILD_DIR/endfeet_meshes.h5",
                        }
                    },
                },
            ],
        },
        "atlases": {
            "intensity": f"{DATA_DIR}/atlas/[density]astrocytes.nrrd",
            "brain_regions": f"{DATA_DIR}/atlas/brain_regions.nrrd",
        },
    }

    build_sonata_config = load_json(BUILD_DIR / "ngv_config.json")
    assert not jsondiff.diff(build_sonata_config, expected_sonata_config)


def test_integrity(circuit):
    archngv.testing.assert_circuit_integrity(circuit)


def test_integrity__neuroglial_connectome__property_dtypes(circuit):

    ng_conn = circuit.neuroglial_connectome

    prop_dtypes = {
        "@source_node": np.int64,
        "@target_node": np.int64,
        "synapse_id": np.uint64,
        "astrocyte_section_id": np.uint32,
        "astrocyte_segment_id": np.uint32,
        "astrocyte_segment_offset": np.float32,
        "astrocyte_section_pos": np.float32,
        "astrocyte_center_x": np.float32,
        "astrocyte_center_y": np.float32,
        "astrocyte_center_z": np.float32,
    }

    expected_properties = set(prop_dtypes.keys())
    assert ng_conn.property_names == expected_properties, (
        ng_conn.property_names,
        expected_properties,
    )

    for property_name, expected_dtype in prop_dtypes.items():

        arr = ng_conn.get([0, 1], property_name)
        npt.assert_equal(arr.dtype, expected_dtype)


def test_integrity__neuroglial_connectome__annotation_equivalency(circuit):
    """Check that the section_id, segment_id, segment_offset annotation is equivalent to section_id, section_pos"""
    ng_conn = circuit.neuroglial_connectome

    data = ng_conn.get(
        edge_ids=None,
        properties=[
            "@source_node",
            "astrocyte_section_id",
            "astrocyte_segment_id",
            "astrocyte_segment_offset",
            "astrocyte_section_pos",
        ],
    )

    astro_ids = np.unique(data.loc[:, "@source_node"].to_numpy())
    astro_morphs = {
        int(i): morphio.Morphology(circuit.astrocytes.morph.get_filepath(int(i))) for i in astro_ids
    }

    for (
        _,
        astrocyte_id,
        section_id,
        segment_id,
        segment_offset,
        expected_section_pos,
    ) in data.itertuples():

        points = astro_morphs[astrocyte_id].sections[section_id].points
        segment_lengths = np.linalg.norm(points[1:] - points[:-1], axis=1)

        path_length = 0.0
        for i, length in enumerate(segment_lengths):
            if i < segment_id:
                path_length += length

        path_length += segment_offset

        # the section position is normalized by the section length
        section_position = path_length / segment_lengths.sum()

        npt.assert_allclose(section_position, expected_section_pos, atol=1e-6)


def test_integrity__gliovascular_connectome__property_dtypes(circuit):

    gv_conn = circuit.gliovascular_connectome

    prop_dtypes = {
        "@source_node": np.int64,
        "@target_node": np.int64,
        "endfoot_id": np.uint64,
        "endfoot_surface_x": np.float32,
        "endfoot_surface_y": np.float32,
        "endfoot_surface_z": np.float32,
        "endfoot_compartment_length": np.float32,
        "endfoot_compartment_diameter": np.float32,
        "endfoot_compartment_perimeter": np.float32,
        "astrocyte_section_id": np.uint32,
        "vasculature_section_id": np.uint32,
        "vasculature_segment_id": np.uint32,
    }

    expected_properties = set(prop_dtypes.keys())
    assert gv_conn.property_names == expected_properties, (
        gv_conn.property_names,
        expected_properties,
    )

    circuit_dtypes = gv_conn.property_dtypes

    for property_name, expected_dtype in prop_dtypes.items():
        npt.assert_equal(
            circuit_dtypes[property_name], expected_dtype, err_msg=f"Property: {property_name}"
        )


def test_integrity__vasculature_representations_consistency(circuit):
    """Test that it is equivalent to get the segment coordinates
    via the sonata and morphio representations
    """
    astrocytes = circuit.astrocytes
    gv_connectivity = circuit.gliovascular_connectome

    c_vasc = circuit.vasculature

    morphio_vasculature = mVasculature(c_vasc.config["vasculature_file"])
    sonata_vasculature = sVasculature.load_sonata(BUILD_DIR / "sonata/nodes/vasculature.h5")

    morphio_sections = morphio_vasculature.sections

    sonata_points = sonata_vasculature.points
    sonata_edges = sonata_vasculature.edges

    for aid in range(astrocytes.size):

        endfeet_ids = gv_connectivity.astrocyte_endfeet(aid)
        data = gv_connectivity.vasculature_sections_segments(endfeet_ids).to_numpy(dtype=np.int64)

        for edge_id, sec_id, seg_id in data:

            sonata_segment = sonata_points[sonata_edges[edge_id]]
            morphio_segment = morphio_sections[sec_id].points[seg_id : seg_id + 2]

            npt.assert_allclose(sonata_segment, morphio_segment)

    # convert section morphology to point graph
    v1 = circuit.vasculature.morphology.as_point_graph()

    # load point graph from sonata
    v2 = circuit.vasculature.point_graph

    pdt.assert_frame_equal(v1.node_properties, v2.node_properties, check_dtype=False)
    pdt.assert_frame_equal(v1.edge_properties, v2.edge_properties, check_dtype=False)
