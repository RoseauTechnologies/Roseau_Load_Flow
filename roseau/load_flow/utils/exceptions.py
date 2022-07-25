class ThundersException(Exception):
    """A base class for all exception in Thunders"""

    pass


class ThundersRuntimeError(ThundersException, RuntimeError):
    """A generic runtime error class for Thunders"""

    pass


class ThundersLoadFlowError(ThundersRuntimeError):
    """An error related to the convergence of the load flow in Thunders."""

    pass


class ThundersValueError(ThundersException, ValueError):
    """A generic value error class for Thunders"""

    pass


class ThundersIOError(ThundersException, IOError):
    """A generic io error class for Thunders"""

    pass
