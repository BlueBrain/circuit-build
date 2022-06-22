from circuit_build.constants import APPTAINER_MODULES, ENV_CONFIG, ENV_TYPE_MODULE
from circuit_build.version import VERSION


def test_release_does_not_contain_unstable_modules():
    is_release = "dev" not in VERSION
    unstable_envs = [
        env_name
        for env_name, config in ENV_CONFIG.items()
        if config["env_type"] == ENV_TYPE_MODULE and "unstable" in config["modules"]
    ]
    env_types = set(config["env_type"] for config in ENV_CONFIG.values())
    if is_release:
        assert unstable_envs == [], "No unstable modules are allowed in a release"
        assert env_types == {ENV_TYPE_MODULE}, "Only modules can be used in a release"
        assert (
            "unstable" not in APPTAINER_MODULES
        ), "No unstable Apptainer/Singularity modules are allowed in a release"
