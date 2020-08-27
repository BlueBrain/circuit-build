"""Cli module"""
from pathlib import Path
import subprocess
import click
import pkg_resources


@click.group()
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
@click.option('-u', '--cluster-config', required=True, type=click.Path(exists=True, dir_okay=False))
@click.option('--bioname', required=True, type=click.Path(exists=True, file_okay=False))
@click.option('-m', '--module', 'modules', multiple=True, required=False)
@click.option('-s', '--snakefile', required=False, type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def run(ctx, cluster_config: str, bioname: str, modules: list, snakefile: str = None):
    """Run a circuit-build task.

    Any additional snakemake arguments or options can be passed at the end of this command's call.

    Args:
        ctx: context for collecting all unrecognized options and pass them further to snakemake
        cluster_config: path to cluster config
        bioname: path to 'bioname' folder of a circuit
        modules: spack modules that are overwritten by a user
        snakefile: path to the sonata circuit config file. By default
    """

    def _build_config_args():
        config_args = ['--config', f'bioname={bioname}']
        if modules:
            config_args += [f'modules={modules}']
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
    return subprocess.run(cmd, check=True, capture_output=True)


@cli.command()
def snakefile_path():
    """Outputs a path to the default Snakefile."""
    click.echo(pkg_resources.resource_filename(__name__, 'snakemake/Snakefile'))
