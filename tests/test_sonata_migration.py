import subprocess
import tempfile
from pathlib import Path

from numpy.testing import assert_equal, assert_almost_equal
from pandas.testing import assert_frame_equal

from voxcell import CellCollection

from utils import TEST_DIR, SNAKEMAKE_ARGS


def assert_equal_cells(c0, c1):
    assert_equal(c0.positions, c1.positions)
    if c0.orientations is None:
        assert c1.orientations is None
    else:
        assert_almost_equal(c0.orientations, c1.orientations)
    assert_frame_equal(
        c0.properties.sort_index(axis=1),
        c1.properties.sort_index(axis=1),
        check_names=True
    )


def test_default_rule():
    with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmpdirname:
        cmd = ['snakemake'] + SNAKEMAKE_ARGS
        result = subprocess.run(cmd, cwd=tmpdirname, check=True, timeout=60 * 60)
        assert result.returncode == 0
        tmpdirname = Path(tmpdirname)

        assert tmpdirname.joinpath('circuit.mvd3').stat().st_size > 100
        mvd3_cells = CellCollection.load_mvd3(tmpdirname / 'circuit.mvd3')
        assert tmpdirname.joinpath('circuit.h5').stat().st_size > 100
        sonata_cells = CellCollection.load_sonata(tmpdirname / 'circuit.h5')
        assert tmpdirname.joinpath('start.target').stat().st_size > 100

    assert_equal_cells(mvd3_cells, sonata_cells)


def test_node_sets():
    with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmpdirname:
        cmd = ['snakemake'] + SNAKEMAKE_ARGS + ['node_sets']
        result = subprocess.run(cmd, cwd=tmpdirname, check=True, timeout=60 * 60)
        assert result.returncode == 0
        node_sets = Path(tmpdirname).joinpath('sonata/node_sets.json').read_text()
        assert len(node_sets) > 100
