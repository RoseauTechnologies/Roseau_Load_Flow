import pytest

from roseau.load_flow.utils.deprecations import (
    deprecate_nonkeyword_arguments,
    deprecate_parameter_as_multi_positional,
    deprecate_renamed_parameter,
    deprecate_renamed_parameters,
)


class Deprecations:
    @deprecate_renamed_parameter("old", "new", version="1.0.0")
    def __init__(self, new=None):
        self.attr = new

    @deprecate_renamed_parameter("old", "new", version="1.0.0")
    def renamed_parameter(self, new: str):
        return new

    @deprecate_renamed_parameters({"old1": "new1", "old2": "new2"}, version="1.0.0")
    def renamed_parameters(self, new1: str, *, new2: str):
        return new1, new2

    @deprecate_nonkeyword_arguments(allowed_args=("self", "arg1"), version="1.0.0")
    def nonkeyword_arguments(self, arg1: str, kwd: str):
        return arg1, kwd

    @deprecate_nonkeyword_arguments(version="1.0.0")
    def nonkeyword_arguments2(self, arg1: str, arg2: str, /, kwd: str = ""):
        return arg1, arg2, kwd

    @staticmethod
    @deprecate_nonkeyword_arguments(version="1.0.0")
    def nonkeyword_arguments3():
        return ()

    @deprecate_nonkeyword_arguments(allowed_args=("self",), message="Pass kwd as keyword", version="1.0.0")
    def nonkeyword_arguments4(self, kwd: str):
        return kwd

    @deprecate_parameter_as_multi_positional("phases", version="1.0.0")
    def parameter_as_multi_positional(self, *phases: str):
        return phases


def test_deprecate_renamed_parameter():
    # Constructor
    d = Deprecations(new="passed")
    with pytest.warns(
        FutureWarning, match=r"Argument 'old' for Deprecations\(\) is deprecated. It has been renamed to 'new'."
    ):
        Deprecations(old="passed")  # type: ignore

    # Other methods
    assert d.renamed_parameter(new="passed") == "passed"
    with pytest.warns(
        FutureWarning,
        match=r"Argument 'old' for Deprecations.renamed_parameter\(\) is deprecated. It has been renamed to 'new'.",
    ):
        assert d.renamed_parameter(old="passed") == "passed"  # type: ignore
    with pytest.raises(
        TypeError,
        match=(
            r"Deprecations.renamed_parameter\(\) got both 'old' and 'new' as arguments; "
            r"'old' is deprecated, use 'new' instead."
        ),
    ):
        d.renamed_parameter(old="passed", new="passed")  # type: ignore
    with pytest.raises(
        TypeError, match=r"Deprecations.renamed_parameter\(\) got an unexpected keyword argument 'unrelated'"
    ):
        # unrelated parameters are not affected
        d.renamed_parameter(unrelated="passed")  # type: ignore


def test_deprecate_renamed_parameters():
    d = Deprecations("arg")
    assert d.renamed_parameters(new1="passed1", new2="passed2") == ("passed1", "passed2")
    with pytest.warns(
        FutureWarning,
        match=(
            r"Argument 'old1' for Deprecations.renamed_parameters\(\) is deprecated. It has been renamed to 'new1'."
        ),
    ):
        assert d.renamed_parameters(old1="passed1", new2="passed2") == ("passed1", "passed2")  # type: ignore
    with pytest.warns(
        FutureWarning,
        match=(
            r"Argument 'old2' for Deprecations.renamed_parameters\(\) is deprecated. It has been renamed to 'new2'."
        ),
    ):
        assert d.renamed_parameters(new1="passed1", old2="passed2") == ("passed1", "passed2")  # type: ignore


def test_deprecate_nonkeyword_arguments():
    d = Deprecations("arg")
    assert d.nonkeyword_arguments("passed1", kwd="passed2") == ("passed1", "passed2")
    with pytest.warns(
        FutureWarning,
        match=(
            r"All arguments of Deprecations.nonkeyword_arguments\(\) except for 'arg1' will be "
            r"keyword-only in the future. Use keyword arguments to silence this warning."
        ),
    ):
        assert d.nonkeyword_arguments("passed1", "passed2") == ("passed1", "passed2")

    assert d.nonkeyword_arguments2("passed1", "passed2", kwd="passed3") == ("passed1", "passed2", "passed3")
    with pytest.warns(
        FutureWarning,
        match=(
            r"All arguments of Deprecations.nonkeyword_arguments2\(\) except for 'arg1' and 'arg2' "
            r"will be keyword-only in the future. Use keyword arguments to silence this warning."
        ),
    ):
        assert d.nonkeyword_arguments2("passed1", "passed2", "passed3") == ("passed1", "passed2", "passed3")

    Deprecations.nonkeyword_arguments3()
    d.nonkeyword_arguments3()

    with pytest.warns(FutureWarning, match=r"Pass kwd as keyword"):
        assert d.nonkeyword_arguments4("passed") == "passed"


def test_deprecate_parameter_as_multi_positional():
    d = Deprecations("arg")
    assert d.parameter_as_multi_positional("a", "b", "c") == ("a", "b", "c")
    with pytest.warns(
        FutureWarning,
        match=(r"Passing 'phases' as a keyword argument is deprecated. Pass it as a positional argument instead."),
    ):
        assert d.parameter_as_multi_positional(phases=("a", "b", "c")) == ("a", "b", "c")  # type: ignore
    with pytest.warns(
        FutureWarning,
        match=(r"Passing 'phases' as a keyword argument is deprecated. Pass it as a positional argument instead."),
    ):
        assert d.parameter_as_multi_positional(phases=["a", "b", "c"]) == ("a", "b", "c")  # type: ignore
    with pytest.warns(
        FutureWarning,
        match=(r"Passing 'phases' as a keyword argument is deprecated. Pass it as a positional argument instead."),
    ):
        assert d.parameter_as_multi_positional(phases="a") == ("a",)  # type: ignore
