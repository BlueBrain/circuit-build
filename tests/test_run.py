from pathlib import Path

from click.testing import CliRunner
from circuit_build.cli import run
from utils import tmp_cwd, SNAKEMAKE_ARGS


def test_functional_all():
    with tmp_cwd() as tmpdirname:
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ['functional_all'], catch_exceptions=False)
        assert result.exit_code == 0
        tmpdirname = Path(tmpdirname)
        assert tmpdirname.joinpath('CircuitConfig').stat().st_size > 100
        assert tmpdirname.joinpath('CircuitConfig_nrn').stat().st_size > 100
        assert tmpdirname.joinpath('circuit.mvd3').stat().st_size > 100
        assert tmpdirname.joinpath('sonata/networks/nodes/All/nodes.h5').stat().st_size > 100
        assert tmpdirname.joinpath('connectome/functional/edges.sonata').stat().st_size > 100
        assert tmpdirname.joinpath('start.target').stat().st_size > 100
