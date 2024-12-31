# The find_stack_level function is adapted from the `pandas.util._exceptions.find_stack_level`
# function from the pandas library licensed under the BSD 3-Clause license.
# pandas source code is available at https://github.com/pandas-dev/pandas
import inspect
from pathlib import Path

_pkg_and_tests_dirs: tuple[str, tuple[str, ...]] | None = None


def _get_dirs() -> tuple[str, tuple[str, ...]]:
    global _pkg_and_tests_dirs
    if _pkg_and_tests_dirs is None:
        import roseau.load_flow

        pkg_dir = Path(roseau.load_flow.__file__).parent
        test_dirs = tuple(str(p) for p in pkg_dir.glob("**/tests") if p.is_dir())
        _pkg_and_tests_dirs = str(pkg_dir), test_dirs
    return _pkg_and_tests_dirs


def find_stack_level() -> int:
    """Find the first place in the stack that is not inside `roseau.load_flow` (tests notwithstanding)."""
    pkg_dir, test_dirs = _get_dirs()

    # https://stackoverflow.com/questions/17407119/python-inspect-stack-is-slow
    frame = inspect.currentframe()
    try:
        n = 0
        while frame:  # pragma: no cover
            filename = inspect.getfile(frame)
            if filename.startswith(pkg_dir) and not filename.startswith(test_dirs):
                frame = frame.f_back
                n += 1
            else:
                break
    finally:
        # See note in https://docs.python.org/3/library/inspect.html#inspect.Traceback
        # And Issue https://github.com/pandas-dev/pandas/issues/54628
        del frame
    return max(n, 2)
