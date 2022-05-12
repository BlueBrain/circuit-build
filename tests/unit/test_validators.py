import warnings

import pytest
from utils import UNIT_TESTS_DIR

from circuit_build import validators as test_module
from circuit_build.constants import ENV_CONFIG
from circuit_build.utils import load_yaml
from circuit_build.validators import ValidationError


def test_validate_default_environments():
    config = {"env_config": ENV_CONFIG}
    schema_file = "environments.yaml"
    test_module.validate_config(config, schema_file)


@pytest.mark.parametrize(
    "schema_file, config_file",
    [
        ("MANIFEST.yaml", "proj66-tiny/MANIFEST.yaml"),
        ("MANIFEST.yaml", "proj66-tiny-synth/MANIFEST.yaml"),
        ("cluster.yaml", "proj66-tiny/cluster.yaml"),
        ("cluster.yaml", "proj66-tiny-synth/cluster.yaml"),
        ("cluster.yaml", "data/config/valid/cluster_empty.yaml"),
        ("cluster.yaml", "data/config/valid/cluster_all.yaml"),
        ("environments.yaml", "data/config/valid/environments_empty.yaml"),
        ("environments.yaml", "data/config/valid/environments_all.yaml"),
        ("environments.yaml", "data/config/valid/environments_apptainer.yaml"),
        ("environments.yaml", "data/config/valid/environments_module.yaml"),
        ("environments.yaml", "data/config/valid/environments_venv.yaml"),
    ],
)
def test_validate_config_success(schema_file, config_file):
    config = load_yaml(UNIT_TESTS_DIR / config_file)
    test_module.validate_config(config, schema_file)


@pytest.mark.parametrize(
    "schema_file, config_file",
    [
        ("MANIFEST.yaml", "data/config/invalid/MANIFEST_invalid_name.yaml"),
        ("cluster.yaml", "data/config/invalid/cluster_invalid_name.yaml"),
        ("environments.yaml", "data/config/invalid/environments_invalid_name.yaml"),
    ],
)
def test_validate_config_failure(schema_file, config_file):
    config = load_yaml(UNIT_TESTS_DIR / config_file)
    with pytest.raises(ValidationError):
        test_module.validate_config(config, schema_file)


@pytest.mark.parametrize("allowed_part", ["ncx", "neocortex", "hippocampus", "thalamus", "mousify"])
@pytest.mark.parametrize("allowed_type", ["neurons", "astrocytes", "projections"])
def test_validate_node_population_name(allowed_part, allowed_type):
    # ensure that no warnings are emitted
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        name = f"{allowed_part}_{allowed_type}"
        test_module.validate_node_population_name(name)


@pytest.mark.parametrize(
    "allowed_connection", ["electrical", "chemical_synapse", "synapse_astrocyte", "endfoot"]
)
def test_validate_edge_population_name(allowed_connection):
    # ensure that no warnings are emitted
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        name = f"neocortex_neurons__{allowed_connection}"
        test_module.validate_edge_population_name(name)
        name = f"neocortex_neurons__hippocampus_projections__{allowed_connection}"
        test_module.validate_edge_population_name(name)


@pytest.mark.parametrize("name", ["All", "neocortex"])
def test_validate_node_population_name_failure(name):
    match = '"node_population_name" in MANIFEST.yaml must exist and should fit the pattern'
    with pytest.warns(UserWarning, match=match):
        test_module.validate_node_population_name(name)


@pytest.mark.parametrize("name", ["All", "neocortex_neurons__chemical"])
def test_validate_edge_population_name_failure(name):
    match = '"edge_population_name" in MANIFEST.yaml must exist and should fit the pattern'
    with pytest.warns(UserWarning, match=match):
        test_module.validate_edge_population_name(name)
