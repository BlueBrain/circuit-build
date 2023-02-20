from xdist.scheduler.loadscope import LoadScopeScheduling


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
