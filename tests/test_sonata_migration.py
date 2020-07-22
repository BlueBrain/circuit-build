from pathlib import Path

from voxcell import CellCollection

from click.testing import CliRunner
from circuit_build.cli import run
from numpy.testing import assert_equal, assert_almost_equal
from pandas.testing import assert_frame_equal

from utils import tmp_cwd, SNAKEMAKE_ARGS


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
    with tmp_cwd() as tmpdirname:
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ['assign_emodels'], catch_exceptions=False)
        assert result.exit_code == 0
        tmpdirname = Path(tmpdirname)

        assert tmpdirname.joinpath('circuit.mvd3').stat().st_size > 100
        mvd3_cells = CellCollection.load_mvd3(tmpdirname / 'circuit.mvd3')
        assert tmpdirname.joinpath('circuit.h5').stat().st_size > 100
        sonata_cells = CellCollection.load_sonata(tmpdirname / 'circuit.h5')

    assert_equal_cells(mvd3_cells, sonata_cells)


def test_node_sets():
    with tmp_cwd() as tmpdirname:
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ['node_sets'], catch_exceptions=False)
        assert result.exit_code == 0
        node_sets = Path(tmpdirname).joinpath('sonata/node_sets.json').read_text()
        assert len(node_sets) > 100
