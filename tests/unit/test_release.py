from circuit_build.constants import MODULES
from circuit_build.version import VERSION


def test_release_does_not_contain_unstable_modules():
    is_release = "dev" not in VERSION
    unstable_envs = [
        module_env
        for module_env, (module_path, modules) in MODULES.items()
        if "unstable" in modules
    ]
    if is_release:
        assert unstable_envs == []
