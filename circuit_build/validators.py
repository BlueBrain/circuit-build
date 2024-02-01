"""Validators."""

import logging
import os
import warnings
from pathlib import Path

import jsonschema

from circuit_build.utils import read_schema

logger = logging.getLogger(__name__)


def _format_error(error):
    """Return a formatted error message.

    Args:
        error (jsonschema.exceptions.ValidationError): validation error from jsonschema.

    Examples:
        Failed validating root: Additional properties are not allowed ('x' was unexpected)
        Failed validating root.assign_emodels.seed: 'a' is not of type 'integer'
    """
    path = ".".join(str(elem) for elem in ["root"] + list(error.absolute_path))
    return f"Failed validating {path}: {error.message}"


class ValidationError(Exception):
    """Validation error."""


def validate_config(config, schema_name):
    """Raise an exception if the configuration is not valid.

    Args:
        config (dict): configuration to be validated.
        schema_name (str): filename of the configuration schema, searched in the schemas directory.

    Raises:
        ValidationError in case of validation error.
    """
    schema = read_schema(schema_name)
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    validator = cls(schema)
    errors = list(validator.iter_errors(config))
    if errors:
        msg = "\n".join(f"{n}: {_format_error(e)}" for n, e in enumerate(errors, 1))
        logger.error("Invalid configuration [%s]\n%s", schema_name, msg)
        raise ValidationError(f"Invalid configuration [{schema_name}]")


def validate_node_population_name(name):
    """Validate the name of the node population."""
    doc_url = "https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/bioname.html#manifest-yaml"
    allowed_parts = {"ncx", "neocortex", "hippocampus", "thalamus", "mousify"}
    allowed_types = {"neurons", "astrocytes", "projections"}
    msg = (
        '"node_population_name" in MANIFEST.yaml must exist and should fit the pattern: '
        f'"<part>_<type>", see {doc_url} for details'
    )

    if name is None:
        raise ValidationError(msg)
    name_parts = name.split("_")
    if len(name_parts) != 2:
        warnings.warn(msg)
    elif name_parts[0] not in allowed_parts or name_parts[1] not in allowed_types:
        warnings.warn(msg)

    return name


def validate_edge_population_name(name):
    """Validate the name of the edge population."""
    doc_url = "https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/bioname.html#manifest-yaml"
    allowed_connection = {"electrical", "chemical_synapse", "synapse_astrocyte", "endfoot"}
    msg = (
        '"edge_population_name" in MANIFEST.yaml must exist and should fit the pattern: '
        f'"<source_population>__<target_population>__<connection>", see {doc_url} for details'
    )

    if name is None:
        raise ValidationError(msg)
    name_parts = name.split("__")
    if (len(name_parts) not in [2, 3]) or (name_parts[-1] not in allowed_connection):
        warnings.warn(msg)

    return name


def validate_morphology_release(directory):
    """Validate the directory of morphology release.

    Notes:
        Checks that are performed:
            - sub-directories ascii/ and h5v1/ exist.
            - sub-directories are not empty.
            - sub-directories have matching file names.

    """
    doc_url = "https://bbpteam.epfl.ch/documentation/projects/circuit-build/latest/bioname.html#manifest-yaml"

    subdir_to_extension = {"ascii": "asc", "h5v1": "h5"}

    def get_morphology_names(path):
        suffix = f".{subdir_to_extension[path.stem]}"
        filenames = {f.removesuffix(suffix) for f in os.listdir(path) if f.endswith(suffix)}

        if not filenames:
            raise ValidationError(
                f"Morphology release at {directory} has no morphologies with extension {suffix} "
                f"in the {path.stem}/ sub-directory."
            )
        return filenames

    directory = Path(directory)
    subdir_paths = [Path(directory, name) for name in subdir_to_extension]

    missing_subdirs = [path.stem for path in subdir_paths if not path.is_dir()]
    if missing_subdirs:
        missing = ", ".join(f"{name}/" for name in missing_subdirs)
        raise ValidationError(
            f"Morphology release at {directory} is missing: {missing}\n"
            f"See {doc_url} for more details on the mandatory sub-directories."
        )

    target_filenames = get_morphology_names(subdir_paths[0])
    for subdir in subdir_paths[1:]:
        if target_filenames != get_morphology_names(subdir):
            raise ValidationError(
                f"Morphology release at {directory} has mismatching files "
                f"between {subdir_paths[0].stem}/ and {subdir.stem}/."
            )

    return directory
