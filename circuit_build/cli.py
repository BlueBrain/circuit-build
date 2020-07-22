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


def _set_bioname_config(args, bioname):
    """Sets a proper bioname path into snakemake config."""
    config_index = _index(args, '--config', '-C')
    if config_index is None:
        args += ['--config', 'bioname=' + bioname]
    else:
        next_opt_index = len(args)
        for idx in range(config_index + 1, len(args)):
            if args[idx].startswith('bioname'):
                raise ValueError('Bioname path can be set only with `bioname` argument')
            if args[idx].startswith('-'):
                next_opt_index = idx
        args.insert(next_opt_index, 'bioname=' + bioname)


@cli.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option('-u', '--cluster-config', required=True, type=click.Path(exists=True, dir_okay=False))
@click.option('--bioname', required=True, type=click.Path(exists=True, file_okay=False))
@click.option('-s', '--snakefile', required=False, type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def run(ctx, cluster_config: str, bioname: str, snakefile: str = None):
    """Run a circuit-build task.

    Any additional snakemake arguments or options can be passed at the end of this command's call.

    Args:
        ctx: context for collecting all unrecognized options and pass them further to snakemake
        cluster_config: path to cluster config
        bioname: path to 'bioname' folder of a circuit
        snakefile: path to the sonata circuit config file. By default
    """
    if snakefile is None:
        snakefile = pkg_resources.resource_filename(__name__, 'snakemake/Snakefile')
    assert Path(snakefile).is_file(), 'Project\'s Snakefile does not exist!'
    args = ctx.args
    if _index(args, '--printshellcmds', '-p') is None:
        args = ['--printshellcmds'] + args
    if _index(args, '--cores', '--jobs', '-j') is None:
        args = ['--jobs', '8'] + args
    _set_bioname_config(args, bioname)
    cmd = ['snakemake', *args, '--snakefile', snakefile, '--cluster-config', cluster_config]
    return subprocess.run(cmd, check=True)


@cli.command()
def snakefile_path():
    """Outputs a path to the default Snakefile."""
    click.echo(pkg_resources.resource_filename(__name__, 'snakemake/Snakefile'))
