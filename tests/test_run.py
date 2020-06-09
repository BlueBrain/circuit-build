import subprocess
import tempfile
from pathlib import Path

from utils import TEST_DIR, SNAKEMAKE_ARGS


def test_functional_all():
    with tempfile.TemporaryDirectory(dir=TEST_DIR) as tmpdirname:
        cmd = ['snakemake'] + SNAKEMAKE_ARGS + ['functional_all']
        result = subprocess.run(cmd, cwd=tmpdirname, check=True, timeout=60 * 60)
        assert result.returncode == 0
        tmpdirname = Path(tmpdirname)
        assert tmpdirname.joinpath('CircuitConfig').stat().st_size > 100
        assert tmpdirname.joinpath('CircuitConfig_nrn').stat().st_size > 100
        assert tmpdirname.joinpath('circuit.mvd3').stat().st_size > 100
        assert tmpdirname.joinpath('sonata/networks/nodes/All/nodes.h5').stat().st_size > 100
        assert tmpdirname.joinpath('connectome/functional/edges.sonata').stat().st_size > 100
        assert tmpdirname.joinpath('start.target').stat().st_size > 100
