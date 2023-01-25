import os

import pytest
from xdist.scheduler.loadscope import LoadScopeScheduling


def pytest_addoption(parser):
    parser.addoption(
        "--basetemp-permissions",
        action="store",
        help=(
            "Permissions of the base temporary directory used by tmp_path, "
            "as octal value. Examples: 700 (default), 750, 770"
        ),
    )


@pytest.fixture
def tmp_path(tmp_path, request):
    permissions = request.config.getoption("--basetemp-permissions")
    if permissions:
        permissions = int(permissions, 8)
        # enforce the permissions according to the temp directory layout:
        # - <basetemp>/test_<name>, when running without pytest-xdist
        # - <basetemp>/popen-gw<num>/test_<name>, when running with pytest-xdist
        tmp_path.chmod(permissions)
        tmp_path.parent.chmod(permissions)
        if os.getenv("PYTEST_XDIST_WORKER_COUNT"):
            tmp_path.parent.parent.chmod(permissions)
    return tmp_path


# tests that should not be grouped together, even when they belong to the same module
PARALLEL_TESTS = {
    "tests/functional/test_run.py::test_functional_all",
    "tests/functional/test_run_synthesis.py::test_synthesis",
}


class CustomScheduler(LoadScopeScheduling):
    """Implement load scheduling across nodes, but grouping test by scope."""

    def _split_scope(self, nodeid):
        """Determine the scope (grouping) of a nodeid."""
        if nodeid in PARALLEL_TESTS:
            return nodeid
        return super()._split_scope(nodeid)


def pytest_xdist_make_scheduler(config, log):
    return CustomScheduler(config, log)
