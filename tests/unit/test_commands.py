import pytest

from circuit_build import commands as test_module


@pytest.mark.parametrize(
    "env_name, slurm_env, env_config, expected",
    [
        pytest.param(
            "brainbuilder",
            "brainbuilder",
            {
                "brainbuilder": {
                    "env_type": "MODULE",
                    "modules": ["archive/2022-03", "brainbuilder/0.17.0"],
                },
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                "&& export MODULEPATH=/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta "
                "&& module load archive/2022-03 brainbuilder/0.17.0 "
                "&& echo MODULEPATH=/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta "
                "&& module list "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c 'echo mytest'"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="module",
        ),
        pytest.param(
            "brainbuilder",
            "brainbuilder_with_env_vars",
            {
                "brainbuilder": {
                    "env_type": "MODULE",
                    "modules": ["archive/2022-03", "brainbuilder/0.17.0"],
                },
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                "&& export MODULEPATH=/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta "
                "&& module load archive/2022-03 brainbuilder/0.17.0 "
                "&& echo MODULEPATH=/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta "
                "&& module list "
                "&& export MYVAR1=VALUE1 MYVAR2=VALUE2 "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c 'echo mytest'"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="module_with_env_vars",
        ),
        pytest.param(
            "brainbuilder",
            None,
            {
                "brainbuilder": {
                    "env_type": "MODULE",
                    "modules": ["archive/2022-03", "brainbuilder/0.17.0"],
                },
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                "&& export MODULEPATH=/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta "
                "&& module load archive/2022-03 brainbuilder/0.17.0 "
                "&& echo MODULEPATH=/gpfs/bbp.cscs.ch/ssd/apps/bsd/modules/_meta "
                "&& module list "
                "&& echo mytest"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="module_without_slurm",
        ),
        pytest.param(
            "brainbuilder",
            "brainbuilder",
            {
                "brainbuilder": {"env_type": "APPTAINER", "image": "nse/brainbuilder_0.17.1.sif"},
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                "&& module use /gpfs/bbp.cscs.ch/apps/hpc/singularity/modules/linux-rhel7-x86_64 "
                "&& module load archive/2021-12 singularityce "
                "&& singularity --version "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c '"
                "singularity exec --cleanenv --containall --bind $TMPDIR:/tmp,/gpfs/bbp.cscs.ch/project "
                "/gpfs/bbp.cscs.ch/project/proj30/singularity-images/nse/brainbuilder_0.17.1.sif "
                "echo mytest'"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="apptainer",
        ),
        pytest.param(
            "brainbuilder",
            None,
            {
                "brainbuilder": {"env_type": "APPTAINER", "image": "nse/brainbuilder_0.17.1.sif"},
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                "&& module use /gpfs/bbp.cscs.ch/apps/hpc/singularity/modules/linux-rhel7-x86_64 "
                "&& module load archive/2021-12 singularityce "
                "&& singularity --version "
                "&& singularity exec --cleanenv --containall --bind $TMPDIR:/tmp,/gpfs/bbp.cscs.ch/project "
                "/gpfs/bbp.cscs.ch/project/proj30/singularity-images/nse/brainbuilder_0.17.1.sif "
                "echo mytest"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="apptainer_without_slurm",
        ),
        pytest.param(
            "brainbuilder",
            "brainbuilder",
            {
                "brainbuilder": {"env_type": "VENV", "path": "/path/to/venv"},
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /path/to/venv/bin/activate "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c 'echo mytest'"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="venv",
        ),
        pytest.param(
            "brainbuilder",
            None,
            {
                "brainbuilder": {"env_type": "VENV", "path": "/path/to/venv"},
            },
            (
                "set -o pipefail; ( set -ex; "
                ". /path/to/venv/bin/activate && echo mytest"
                " ) 2>&1 | tee -a {log} 1>&2"
            ),
            id="venv_without_slurm",
        ),
    ],
)
def test_build_command(env_name, slurm_env, env_config, expected):
    cmd = ["echo", "mytest"]
    cluster_config = {
        "__default__": {"salloc": "-A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:05:00"},
        "brainbuilder": {"salloc": "-A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00"},
        "brainbuilder_with_env_vars": {
            "jobname": "brainbuilder",
            "salloc": "-A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00",
            "env_vars": {"MYVAR1": "VALUE1", "MYVAR2": "VALUE2"},
        },
    }
    skip_run = False
    result = test_module.build_command(
        cmd=cmd,
        env_config=env_config,
        env_name=env_name,
        cluster_config=cluster_config,
        slurm_env=slurm_env,
        skip_srun=skip_run,
    )
    assert result == expected
