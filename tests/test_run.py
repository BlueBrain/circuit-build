import shutil
import subprocess
import tempfile
from functools import partial
from pathlib import Path
from subprocess import CalledProcessError

import yaml
from unittest.mock import patch
from nose.tools import assert_raises

from click.testing import CliRunner
from circuit_build.cli import run

from utils import tmp_cwd, TEST_DIR, TEST_DATA_DIR, SNAKEMAKE_ARGS


def test_functional_all():
    with tmp_cwd() as tmp_dir:
        runner = CliRunner()
        result = runner.invoke(run, SNAKEMAKE_ARGS + ['functional_all'], catch_exceptions=False)
        assert result.exit_code == 0
        tmp_dir = Path(tmp_dir)
        assert tmp_dir.joinpath('CircuitConfig').stat().st_size > 100
        assert tmp_dir.joinpath('CircuitConfig_nrn').stat().st_size > 100
        assert tmp_dir.joinpath('circuit.mvd3').stat().st_size > 100
        assert tmp_dir.joinpath('sonata/networks/nodes/All/nodes.h5').stat().st_size > 100
        assert tmp_dir.joinpath('connectome/functional/edges.sonata').stat().st_size > 100
        assert tmp_dir.joinpath('start.target').stat().st_size > 100


def test_no_emodel():
    def _remove_emodel(manifest_file):
        with manifest_file.open() as f:
            manifest = yaml.safe_load(f)
            del manifest['common']['emodel_release']
        with manifest_file.open('w') as f:
            yaml.dump(manifest, f)

    with tmp_cwd() as tmp_dir, tempfile.TemporaryDirectory(dir=TEST_DIR) as data_copy_dir:
        data_copy_dir = Path(data_copy_dir) / TEST_DATA_DIR.name
        shutil.copytree(TEST_DATA_DIR, data_copy_dir)
        _remove_emodel(data_copy_dir / 'MANIFEST.yaml')
        args = ['--bioname', str(data_copy_dir), '-u', str(data_copy_dir / 'cluster.yaml')]

        runner = CliRunner()
        result = runner.invoke(
            run, args + ['assign_emodels', 'circuitconfig_nrn'], catch_exceptions=False)
        assert result.exit_code == 0
        tmp_dir = Path(tmp_dir)
        assert tmp_dir.joinpath('CircuitConfig_nrn').stat().st_size > 100
        assert tmp_dir.joinpath('circuit.h5').stat().st_size > 100


@patch('subprocess.run', partial(subprocess.run, capture_output=True))
def test_custom_module():
    with tmp_cwd():
        args = SNAKEMAKE_ARGS + ['-m', 'jinja2:invalid_module1:invalid_module_path']

        runner = CliRunner()
        with assert_raises(CalledProcessError) as err:
            runner.invoke(run, args + ['circuitconfig_nrn'], catch_exceptions=False)
        assert "Unable to locate a modulefile for 'invalid_module1'" in \
               err.exception.stderr.decode('utf-8')
