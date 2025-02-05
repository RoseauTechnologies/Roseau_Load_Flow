import pytest

from roseau.load_flow.utils.helpers import CaseInsensitiveStrEnum, count_repr, one_or_more_repr


def test_count_repr():
    assert count_repr(["a"], "bus", "buses") == "1 bus"
    assert count_repr(["a", "b"], "bus", "buses") == "2 buses"
    assert count_repr(["a", "b"], "load") == "2 loads"


def test_one_or_more_repr():
    assert one_or_more_repr(["a"], "phase") == ("phase 'a'", "is")
    assert one_or_more_repr(["a", "b"], "phase") == ("phases ['a', 'b']", "are")
    assert one_or_more_repr("ab", "phase") == ("phases 'ab'", "are")
    assert one_or_more_repr(["a", "b"], "Bus", "Buses") == ("Buses ['a', 'b']", "are")


def test_case_insensitive_str_enum():
    class TestEnum(CaseInsensitiveStrEnum):
        AA = "Aa"
        BB = "Bb"

    assert issubclass(TestEnum, str)
    assert isinstance(TestEnum.AA, str)
    assert TestEnum("aa") == TestEnum.AA
    assert TestEnum("Aa") == TestEnum.AA
    assert TestEnum("AA") == TestEnum.AA
    assert TestEnum("bb") == TestEnum.BB
    assert TestEnum["AA"] == TestEnum.AA

    with pytest.raises(ValueError, match=r"'Cc' is not a valid .*TestEnum"):
        TestEnum("Cc")
