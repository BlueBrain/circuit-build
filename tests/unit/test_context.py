from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from circuit_build import context as test_module
from circuit_build.utils import load_yaml

from utils import TEST_PROJ_TINY


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
    assert ctx.BIONAME == str(bioname)
    assert ctx.CIRCUIT_DIR == "."
    assert ctx.BUILDER_RECIPE == str(bioname / "builderRecipeAllPathways.xml")
    assert ctx.MORPHDB == str(bioname / "extNeuronDB.dat")
    assert ctx.SYNTHESIZE_PROTOCOL_CONFIG == str(bioname / "protocol_config.yaml")
    assert ctx.SYNTHESIZE is False
    assert ctx.SYNTHESIZE_MORPH_DIR == str(cwd / "morphologies")
    assert ctx.SYNTHESIZE_MORPHDB == str(bioname / "neurondb-axon.dat")
    assert ctx.PARTITION == []
    assert ctx.ATLAS == "/gpfs/bbp.cscs.ch/project/proj66/entities/dev/atlas/O1-152"
    assert ctx.ATLAS_CACHE_DIR == ".atlas"
    assert ctx.NODE_POPULATION_NAME == "neocortex_neurons"
    assert ctx.EDGE_POPULATION_NAME == "neocortex_neurons__chemical_synapse"
    assert ctx.MORPH_RELEASE == "/gpfs/bbp.cscs.ch/project/proj66/entities/morphologies/2018.02.16"
    assert ctx.EMODEL_RELEASE == "/gpfs/bbp.cscs.ch/project/proj66/entities/emodels/2018.02.26.dev0"
    assert ctx.SYNTHESIZE_EMODEL_RELEASE == ""
    assert ctx.EMODEL_RELEASE_MECOMBO == expected_emodel_release_mecombo
    assert ctx.EMODEL_RELEASE_HOC == expected_emodel_release_hoc
    assert ctx.LOGS_DIR == "logs"
    assert ctx.NODESETS_FILE == "node_sets.json"
    assert ctx.TOUCHES_DIR == "connectome/touches"
    assert ctx.TOUCHES_GLIA_DIR == "connectome/astrocytes/touches"
    assert ctx.CONNECTOME_FUNCTIONAL_DIR == "connectome/functional"
    assert ctx.CONNECTOME_STRUCTURAL_DIR == "connectome/structural"
