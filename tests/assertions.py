import bluepysnap
import numpy as np


def assert_node_population_morphologies_accessible(circuit, population_name, extensions):
    """
    Args:
        circuit (bluepysnap.Circuit): Circuit to check.
        population_name (str): Name of node population.
        extensions (List[str]): List of file extensions that are expected, ["swc", "asc", "h5"].
    """
    population = circuit.nodes[population_name]

    cell_id = population.size // 2

    def is_invalid_extension(extension):
        try:
            population.morph.get(cell_id, extension=extension)
        except bluepysnap.BluepySnapError:
            return True
        return False

    invalid_extensions = list(filter(is_invalid_extension, extensions))

    if invalid_extensions:
        raise AssertionError(f"Inaccessible morphology extensions: {', '.join(invalid_extensions)}")
