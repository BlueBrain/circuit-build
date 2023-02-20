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


def _get_slurm_config(cluster_config, slurm_env):
    """Return the slurm configuration corresponding to slurm_env."""
    if slurm_env in cluster_config:
        return cluster_config[slurm_env]
    if "__default__" in cluster_config:
        return cluster_config["__default__"]
    raise ValueError(f"{slurm_env} or __default__ must be defined in cluster configuration")


def _with_slurm(cmd, cluster_config, slurm_env):
    """Wrap the command with slurm/salloc."""
    slurm_config = _get_slurm_config(cluster_config, slurm_env)
    jobname = slurm_config.get("jobname", slurm_env)
    salloc = slurm_config["salloc"]
    cmd = _escape_single_quotes(cmd)
    cmd = f"salloc -J {jobname} {salloc} srun sh -c '{cmd}'"
    # set the environment variables if needed
    env_vars = slurm_config.get("env_vars")
    if env_vars:
        variables = " ".join(f"{k}={v}" for k, v in env_vars.items())
        cmd = f"export {variables} && {cmd}"
    return cmd


def build_module_cmd(cmd, config, cluster_config, slurm_env=None):
    """Wrap the command with modules."""
    modulepath = config.get("modulepath", SPACK_MODULEPATH)
    modules = config["modules"]
    if slurm_env and cluster_config:
        cmd = _with_slurm(cmd, cluster_config, slurm_env)
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


def build_apptainer_cmd(cmd, config, cluster_config, slurm_env=None):
    """Wrap the command with apptainer/singularity."""
    modulepath = config.get("modulepath", APPTAINER_MODULEPATH)
    modules = config.get("modules", APPTAINER_MODULES)
    options = config.get("options", APPTAINER_OPTIONS)
    executable = config.get("executable", APPTAINER_EXECUTABLE)
    image = Path(APPTAINER_IMAGEPATH, config["image"])
    # the current working directory is used also inside the container
    cmd = f'{executable} exec {options} {image} bash <<EOF\ncd "$(pwd)" && {cmd}\nEOF\n'
    if slurm_env and cluster_config:
        cmd = _with_slurm(cmd, cluster_config, slurm_env)
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


def build_venv_cmd(cmd, config, cluster_config, slurm_env=None):
    """Wrap the command with an existing virtual environment."""
    path = config["path"]
    if slurm_env and cluster_config:
        cmd = _with_slurm(cmd, cluster_config, slurm_env)
    cmd = f". {path}/bin/activate && {cmd}"
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
    env_mapping = {
        ENV_TYPE_MODULE: build_module_cmd,
        ENV_TYPE_APPTAINER: build_apptainer_cmd,
        ENV_TYPE_VENV: build_venv_cmd,
    }
    config = env_config[env_name]
    func = env_mapping[config["env_type"]]
    cmd = " ".join(map(str, cmd))
    cmd = func(
        cmd=cmd,
        config=config,
        cluster_config=cluster_config,
        slurm_env=slurm_env,
    )
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
