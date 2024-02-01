"""Utilities to build the commands to execute the Snakemake rules."""

from pathlib import Path

from circuit_build.constants import (
    APPTAINER_EXECUTABLE,
    APPTAINER_IMAGEPATH,
    APPTAINER_MODULEPATH,
    APPTAINER_MODULES,
    APPTAINER_OPTIONS,
    ENV_CONFIG,
    ENV_TYPE_APPTAINER,
    ENV_TYPE_MODULE,
    ENV_TYPE_VENV,
    SPACK_MODULEPATH,
)
from circuit_build.utils import redirect_to_file


def _escape_single_quotes(value):
    """Return the given string after escaping the single quote character."""
    return value.replace("'", "'\\''")


def _unset_threads_vars(cmd):
    """Unset the THREADS env variables because they may interfere with jobs.

    They are automatically set by Snakemake, depending on the `threads` configuration,
    see https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#threads
    and https://github.com/snakemake/snakemake/blob/e9f67318/snakemake/shell.py#L216-L221
    """
    env_vars = [
        "GOTO_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ]
    return f"unset {' '.join(env_vars)} && {cmd}"


def _get_source_file(path):
    """Return the activation file if the path is a venv directory, or the same path otherwise."""
    path = Path(path)
    if path.is_dir():
        path = path / "bin" / "activate"
    if not path.is_file():
        raise ValueError(
            "The given path must be a virtualenv directory, or a file that will be sourced as is."
        )
    return path


def _get_slurm_config(cluster_config, slurm_env):
    """Return the slurm configuration corresponding to slurm_env."""
    if not slurm_env or not cluster_config:
        return {}
    if slurm_env in cluster_config:
        selected = cluster_config[slurm_env]
    elif "__default__" in cluster_config:
        selected = cluster_config["__default__"]
    else:
        raise ValueError(f"{slurm_env} or __default__ must be defined in cluster configuration")
    return {"jobname": slurm_env, **selected}


def _with_slurm(cmd, cluster_config):
    """Wrap the command with slurm/salloc."""
    if cluster_config:
        jobname = cluster_config["jobname"]
        salloc = cluster_config["salloc"]
        cmd = _escape_single_quotes(cmd)
        cmd = f"salloc -J {jobname} {salloc} srun sh -c '{cmd}'"
    return cmd


def _with_env_vars(cmd, env_config, cluster_config):
    """Wrap the command with exporting the environment variables if needed."""
    env_vars = {
        **env_config.get("env_vars", {}),
        **cluster_config.get("env_vars", {}),
    }
    if env_vars:
        variables = " ".join(f"{k}={v}" for k, v in env_vars.items())
        cmd = f"export {variables} && {cmd}"
    return cmd


def build_module_cmd(cmd, env_config, cluster_config):
    """Wrap the command with modules."""
    modulepath = env_config.get("modulepath", SPACK_MODULEPATH)
    modules = env_config["modules"]
    cmd = _with_env_vars(cmd, env_config, cluster_config)
    cmd = _with_slurm(cmd, cluster_config)
    return " && ".join(
        [
            ". /etc/profile.d/modules.sh",
            "module purge",
            f"export MODULEPATH={modulepath}",
            f"module load {' '.join(modules)}",
            f"echo MODULEPATH={modulepath}",
            "module list",
            cmd,
        ]
    )


def build_apptainer_cmd(cmd, env_config, cluster_config):
    """Wrap the command with apptainer/singularity."""
    modulepath = env_config.get("modulepath", APPTAINER_MODULEPATH)
    modules = env_config.get("modules", APPTAINER_MODULES)
    options = env_config.get("options", APPTAINER_OPTIONS)
    executable = env_config.get("executable", APPTAINER_EXECUTABLE)
    image = Path(APPTAINER_IMAGEPATH, env_config["image"])
    # the current working directory is used also inside the container
    cmd = f'{executable} exec {options} {image} bash <<EOF\ncd "$(pwd)" && {cmd}\nEOF\n'
    cmd = _with_env_vars(cmd, env_config, cluster_config)
    cmd = _with_slurm(cmd, cluster_config)
    cmd = " && ".join(
        [
            ". /etc/profile.d/modules.sh",
            "module purge",
            f"module use {modulepath}",
            f"module load {' '.join(modules)}",
            "singularity --version",
            cmd,
        ]
    )
    return cmd


def build_venv_cmd(cmd, env_config, cluster_config):
    """Wrap the command with an existing virtual environment, or source a custom file."""
    source = _get_source_file(env_config["path"])
    cmd = f". {source} && {cmd}"
    cmd = _with_env_vars(cmd, env_config, cluster_config)
    cmd = _with_slurm(cmd, cluster_config)
    modulepath = env_config.get("modulepath", SPACK_MODULEPATH)
    modules = env_config.get("modules")
    if modules:
        cmd = " && ".join(
            [
                ". /etc/profile.d/modules.sh",
                "module purge",
                f"export MODULEPATH={modulepath}",
                f"module load {' '.join(modules)}",
                f"echo MODULEPATH={modulepath}",
                "module list",
                cmd,
            ]
        )
    return cmd


def build_command(cmd, env_config, env_name, cluster_config, slurm_env=None):
    """Wrap and return the command string to be executed.

    Args:
        cmd (list): command to be executed as a list of strings.
        env_config (dict): environment configuration.
        env_name (str): key in env_config.
        cluster_config (dict): cluster configuration.
        slurm_env (str): key in cluster_config.
    """
    selected_env_config = env_config[env_name]
    selected_cluster_config = _get_slurm_config(cluster_config, slurm_env)
    func = {
        ENV_TYPE_MODULE: build_module_cmd,
        ENV_TYPE_APPTAINER: build_apptainer_cmd,
        ENV_TYPE_VENV: build_venv_cmd,
    }[selected_env_config["env_type"]]
    cmd = " ".join(map(str, cmd))
    cmd = func(
        cmd=cmd,
        env_config=selected_env_config,
        cluster_config=selected_cluster_config,
    )
    cmd = _unset_threads_vars(cmd)
    cmd = redirect_to_file(cmd)
    return cmd


def load_legacy_env_config(custom_modules):
    """Return the loader_configuration after overwriting it with the custom modules.

    Custom modules can be configured using one of:
    - configuration file MANIFEST.yaml -> list of str from yaml
    - command line parameter --config -> list of str from json for backward compatibility

    Examples:
    - brainbuilder:archive/2020-08,brainbuilder/0.14.0
    - touchdetector:archive/2020-05,touchdetector/5.4.0,hpe-mpi
    - spykfunc:archive/2020-06,spykfunc/0.15.6:/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta
    """
    env_config = {}
    for module in custom_modules:
        parts = module.split(":")
        if len(parts) not in (2, 3):
            raise ValueError(f"Invalid custom spack module format: {module}")
        module_env = parts[0]
        if module_env not in ENV_CONFIG:
            raise ValueError(
                f"Unknown environment: {module_env}, known environments are: {','.join(ENV_CONFIG)}"
            )
        module_list = parts[1].split(",")
        module_path = parts[2] if len(parts) == 3 else SPACK_MODULEPATH
        env_config[module_env] = {
            "env_type": ENV_TYPE_MODULE,
            "modulepath": module_path,
            "modules": module_list,
        }
    return env_config
