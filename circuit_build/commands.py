"""Utilities to build the commands to execute the Snakemake rules."""
from circuit_build.utils import escape_single_quotes, redirect_to_file


def bbp_env(modules_config, cluster_config, module_env, command, slurm_env=None, skip_srun=False):
    """Wrap and return the command string to be executed."""
    result = " ".join(map(str, command))

    if slurm_env and cluster_config:
        if slurm_env in cluster_config:
            slurm_config = cluster_config[slurm_env]
        else:
            # break only if __default__ is needed and missing
            slurm_config = cluster_config["__default__"]
        result = "salloc -J {jobname} {alloc} {srun} sh -c '{cmd}'".format(
            jobname=slurm_config.get("jobname", slurm_env),
            alloc=slurm_config["salloc"],
            srun="" if skip_srun else "srun",
            cmd=escape_single_quotes(result),
        )
        # set the environment variables if needed
        env_vars = slurm_config.get("env_vars")
        if env_vars:
            variables = " ".join(f"{k}={v}" for k, v in env_vars.items())
            result = f"env {variables} {result}"

    if module_env:
        modulepath, modules = modules_config[module_env]
        result = " && ".join(
            [
                ". /etc/profile.d/modules.sh",
                "module purge",
                f"export MODULEPATH={modulepath}",
                f"module load {' '.join(modules)}",
                f"echo MODULEPATH={modulepath}",
                "module list",
                result,
            ]
        )

    return redirect_to_file(result)
