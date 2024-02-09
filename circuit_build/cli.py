"""Cli module."""

import contextlib
import importlib.resources
import json
import logging
import subprocess
import sys
from datetime import datetime
from functools import partial
from pathlib import Path

import click

from circuit_build.utils import clean_slurm_env

L = logging.getLogger()


@contextlib.contextmanager
def _snakefile(snakefile):
    """Ensure that snakefile is available, and deleted if it's a temporary file."""
    if snakefile is None:
        ref = importlib.resources.files(__package__) / "snakemake" / "Snakefile"
        with importlib.resources.as_file(ref) as path:
            yield path
    else:
        path = Path(snakefile)
        if not path.is_file():
            raise RuntimeError(f"Snakefile '{path}' does not exist!")
        yield path


def _index(args, *opts):
    """Finds index position of `opts` in `args`."""
    indices = [i for i, arg in enumerate(args) if arg in opts]
    assert len(indices) < 2, f"{opts} options can't be used together, use only one of them"
    if len(indices) == 0:
        return None
    return indices[0]


def _build_cmd(base_cmd, args, bioname, modules, timestamp, cluster_config, skip_check_git=False):
    # force the timestamp to the same value in different executions of snakemake
    extra_args = [
        "--config",
        f"bioname={bioname}",
        f"timestamp={timestamp}",
        f"cluster_config={cluster_config}",
    ]
    if modules:
        # serialize the list of strings with json to be backward compatible with Snakemake:
        # snakemake >= 5.28.0 loads config using yaml.BaseLoader,
        # snakemake < 5.28.0 loads config using eval.
        extra_args += [f'modules={json.dumps(modules, separators=(",", ":"))}']
    if skip_check_git:
        extra_args += ["skip_check_git=1"]
    if _index(args, "--cores", "--jobs", "-j") is None:
        extra_args += ["--jobs", "8"]
    if _index(args, "--printshellcmds", "-p") is None:
        extra_args += ["--printshellcmds"]
    # prepend the extra args to args
    return base_cmd + extra_args + args


def _run_snakemake_process(cmd, errorcode=1):
    """Run the main snakemake process."""
    L.info("Command: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        L.error("Snakemake process failed")
        return errorcode
    return 0


def _run_summary_process(cmd, filepath: Path, errorcode=2):
    """Save the summary to file."""
    cmd = cmd + ["--detailed-summary"]
    L.info("Command: %s", " ".join(cmd))
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w") as fd:
        result = subprocess.run(cmd, stdout=fd, check=False)
    if result.returncode != 0:
        L.error("Summary process failed")
        return errorcode
    return 0


def _run_report_process(cmd, filepath: Path, errorcode=4):
    """Save the report to file."""
    cmd = cmd + ["--report", str(filepath)]
    L.info("Command: %s", " ".join(cmd))
    filepath.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        L.error("Report process failed")
        return errorcode
    return 0


@click.group()
@click.version_option()
@click.option("-v", "--verbose", count=True, default=0, help="-v for INFO, -vv for DEBUG")
def cli(verbose):
    """The CLI entry point."""
    logformat = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    level = (logging.WARNING, logging.INFO, logging.DEBUG)[min(verbose, 2)]
    logging.basicConfig(level=level, format=logformat)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.option(
    "-u",
    "--cluster-config",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to cluster config.",
)
@click.option(
    "--bioname",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to `bioname` folder of a circuit.",
)
@click.option(
    "-m",
    "--module",
    "modules",
    multiple=True,
    required=False,
    help="""
Modules to be overwritten, intended for internal or experimental use.\n
Multiple configurations are allowed, and each one should be given in the format:\n
    module_env:module_name/module_version[,module_name/module_version...][:module_path]\n
Examples:\n
    brainbuilder:archive/2020-08,brainbuilder/0.14.0\n
    touchdetector:archive/2020-05,touchdetector/5.4.0,hpe-mpi\n
    spykfunc:archive/2020-06,spykfunc/0.15.6:/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta
    """,
)
@click.option(
    "-s",
    "--snakefile",
    required=False,
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    show_default=True,
    help="Path to workflow definition in form of a snakefile, needed only to override the builtin.",
)
@click.option(
    "-d",
    "--directory",
    required=False,
    type=click.Path(exists=False, file_okay=False),
    help="Working directory (relative paths in the snakefile will use this as their origin).",
    default=".",
    show_default=True,
)
@click.option(
    "--with-summary", is_flag=True, help="Save a summary in `logs/<timestamp>/summary.tsv`."
)
@click.option(
    "--with-report", is_flag=True, help="Save a report in `logs/<timestamp>/report.html`."
)
@click.pass_context
def run(
    ctx,
    cluster_config: str,
    bioname: str,
    modules: list,
    snakefile: str,
    directory: str,
    with_summary: bool,
    with_report: bool,
):
    """Run a circuit-build task.

    Any additional snakemake arguments or options can be passed at the end of this command's call.
    """
    args = ctx.args
    assert _index(args, "--config", "-C") is None, "snakemake `--config` option is not allowed"

    clean_slurm_env()

    with _snakefile(snakefile) as snakefile_path:
        base_cmd = [
            "snakemake",
            "--snakefile",
            str(snakefile_path),
            "--directory",
            directory,
        ]
        timestamp = f"{datetime.now():%Y%m%dT%H%M%S}"
        build_cmd = partial(_build_cmd, base_cmd, args, bioname, modules, timestamp, cluster_config)
        exit_code = _run_snakemake_process(cmd=build_cmd())
        if with_summary:
            # snakemake with the --summary/--detailed-summary option does not execute the workflow
            filepath = Path(f"{directory}/logs/{timestamp}/summary.tsv")
            L.info("Creating report in %s", filepath)
            exit_code += _run_summary_process(cmd=build_cmd(skip_check_git=True), filepath=filepath)
        if with_report:
            # snakemake with the --report option does not execute the workflow
            filepath = Path(f"{directory}/logs/{timestamp}/report.html")
            L.info("Creating summary in %s", filepath)
            exit_code += _run_report_process(cmd=build_cmd(skip_check_git=True), filepath=filepath)

    # cumulative exit code given by the union of the exit codes, only for internal use
    #   0: success
    #   1: snakemake process failed
    #   2: summary process failed
    #   4: report process failed
    sys.exit(exit_code)
