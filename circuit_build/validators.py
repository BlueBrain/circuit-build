"""Validators."""
import logging
import warnings

import jsonschema

from circuit_build.utils import read_schema

logger = logging.getLogger(__name__)


def validate_config(config, schema_name):
    """Raise an exception if the configuration is not valid."""
    schema = read_schema(schema_name)
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    validator = cls(schema)
    errors = list(validator.iter_errors(config))
    if errors:
        # Log an error message like the following:
        #  Invalid configuration: MANIFEST.yaml
        #  1: Failed validating root: Additional properties are not allowed ('x' was unexpected)
        #  2: Failed validating root.assign_emodels.seed: 'a' is not of type 'integer'
        msg = "\n".join(
            "{n}: Failed validating {path}: {message}".format(
                n=n,
                path=".".join(str(elem) for elem in ["root"] + list(e.absolute_path)),
                message=e.message,
            )
            for n, e in enumerate(errors, 1)
        )
        logger.error("Invalid configuration: %s\n%s", schema_name, msg)
        raise Exception("Validation error")


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
        raise ValueError(msg)
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
        raise ValueError(msg)
    name_parts = name.split("__")
    if (len(name_parts) not in [2, 3]) or (name_parts[-1] not in allowed_connection):
        warnings.warn(msg)

    return name
