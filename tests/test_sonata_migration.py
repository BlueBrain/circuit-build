from click.testing import CliRunner
from numpy.testing import assert_almost_equal, assert_equal
from pandas.testing import assert_frame_equal
from utils import SNAKEMAKE_ARGS, cwd
from voxcell import CellCollection

from circuit_build.cli import run


def assert_equal_cells(c0, c1):
    assert_equal(c0.positions, c1.positions)
    if c0.orientations is None:
        assert c1.orientations is None
    else:
        assert_almost_equal(c0.orientations, c1.orientations)
    assert_frame_equal(
        c0.properties.sort_index(axis=1),
        c1.properties.sort_index(axis=1),
        check_names=True,
    )


def test_default_rule(tmp_path):
    with cwd(tmp_path):
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ["assign_emodels"], catch_exceptions=False)
        assert result.exit_code == 0

        assert tmp_path.joinpath("circuit.mvd3").stat().st_size > 100
        mvd3_cells = CellCollection.load_mvd3(tmp_path / "circuit.mvd3")
        assert tmp_path.joinpath("circuit.h5").stat().st_size > 100
        sonata_cells = CellCollection.load_sonata(tmp_path / "circuit.h5")

    assert_equal_cells(mvd3_cells, sonata_cells)


def test_node_sets(tmp_path):
    with cwd(tmp_path):
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ["node_sets"], catch_exceptions=False)
        assert result.exit_code == 0
        node_sets = tmp_path.joinpath("sonata/node_sets.json").read_text()
        assert len(node_sets) > 100
