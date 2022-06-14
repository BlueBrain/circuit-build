"""SONATA config building tool."""
import inspect
import json
from pathlib import Path


def build_config(nodes, edges, node_sets_file=None):
    """Builds the SONATA config dictionary based on the list of nodes and edges provided.

    Args:

        nodes (List[dict]): A list of dictionaries corresponding to the node populations to be
            included in the config.
        edges (List[dict]): A list of dictionaries corresponding to the edge populations to be
            included in the config.
        node_sets_file (str): Node sets filename, e.g. node_sets.json

    Returns:
        The SONATA config dictionary.
    """
    node_types = {
        "biophysical": _nodes_biophysical,
        "virtual": _nodes_default,
        "point_neuron": _nodes_default,
        "astrocyte": _nodes_astrocyte,
        "vasculature": _nodes_vasculature,
    }
    edge_types = {
        "chemical": _edges_default,
        "electrical_synapse": _edges_default,
        "glialglial": _edges_default,
        "synapse_astrocyte": _edges_default,
        "endfoot": _edges_endfoot,
        "neuromodulatory": _edges_default,
        "TM_synapse": _edges_default,
    }

    cfg = {
        "version": 2,
        "manifest": {"$BASE_DIR": "."},
    }

    if node_sets_file is not None:
        cfg["node_sets_file"] = node_sets_file

    cfg["networks"] = {
        "nodes": [_render_template(node_dict, node_types) for node_dict in nodes],
        "edges": [_render_template(edge_dict, edge_types) for edge_dict in edges],
    }
    return cfg


def _render_template(network_arguments, network_types):
    """Returns the dict population entry.

    Args:
        network_arguments (dict): Dictionary with the arguments of the template function from the
            population of type network_arguments['population_type'].
        network_types (dict): The network (nodes|edges) dictionary of the available population
            template functions.

    Returns:
        A dictionary for the population entry, which will be added to the sonata config.
    """
    population_type = network_arguments["population_type"]

    if population_type not in network_types:
        raise TypeError(
            f"Population type '{population_type}' is not available.\n"
            f"Please choose one of: {network_types.keys()}"
        )

    template_function = network_types[population_type]

    try:
        return template_function(**network_arguments)
    except TypeError as e:
        raise TypeError(
            f"Population type '{population_type}' has mismatching arguments.\n"
            f"Arguments: {set(network_arguments.keys())}\n"
            f"Expected : {set(inspect.signature(template_function).parameters.keys())}"
        ) from e


def _nodes_config_template(nodes_file, population_name, population_type, **kwargs):
    return {
        "nodes_file": nodes_file,
        "populations": {population_name: {"type": population_type, **kwargs}},
    }


def _nodes_default(nodes_file, population_name, population_type):
    return _nodes_config_template(
        nodes_file=nodes_file,
        population_name=population_name,
        population_type=population_type,
    )


def _nodes_biophysical(
    nodes_file,
    population_name,
    population_type,
    morphologies_dir,
    biophysical_neuron_models_dir,
):
    return _nodes_config_template(
        nodes_file=nodes_file,
        population_name=population_name,
        population_type=population_type,
        morphologies_dir=morphologies_dir,
        biophysical_neuron_models_dir=biophysical_neuron_models_dir,
    )


def _nodes_astrocyte(
    nodes_file, population_name, population_type, morphologies_dir, microdomains_file
):
    return _nodes_config_template(
        nodes_file=nodes_file,
        population_name=population_name,
        population_type=population_type,
        alternate_morphologies={"h5v1": morphologies_dir},
        microdomains_file=microdomains_file,
    )


def _nodes_vasculature(
    nodes_file, population_name, population_type, vasculature_file, vasculature_mesh
):
    return _nodes_config_template(
        nodes_file=nodes_file,
        population_name=population_name,
        population_type=population_type,
        vasculature_file=vasculature_file,
        vasculature_mesh=vasculature_mesh,
    )


def _edges_config_template(edges_file, population_name, population_type, **kwargs):
    return {
        "edges_file": edges_file,
        "populations": {population_name: {"type": population_type, **kwargs}},
    }


def _edges_default(edges_file, population_name, population_type):
    return _edges_config_template(
        edges_file=edges_file,
        population_name=population_name,
        population_type=population_type,
    )


def _edges_endfoot(edges_file, population_name, population_type, endfeet_meshes_file):
    return _edges_config_template(
        edges_file=edges_file,
        population_name=population_name,
        population_type=population_type,
        endfeet_meshes_file=endfeet_meshes_file,
    )


def resolve_config_paths(config, circuit_dir, base_dir):
    """Resolves absolute paths with respect to base_dir.

    Args:
        config (dict): The built config.
        circuit_dir (str|Path): The path to the circuit directory.
        base_dir (str|Path): The path to the directory of the config.

    Returns:
        A new config with the paths resolved.
    """
    circuit_dir = Path(circuit_dir)
    base_dir = Path(base_dir)

    assert base_dir.is_relative_to(circuit_dir), (
        f"Circuit dir is not a parent of base_dir.\n"
        f"Circuit dir: {str(circuit_dir)}\n"
        f"Base dir   : {str(base_dir)}"
    )

    resolved_config = {
        "version": config["version"],
        "manifest": config["manifest"],
    }

    assert config["manifest"]["$BASE_DIR"] == "."

    if "node_sets_file" in config:
        resolved_config["node_sets_file"] = _resolve_path(
            config["node_sets_file"], circuit_dir, base_dir
        )

    resolver = {
        "nodes_file": _resolve_path,
        "edges_file": _resolve_path,
        "populations": _resolve_populations,
    }
    resolved_config["networks"] = {
        network_type: [
            {key: resolver[key](value, circuit_dir, base_dir) for key, value in net_dict.items()}
            for net_dict in network_list
        ]
        for network_type, network_list in config["networks"].items()
    }
    return resolved_config


def _resolve_path(path, circuit_dir, base_dir):

    path = str(path)

    if path.startswith("$") or path == "":
        return path

    path = Path(path)

    if path.is_absolute():

        if path.is_relative_to(base_dir):
            return str(Path("$BASE_DIR", path.relative_to(base_dir)))

        if path.is_relative_to(circuit_dir):
            n_levels = len(base_dir.relative_to(circuit_dir).parts)
            return str(Path("$BASE_DIR", "../" * n_levels, path.relative_to(circuit_dir)))

    return str(Path("$BASE_DIR", path))


def _resolve_populations(populations_dict, circuit_dir, base_dir):
    def resolve_entry(key, value):

        if key.endswith(("file", "dir", "mesh")):
            return _resolve_path(value, circuit_dir, base_dir)

        if key == "alternate_morphologies":
            return {
                alt_key: _resolve_path(alt_path, circuit_dir, base_dir)
                for alt_key, alt_path in value.items()
            }

        return value

    return {
        pop_name: {key: resolve_entry(key, value) for key, value in pop_dict.items()}
        for pop_name, pop_dict in populations_dict.items()
    }


def write_config(output_file, circuit_dir, nodes, edges, node_sets_file=None):
    """Builds and writes a config to the output file.

    Args:
        output_file (str|Path|io.TextIOWrapper): Path to the output file or file object.
        circuit_dir (str|Path): The path to the circuit directory.
        base_dir (str|Path): The path to the directory of the config.
        nodes (List[dict]): A list of dictionaries corresponding to the node populations to be
            included in the config.
        edges (List[dict]): A list of dictionaries corresponding to the edge populations to be
            included in the config.
        node_sets_file (str|Path|None): Node sets filepath, e.g. /path/to/node_sets.json
    """
    if isinstance(output_file, (str, Path)):
        with open(output_file, mode="w", encoding="utf-8") as out:
            write_config(out, circuit_dir, nodes, edges, node_sets_file)
    else:
        config = build_config(nodes, edges, node_sets_file=node_sets_file)
        resolved_config = resolve_config_paths(
            config=config,
            circuit_dir=circuit_dir,
            base_dir=Path(output_file.name).resolve().parent,
        )
        json.dump(resolved_config, output_file, indent=2)