"""Utilities specific to the NGV building."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from bluepysnap.circuit import CircuitConfig

L = logging.getLogger(__name__)


class BaseConfigKeys:
    """NGV Base config keys."""

    CONFIG = "config"
    NODES_FILE = "nodes_file"
    EDGES_FILE = "edges_file"
    NODE_POPULATION_NAME = "node_population_name"
    EDGE_POPULATION_NAME = "edge_population_name"
    MORPHOLOGIES_DIR = "morphologies_dir"
    HOC_DIR = "biophysical_neuron_models_dir"
    SPATIAL_SYNAPSE_INDEX_DIR = "spatial_synapse_index_dir"
    SPATIAL_SEGMENT_INDEX_DIR = "spatial_segment_index_dir"


_REQUIRED_CONFIG_ENTRIES = {
    BaseConfigKeys.CONFIG,
    BaseConfigKeys.NODE_POPULATION_NAME,
    BaseConfigKeys.EDGE_POPULATION_NAME,
}


@dataclass
class _BaseCircuitComponents:
    """Data structure for ngv/common/base_circuit entries."""

    nodes_file: Path
    edges_file: Path
    hoc_dir: Path
    morphologies_dir: Path
    synapse_index_dir: Path | None
    segment_index_dir: Path | None


def stage_ngv_base_circuit(base_circuit_config, context):
    """Stage base circuit for ngv standalone."""
    comps = _get_components(base_circuit_config, parent_dir=context.paths.bioname_dir)

    _stage_path(source=comps.nodes_file, target=context.nodes_neurons_file)
    _stage_path(source=comps.hoc_dir, target=context.EMODEL_RELEASE_HOC)
    _stage_path(source=comps.morphologies_dir, target=context.SYNTHESIZE_MORPH_DIR)
    _stage_path(source=comps.edges_file, target=context.edges_neurons_neurons_file("functional"))

    if comps.synapse_index_dir:
        _stage_path(source=comps.synapse_index_dir, target=context.edges_spatial_index_dir)

    if comps.segment_index_dir:
        _stage_path(source=comps.segment_index_dir, target=context.nodes_spatial_index_dir)


def _get_base_populations(base_config, parent_dir=None):
    try:
        node_population_name = base_config[BaseConfigKeys.NODE_POPULATION_NAME]
        edge_population_name = base_config[BaseConfigKeys.EDGE_POPULATION_NAME]
        config = (
            Path(parent_dir).expanduser().resolve() / base_config[BaseConfigKeys.CONFIG]
            if parent_dir
            else base_config[BaseConfigKeys.CONFIG]
        )
    except KeyError as e:
        raise RuntimeError(
            f"Minimum ngv base circuit entries:\n"
            f"Required : {sorted(_REQUIRED_CONFIG_ENTRIES)}\n"
            f"Got      : {sorted(base_config.keys())}"
        ) from e

    config = CircuitConfig.from_config(Path(config).resolve())

    try:
        node_pop_dict = config.node_populations[node_population_name]
    except KeyError as e:
        raise RuntimeError(
            f"Node population name '{node_population_name}' not in node population names.\n"
            f"Existing node population names: {sorted(config.node_populations)}"
        ) from e

    try:
        edge_pop_dict = config.edge_populations[edge_population_name]
    except KeyError as e:
        raise RuntimeError(
            f"Edge population name '{edge_population_name}' not in edge population names.\n"
            f"Existing edge population names: {sorted(config.edge_populations)}"
        ) from e

    return node_pop_dict, edge_pop_dict


def _get_components(base_config, parent_dir=None):
    """Get base circuit components from the manifest's ngv/common/base_circuit section."""
    node_pop_dict, edge_pop_dict = _get_base_populations(base_config, parent_dir=parent_dir)

    nodes_file = _get_existing_path(
        dct=node_pop_dict,
        key=BaseConfigKeys.NODES_FILE,
        raise_if_no_entry=True,
    )

    hoc_dir = _get_existing_path(
        dct=node_pop_dict,
        key=BaseConfigKeys.HOC_DIR,
        raise_if_no_entry=True,
    )

    edges_file = _get_existing_path(
        dct=edge_pop_dict,
        key=BaseConfigKeys.EDGES_FILE,
        raise_if_no_entry=True,
    )

    # prioritize alt morphs over components if present
    if morph_dict := node_pop_dict.get("alternate_morphologies", None):
        morphologies_dir = _get_existing_path(
            dct=morph_dict,
            key="h5v1",
            raise_if_no_entry=True,
        )
    else:
        morphologies_dir = _get_existing_path(
            dct=node_pop_dict,
            key=BaseConfigKeys.MORPHOLOGIES_DIR,
            raise_if_no_entry=True,
        )

    synapse_index_dir = _get_existing_path(
        dct=edge_pop_dict,
        key=BaseConfigKeys.SPATIAL_SYNAPSE_INDEX_DIR,
        raise_if_no_entry=False,
    )

    segment_index_dir = _get_existing_path(
        dct=node_pop_dict,
        key=BaseConfigKeys.SPATIAL_SEGMENT_INDEX_DIR,
        raise_if_no_entry=False,
    )

    return _BaseCircuitComponents(
        nodes_file=nodes_file,
        hoc_dir=hoc_dir,
        edges_file=edges_file,
        morphologies_dir=morphologies_dir,
        synapse_index_dir=synapse_index_dir,
        segment_index_dir=segment_index_dir,
    )


def _get_existing_path(dct: dict, key: str, raise_if_no_entry: bool = False) -> Path | None:

    def _ensure_existing_path(path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path {path} was not found.")
        return path

    if value := dct.get(key, None):
        return _ensure_existing_path(value)

    if raise_if_no_entry:
        raise RuntimeError(f"Key '{key}' not in population properties: {dct}")

    return None


def _stage_path(source, target):
    source = Path(source)
    target = Path(target)

    if not source.exists():
        raise RuntimeError(f"Source path {source} does not exist.")

    if target.exists():
        if target.is_symlink():
            L.warning("Target %s is a symlink and will be replaced.", target)
            target.unlink(missing_ok=True)
        else:
            # Given that this function creates symbolic links, it is safer to treat
            # existing file/dir targets as unplanned mistakes instead of deleting them
            raise RuntimeError(f"Target {target} exists and is not a symbolic link.")

    if not target.parent.exists():
        target.parent.mkdir(parents=True)
        L.debug("Parent dir of %s doesn't exist. Created.", target.parent)

    os.symlink(source, target)
    L.debug("Link %s -> %s", source, target)
