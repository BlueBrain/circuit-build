import json
import shutil
import subprocess
import tempfile
from functools import partial
from pathlib import Path
from subprocess import CalledProcessError

import h5py
from unittest.mock import patch
from nose.tools import assert_raises

from click.testing import CliRunner
from circuit_build.cli import run

from utils import tmp_cwd, edit_yaml, TEST_DIR, TEST_DATA_DIR, SNAKEMAKE_ARGS, SNAKE_FILE


def test_functional_all():
    # don't test for a custom node population in a separate test because it is too long to execute
    test_name = 'custom_population_name'
    with tmp_cwd() as tmp_dir, tempfile.TemporaryDirectory(dir=TEST_DIR) as data_copy_dir:
        data_copy_dir = Path(data_copy_dir) / TEST_DATA_DIR.name
        shutil.copytree(TEST_DATA_DIR, data_copy_dir)
        with edit_yaml(data_copy_dir / 'MANIFEST.yaml') as manifest:
            manifest['common']['node_population_name'] = test_name

        args = ['--bioname', str(data_copy_dir), '-u', str(data_copy_dir / 'cluster.yaml')]
        runner = CliRunner()
        result = runner.invoke(run, args + ['functional_all', 'functional_sonata', 'functional_nrn'], catch_exceptions=False)
        assert result.exit_code == 0
        tmp_dir = Path(tmp_dir)

        assert tmp_dir.joinpath('CircuitConfig').stat().st_size > 100
        assert tmp_dir.joinpath('CircuitConfig_nrn').stat().st_size > 100
        assert tmp_dir.joinpath('circuit.mvd3').stat().st_size > 100
        assert tmp_dir.joinpath('sonata/node_sets.json').stat().st_size > 100
        assert tmp_dir.joinpath('sonata/circuit_config.json').stat().st_size > 100
        assert tmp_dir.joinpath('start.target').stat().st_size > 100
        assert f'CellLibraryFile circuit.mvd3' in (tmp_dir / 'CircuitConfig_nrn').open().read()

        nodes_file = (tmp_dir / f'sonata/networks/nodes/{test_name}/nodes.h5').resolve()
        assert f'CellLibraryFile {nodes_file}' in (tmp_dir / 'CircuitConfig').open().read()
        assert nodes_file.stat().st_size > 100
        with h5py.File(nodes_file, 'r') as h5f:
            assert f'/nodes/{test_name}' in h5f
        with h5py.File(tmp_dir / 'sonata/networks/edges/functional/All/edges.h5', 'r') as h5f:
            assert test_name == h5f['/edges/default/source_node_id'].attrs['node_population']
            assert test_name == h5f['/edges/default/target_node_id'].attrs['node_population']
        with tmp_dir.joinpath('sonata/circuit_config.json').open('r') as f:
            config = json.load(f)
            assert config['networks']['nodes'][0]['nodes_file'] \
                == f'$NETWORK_NODES_DIR/{test_name}/nodes.h5'


def test_no_emodel():
    with tmp_cwd() as tmp_dir, tempfile.TemporaryDirectory(dir=TEST_DIR) as data_copy_dir:
        data_copy_dir = Path(data_copy_dir) / TEST_DATA_DIR.name
        shutil.copytree(TEST_DATA_DIR, data_copy_dir)
        with edit_yaml(data_copy_dir / 'MANIFEST.yaml') as manifest:
            del manifest['common']['emodel_release']
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


def test_snakemake_circuit_config():
    """This test verifies that building can happen via `snakemake`,
    and `CircuitConfig.j2` is accessible in this case."""
    with tmp_cwd() as tmp_dir:
        args = ['--jobs', '8', '-p', '--config', f'bioname={TEST_DATA_DIR}', '-u',
                str(TEST_DATA_DIR / 'cluster.yaml')]
        cmd = ['snakemake', '--snakefile', SNAKE_FILE] + args + ['CircuitConfig_base']
        result = subprocess.run(cmd, check=True)

        assert result.returncode == 0
        tmp_dir = Path(tmp_dir)
        assert tmp_dir.joinpath('CircuitConfig_base').stat().st_size > 100
        assert f'CellLibraryFile circuit.mvd3' in (tmp_dir / 'CircuitConfig_base').open().read()
