from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from circuit_build import context as test_module
from circuit_build.utils import load_yaml

from utils import TEST_PROJ_TINY, TEST_PROJ_SYNTH


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
    assert ctx.MORPH_RELEASE == "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16"
    assert ctx.EMODEL_RELEASE == "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0"
    assert ctx.SYNTHESIZE_EMODEL_RELEASE == ""
    assert ctx.EMODEL_RELEASE_MECOMBO == expected_emodel_release_mecombo
    assert ctx.EMODEL_RELEASE_HOC == expected_emodel_release_hoc
    assert ctx.paths.logs_dir == cwd / "logs"
    assert ctx.NODESETS_FILE == cwd / "sonata/node_sets.json"


def test_build_circuit_config__release():

    bioname = TEST_PROJ_TINY
    ctx = _get_context(bioname)

    res = ctx.build_circuit_config(
        nrn_path="my-nrn-path",
        cell_library_file="my-cell-library-file",
        morphology_type="asc",
    )

    cwd = Path(".").resolve()

    assert res == (
        "Run Default\n"
        "{\n"
        f"    CircuitPath {cwd}\n"
        f"    nrnPath {cwd}/my-nrn-path\n"
        "    MorphologyPath /gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16/ascii\n"
        "    MorphologyType asc\n"
        "    METypePath /gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/hoc\n"
        "    MEComboInfoFile /gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/mecombo_emodel.tsv\n"
        "    CellLibraryFile my-cell-library-file\n"
        f"    BioName {bioname}\n"
        "    Atlas /gpfs/bbp.cscs.ch/project/proj66/entities/dev/atlas/O1-152\n"
        "}"
    )


def test_build_circuit_config__synthesis():

    bioname = TEST_PROJ_SYNTH
    ctx = _get_context(bioname)

    res = ctx.build_circuit_config(
        nrn_path="my-nrn-path",
        cell_library_file="my-cell-library-file",
        morphology_type="asc",
    )

    cwd = Path(".").resolve()
    assert res == (
        "Run Default\n"
        "{\n"
        f"    CircuitPath {cwd}\n"
        f"    nrnPath {cwd}/my-nrn-path\n"
        f"    MorphologyPath {cwd}/morphologies/neocortex_neurons\n"
        "    MorphologyType asc\n"
        "    METypePath SPECIFY_ME\n"
        "    CellLibraryFile my-cell-library-file\n"
        f"    BioName {bioname}\n"
        "    Atlas /gpfs/bbp.cscs.ch/project/proj66/entities/dev/atlas/O1-152\n"
        "}"
    ), res


def test_build_circuit_config__CircuitConfig_base():

    bioname = TEST_PROJ_TINY
    ctx = _get_context(bioname)

    res = ctx.build_circuit_config(
        nrn_path="my-nrn-path",
        cell_library_file="circuit.mvd3",
        morphology_type=None,
    )

    cwd = Path(".").resolve()

    assert res == (
        "Run Default\n"
        "{\n"
        f"    CircuitPath {cwd}\n"
        f"    nrnPath {cwd}/my-nrn-path\n"
        "    MorphologyPath /gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16\n"
        "    METypePath /gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/hoc\n"
        "    MEComboInfoFile /gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0/mecombo_emodel.tsv\n"
        "    CellLibraryFile circuit.mvd3\n"
        f"    BioName {bioname}\n"
        "    Atlas /gpfs/bbp.cscs.ch/project/proj66/entities/dev/atlas/O1-152\n"
        "}"
    )
