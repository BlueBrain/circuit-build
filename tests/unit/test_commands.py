import pytest

from circuit_build import commands as test_module
from circuit_build.constants import (
    APPTAINER_EXECUTABLE,
    APPTAINER_IMAGEPATH,
    APPTAINER_MODULEPATH,
    APPTAINER_MODULES,
    APPTAINER_OPTIONS,
    SPACK_MODULEPATH,
)


@pytest.mark.parametrize("log_all_to_stderr", [True, False])
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
                "set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                f"&& export MODULEPATH={SPACK_MODULEPATH} "
                "&& module load archive/2022-03 brainbuilder/0.17.0 "
                f"&& echo MODULEPATH={SPACK_MODULEPATH} "
                "&& module list "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c 'echo mytest'"
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
                "set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                f"&& export MODULEPATH={SPACK_MODULEPATH} "
                "&& module load archive/2022-03 brainbuilder/0.17.0 "
                f"&& echo MODULEPATH={SPACK_MODULEPATH} "
                "&& module list "
                "&& export MYVAR1=VALUE1 MYVAR2=VALUE2 "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c 'echo mytest'"
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
                "set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                f"&& export MODULEPATH={SPACK_MODULEPATH} "
                "&& module load archive/2022-03 brainbuilder/0.17.0 "
                f"&& echo MODULEPATH={SPACK_MODULEPATH} "
                "&& module list "
                "&& echo mytest"
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
                "set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                f"&& module use {APPTAINER_MODULEPATH} "
                f"&& module load {' '.join(APPTAINER_MODULES)} "
                f"&& {APPTAINER_EXECUTABLE} --version "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c '"
                f"{APPTAINER_EXECUTABLE} exec {APPTAINER_OPTIONS} "
                f"{APPTAINER_IMAGEPATH}/nse/brainbuilder_0.17.1.sif "
                'bash <<EOF\ncd "$(pwd)" && echo mytest\nEOF\n\''
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
                "set -ex; "
                ". /etc/profile.d/modules.sh "
                "&& module purge "
                f"&& module use {APPTAINER_MODULEPATH} "
                f"&& module load {' '.join(APPTAINER_MODULES)} "
                f"&& {APPTAINER_EXECUTABLE} --version "
                f"&& {APPTAINER_EXECUTABLE} exec {APPTAINER_OPTIONS} "
                f"{APPTAINER_IMAGEPATH}/nse/brainbuilder_0.17.1.sif "
                'bash <<EOF\ncd "$(pwd)" && echo mytest\nEOF\n'
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
                "set -ex; "
                ". /path/to/venv/bin/activate "
                "&& salloc -J brainbuilder -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00 "
                "srun sh -c 'echo mytest'"
            ),
            id="venv",
        ),
        pytest.param(
            "brainbuilder",
            None,
            {
                "brainbuilder": {"env_type": "VENV", "path": "/path/to/venv"},
            },
            "set -ex; . /path/to/venv/bin/activate && echo mytest",
            id="venv_without_slurm",
        ),
        pytest.param(
            "touchdetector",
            "touchdetector",
            {
                "touchdetector": {"env_type": "VENV", "path": "/path/to/venv"},
            },
            (
                "set -ex; "
                ". /path/to/venv/bin/activate "
                "&& salloc -J touchdetector -A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:05:00 "
                "srun sh -c 'echo mytest'"
            ),
            id="fallback_to_default_cluster",
        ),
    ],
)
def test_build_command(env_name, slurm_env, env_config, expected, log_all_to_stderr, monkeypatch):
    if log_all_to_stderr:
        monkeypatch.setenv("LOG_ALL_TO_STDERR", "true")
        expected = f"set -o pipefail; ( {expected} ) 2>&1 | tee -a {{log}} 1>&2"
    else:
        monkeypatch.delenv("LOG_ALL_TO_STDERR", raising=False)
        expected = f"( {expected} ) >{{log}} 2>&1"
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


def test_build_command_raises_when_slurm_env_is_missing():
    env_name = "brainbuilder"
    slurm_env = "brainbuilder"
    env_config = {"brainbuilder": {"env_type": "VENV", "path": "/path/to/venv"}}
    cluster_config = {"other": {"salloc": "-A ${{SALLOC_ACCOUNT}} -p prod_small --time 0:10:00"}}
    cmd = ["echo", "mytest"]
    skip_run = False
    match = "brainbuilder or __default__ must be defined in cluster configuration"
    with pytest.raises(Exception, match=match):
        test_module.build_command(
            cmd=cmd,
            env_config=env_config,
            env_name=env_name,
            cluster_config=cluster_config,
            slurm_env=slurm_env,
            skip_srun=skip_run,
        )


@pytest.mark.parametrize(
    "custom_modules, expected",
    [
        ([], {}),
        (
            [
                "brainbuilder:archive/2020-08,brainbuilder/0.14.0",
                "touchdetector:archive/2020-05,touchdetector/5.4.0,hpe-mpi",
                "spykfunc:archive/2020-06,spykfunc/0.15.6:/custom/path/to/modules",
            ],
            {
                "brainbuilder": {
                    "env_type": "MODULE",
                    "modulepath": SPACK_MODULEPATH,
                    "modules": ["archive/2020-08", "brainbuilder/0.14.0"],
                },
                "touchdetector": {
                    "env_type": "MODULE",
                    "modulepath": SPACK_MODULEPATH,
                    "modules": ["archive/2020-05", "touchdetector/5.4.0", "hpe-mpi"],
                },
                "spykfunc": {
                    "env_type": "MODULE",
                    "modulepath": "/custom/path/to/modules",
                    "modules": ["archive/2020-06", "spykfunc/0.15.6"],
                },
            },
        ),
    ],
)
def test_load_legacy_env_config(custom_modules, expected):
    result = test_module.load_legacy_env_config(custom_modules)
    assert result == expected


@pytest.mark.parametrize(
    "custom_modules",
    [
        ["brainbuilder"],
        ["brainbuilder:archive/2020-08,brainbuilder/0.14.0::"],
    ],
)
def test_load_legacy_env_config_raises_when_format_is_invalid(custom_modules):
    match = "Invalid custom spack module format"
    with pytest.raises(Exception, match=match):
        test_module.load_legacy_env_config(custom_modules)


@pytest.mark.parametrize(
    "custom_modules",
    [
        ["unknown_env:archive/2020-08,brainbuilder/0.14.0"],
        ["unknown_env:archive/2020-08,brainbuilder/0.14.0:/custom/path/to/modules"],
    ],
)
def test_load_legacy_env_config_raises_when_environment_is_unknown(custom_modules):
    match = "Unknown environment: unknown_env, known environments are"
    with pytest.raises(Exception, match=match):
        test_module.load_legacy_env_config(custom_modules)
