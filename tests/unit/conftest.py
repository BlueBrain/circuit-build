from xdist.scheduler.loadscope import LoadScopeScheduling


class CustomScheduler(LoadScopeScheduling):
    """Implement load scheduling across nodes, but grouping test by scope."""

    def _split_scope(self, nodeid):
        """Determine the scope (grouping) of a nodeid."""
        # tests that should not be grouped together, even though they belong to the same module
        if nodeid in {
            "tests/unit/test_run.py::test_functional_all",
            "tests/unit/test_run.py::test_synthesis",
        }:
            return nodeid
        return super()._split_scope(nodeid)


def pytest_xdist_make_scheduler(config, log):
    return CustomScheduler(config, log)
