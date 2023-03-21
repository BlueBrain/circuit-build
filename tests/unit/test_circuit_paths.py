from pathlib import Path

import pytest

from circuit_build.context import CircuitPaths


SELF_DIR = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    "attribute, expected",
    [
        ("circuit_dir", SELF_DIR / "build"),
        ("bioname_dir", SELF_DIR / "bioname"),
        ("connectome_dir", SELF_DIR / "build/connectome"),
        ("morphologies_dir", SELF_DIR / "build/morphologies"),
        ("networks_dir", SELF_DIR / "build/sonata/networks"),
    ],
)
def test_circuit_paths__attributes(attribute, expected):
    paths = CircuitPaths(circuit_dir=SELF_DIR / "build", bioname_dir=SELF_DIR / "bioname")

    assert getattr(paths, attribute) == expected


def test_circuit_paths__methods():
    circuit_dir = SELF_DIR / "build"
    bioname_dir = SELF_DIR / "bioname"

    paths = CircuitPaths(circuit_dir, bioname_dir)

    assert paths.sonata_path("file.h5") == SELF_DIR / "build/sonata/file.h5"
    assert paths.bioname_path("MANIFEST.yml") == SELF_DIR / "bioname/MANIFEST.yml"
    assert paths.auxiliary_path("temp_file.h5") == SELF_DIR / "build/auxiliary/temp_file.h5"
    assert (
        paths.nodes_path("p1", "file2.h5") == SELF_DIR / "build/sonata/networks/nodes/p1/file2.h5"
    )

    assert (
        paths.edges_path("p2", "file1.h5") == SELF_DIR / "build/sonata/networks/edges/p2/file1.h5"
    )

    assert paths.nodes_population_file("p1") == SELF_DIR / "build/sonata/networks/nodes/p1/nodes.h5"
    assert paths.edges_population_file("p2") == SELF_DIR / "build/sonata/networks/edges/p2/edges.h5"
    assert paths.nodes_population_morphologies_dir("p3/h5") == SELF_DIR / "build/morphologies/p3/h5"
    assert (
        paths.edges_population_connectome_path("pop", "p4") == SELF_DIR / "build/connectome/pop/p4"
    )
    assert paths.edges_population_touches_dir("pop1") == SELF_DIR / "build/connectome/pop1/touches"
