import re
import warnings

import pytest
from utils import TEST_PROJ_SYNTH, TEST_PROJ_TINY, UNIT_TESTS_DATA

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
        ("MANIFEST.yaml", TEST_PROJ_TINY / "MANIFEST.yaml"),
        ("MANIFEST.yaml", TEST_PROJ_SYNTH / "MANIFEST.yaml"),
        ("cluster.yaml", TEST_PROJ_TINY / "cluster.yaml"),
        ("cluster.yaml", TEST_PROJ_SYNTH / "cluster.yaml"),
        ("cluster.yaml", UNIT_TESTS_DATA / "config/valid/cluster_empty.yaml"),
        ("cluster.yaml", UNIT_TESTS_DATA / "config/valid/cluster_all.yaml"),
        ("environments.yaml", UNIT_TESTS_DATA / "config/valid/environments_empty.yaml"),
        ("environments.yaml", UNIT_TESTS_DATA / "config/valid/environments_all.yaml"),
        ("environments.yaml", UNIT_TESTS_DATA / "config/valid/environments_apptainer.yaml"),
        ("environments.yaml", UNIT_TESTS_DATA / "config/valid/environments_module.yaml"),
        ("environments.yaml", UNIT_TESTS_DATA / "config/valid/environments_venv.yaml"),
    ],
)
def test_validate_config_success(schema_file, config_file):
    config = load_yaml(config_file)
    test_module.validate_config(config, schema_file)


@pytest.mark.parametrize(
    "schema_file, config_file",
    [
        ("MANIFEST.yaml", UNIT_TESTS_DATA / "config/invalid/MANIFEST_invalid_name.yaml"),
        ("cluster.yaml", UNIT_TESTS_DATA / "config/invalid/cluster_invalid_name.yaml"),
        ("environments.yaml", UNIT_TESTS_DATA / "config/invalid/environments_invalid_name.yaml"),
    ],
)
def test_validate_config_failure(schema_file, config_file):
    config = load_yaml(config_file)
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


@pytest.mark.parametrize("name", ["All", "neocortex", "ncx_nonexistent", "nonexistent_neurons"])
def test_validate_node_population_name_warns(name):
    match = '"node_population_name" in MANIFEST.yaml must exist and should fit the pattern'
    with pytest.warns(UserWarning, match=match):
        test_module.validate_node_population_name(name)


@pytest.mark.parametrize("name", ["All", "neocortex_neurons__chemical"])
def test_validate_edge_population_name_warns(name):
    match = '"edge_population_name" in MANIFEST.yaml must exist and should fit the pattern'
    with pytest.warns(UserWarning, match=match):
        test_module.validate_edge_population_name(name)


def test_validate_node_population_name_raises():
    name = None
    match = '"node_population_name" in MANIFEST.yaml must exist and should fit the pattern'
    with pytest.raises(ValidationError, match=match):
        test_module.validate_node_population_name(name)


def test_validate_edge_population_name_raises():
    name = None
    match = '"edge_population_name" in MANIFEST.yaml must exist and should fit the pattern'
    with pytest.raises(ValidationError, match=match):
        test_module.validate_edge_population_name(name)


def test_validate_morphology_release(tmp_path):
    path = tmp_path / "morphology-release"
    path.mkdir()

    match = f"Morphology release at {path} is missing: ascii/, h5v1/"
    with pytest.raises(ValidationError, match=match):
        test_module.validate_morphology_release(path)

    ascii_subdir = path / "ascii"
    ascii_subdir.mkdir()

    match = f"Morphology release at {path} is missing: h5v1/"
    with pytest.raises(ValidationError, match=match):
        test_module.validate_morphology_release(path)

    h5v1_subdir = path / "h5v1"
    h5v1_subdir.mkdir()

    for filename in ["m1.h5", "m2.h5"]:
        p = h5v1_subdir / filename
        p.touch()

    for filename in ["m1.swc", "m2.swc"]:
        p = ascii_subdir / filename
        p.touch()

    match = f"Morphology release at {path} has no morphologies with extension .asc in the ascii/ sub-directory."
    with pytest.raises(ValidationError, match=match):
        test_module.validate_morphology_release(path)

    for filename in ["m2.asc"]:
        p = ascii_subdir / filename
        p.touch()

    match = f"Morphology release at {path} has mismatching files between ascii/ and h5v1/."
    with pytest.raises(ValidationError, match=match):
        test_module.validate_morphology_release(path)

    p = ascii_subdir / "m1.asc"
    p.touch()

    assert test_module.validate_morphology_release(path) == path
