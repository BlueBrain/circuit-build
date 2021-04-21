"""Cli module"""
from pathlib import Path
import subprocess
import click
import pkg_resources
import json


@click.group()
@click.version_option()
def cli():
    """The CLI entry point"""


def _index(args, *opts):
    """Finds index position of `opts` in `args`"""
    indices = [i for i, arg in enumerate(args) if arg in opts]
    assert len(indices) < 2, f'{opts} options can\'t be used together, use only one of them'
    if len(indices) == 0:
        return None
    return indices[0]


@cli.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option(
    '-u', '--cluster-config', required=True, type=click.Path(exists=True, dir_okay=False),
    help='Path to cluster config.',
)
@click.option(
    '--bioname', required=True, type=click.Path(exists=True, file_okay=False),
    help='Path to `bioname` folder of a circuit.',
)
@click.option(
    '-m', '--module', 'modules', multiple=True, required=False,
    help='''
Modules to be overwritten. Multiple configurations are allowed, and each one
should be given in the format:\n
    module_env:module_name/module_version[,module_name/module_version...][:module_path]\n
Examples:\n
    brainbuilder:archive/2020-08,brainbuilder/0.14.0\n
    touchdetector:archive/2020-05,touchdetector/5.4.0,hpe-mpi\n
    spykfunc:archive/2020-06,spykfunc/0.15.6:/gpfs/bbp.cscs.ch/ssd/apps/hpc/jenkins/modules/all
    '''
)
@click.option(
    '-s', '--snakefile', required=False, type=click.Path(exists=True, dir_okay=False),
    default=pkg_resources.resource_filename(__name__, 'snakemake/Snakefile'), show_default=True,
    help='Path to workflow definition in form of a snakefile.',
)
@click.pass_context
def run(ctx, cluster_config: str, bioname: str, modules: list, snakefile: str):
    """Run a circuit-build task.

    Any additional snakemake arguments or options can be passed at the end of this command's call.
    """

    def _build_config_args():
        config_args = ['--config', f'bioname={bioname}']
        if modules:
            # serialize the list of strings with json to be backward compatible with Snakemake:
            # snakemake >= 5.28.0 loads config using yaml.BaseLoader,
            # snakemake < 5.28.0 loads config using eval.
            config_args += [f'modules={json.dumps(modules)}']
        return config_args

    args = ctx.args
    if snakefile is None:
        snakefile = pkg_resources.resource_filename(__name__, 'snakemake/Snakefile')
    assert Path(snakefile).is_file(), f'Snakefile "{snakefile}" does not exist!'
    assert _index(args, '--config', '-C') is None, 'snakemake `--config` option is not allowed'

    if _index(args, '--printshellcmds', '-p') is None:
        args = ['--printshellcmds'] + args
    if _index(args, '--cores', '--jobs', '-j') is None:
        args = ['--jobs', '8'] + args
    args += _build_config_args()

    cmd = ['snakemake', *args, '--snakefile', snakefile, '--cluster-config', cluster_config]
    return subprocess.run(cmd, check=True)


@cli.command()
def snakefile_path():
    """Outputs a path to the default Snakefile."""
    click.echo(pkg_resources.resource_filename(__name__, 'snakemake/Snakefile'))
