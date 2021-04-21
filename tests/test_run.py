import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from subprocess import CalledProcessError

import h5py

import pytest
from click.testing import CliRunner
from circuit_build.cli import run

from utils import (
    SNAKEFILE,
    SNAKEMAKE_ARGS,
    TEST_DATA_DIR,
    TEST_DIR,
    edit_yaml,
    tmp_cwd,
)


def test_functional_all():
    # don't test for a custom population names in a separate test because it will too long to execute
    node_population_name = 'node_population_name'
    edge_population_name = 'edge_population_name'
    with tmp_cwd() as tmp_dir, tempfile.TemporaryDirectory(dir=TEST_DIR) as data_copy_dir:
        data_copy_dir = Path(data_copy_dir) / TEST_DATA_DIR.name
        shutil.copytree(TEST_DATA_DIR, data_copy_dir)
        with edit_yaml(data_copy_dir / 'MANIFEST.yaml') as manifest:
            manifest['common']['node_population_name'] = node_population_name
            manifest['common']['edge_population_name'] = edge_population_name

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

        nodes_file = (tmp_dir / f'sonata/networks/nodes/{node_population_name}/nodes.h5').resolve()
        assert f'CellLibraryFile {nodes_file}' in (tmp_dir / 'CircuitConfig').open().read()
        assert nodes_file.stat().st_size > 100
        with h5py.File(nodes_file, 'r') as h5f:
            assert f'/nodes/{node_population_name}' in h5f

        edges_file = (tmp_dir / f'sonata/networks/edges/functional/{edge_population_name}/edges.h5').resolve()
        assert edges_file.stat().st_size > 100
        with h5py.File(edges_file, 'r') as h5f:
            assert f'/edges/{edge_population_name}' in h5f
        with h5py.File('connectome/functional/edges.h5', 'r') as h5f:
            assert f'/edges/{edge_population_name}' in h5f

        with h5py.File(edges_file, 'r') as h5f:
            assert node_population_name == h5f[f'/edges/{edge_population_name}/source_node_id'].attrs['node_population']
            assert node_population_name == h5f[f'/edges/{edge_population_name}/target_node_id'].attrs['node_population']
        with tmp_dir.joinpath('sonata/circuit_config.json').open('r') as f:
            config = json.load(f)
            assert config['networks']['nodes'][0]['nodes_file'] == f'$NETWORK_NODES_DIR/{node_population_name}/nodes.h5'
            assert config['networks']['edges'][0]['edges_file'] == f'$NETWORK_EDGES_DIR/{edge_population_name}/edges.h5'


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


def test_custom_module(caplog, capfd):
    with tmp_cwd():
        args = SNAKEMAKE_ARGS + ['-m', 'jinja2:invalid_module1:invalid_module_path']
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(run, args + ['circuitconfig_nrn'], catch_exceptions=False)

        captured = capfd.readouterr()
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert 'Snakemake process failed' in caplog.text
        # the stderr of the subprocess is available in captured.err and not result.stderr
        assert "Unable to locate a modulefile for 'invalid_module1'" in captured.err


def test_no_git_bioname(caplog, capfd):
    """This test verifies that bioname is checked to be under git."""
    with tempfile.TemporaryDirectory() as data_copy_dir:
        data_copy_dir = Path(data_copy_dir) / TEST_DATA_DIR.name
        shutil.copytree(TEST_DATA_DIR, data_copy_dir)
        args = ['--bioname', str(data_copy_dir), '-u', str(data_copy_dir / 'cluster.yaml')]
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(run, args, catch_exceptions=False)

        captured = capfd.readouterr()
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)
        assert 'Snakemake process failed' in caplog.text
        # the stderr of the subprocess is available in captured.err and not result.stderr
        assert f'{str(data_copy_dir)} must be under git' in captured.err


def test_snakemake_circuit_config():
    """This test verifies that building can happen via `snakemake`,
    and `CircuitConfig.j2` is accessible in this case."""
    with tmp_cwd() as tmp_dir:
        args = ['--jobs', '8', '-p', '--config', f'bioname={TEST_DATA_DIR}', '-u',
                str(TEST_DATA_DIR / 'cluster.yaml')]
        cmd = ['snakemake', '--snakefile', SNAKEFILE] + args + ['CircuitConfig_base']
        result = subprocess.run(cmd, check=True)

        assert result.returncode == 0
        tmp_dir = Path(tmp_dir)
        assert tmp_dir.joinpath('CircuitConfig_base').stat().st_size > 100
        assert f'CellLibraryFile circuit.mvd3' in (tmp_dir / 'CircuitConfig_base').open().read()


def test_snakemake_no_git_bioname():
    """This test verifies that bioname is checked to be under git when called via `snakemake`."""
    with tempfile.TemporaryDirectory() as data_copy_dir:
        data_copy_dir = Path(data_copy_dir) / TEST_DATA_DIR.name
        shutil.copytree(TEST_DATA_DIR, data_copy_dir)
        args = ['--jobs', '8', '-p', '--config', f'bioname={data_copy_dir}', '-u',
                str(TEST_DATA_DIR / 'cluster.yaml')]
        cmd = ['snakemake', '--snakefile', SNAKEFILE] + args + ['CircuitConfig_base']

        with pytest.raises(CalledProcessError) as exc_info:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        # the expected message is not contained in str(exception), but it's found in the stderr
        assert f'{str(data_copy_dir)} must be under git' in exc_info.value.stderr
