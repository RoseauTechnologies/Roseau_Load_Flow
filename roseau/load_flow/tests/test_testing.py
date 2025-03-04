import re
import textwrap

import numpy as np
import pytest

from roseau.load_flow.testing import assert_json_close


def test_assert_json_close():
    assert_json_close({"a": 1}, {"a": 1})
    assert_json_close({"a": 1}, {"a": 1.0})
    assert_json_close({"a": 1}, {"a": 1.0000001})
    assert_json_close({"a": 1}, {"a": 1.000001}, rtol=1e-5)
    assert_json_close({"a": "1"}, {"a": "1"})
    assert_json_close({"a": 1}, {"a": np.float64(1.0)})
    assert_json_close({"a": True}, {"a": np.True_})
    assert_json_close({"a": [0, 1]}, {"a": (0, 1)})

    # Simple failure
    with pytest.raises(AssertionError, match=re.escape("'a': numbers are different: 1 != 2")):
        assert_json_close({"a": 1}, {"a": 2})

    # Simple failure due to tolerance
    with pytest.raises(AssertionError, match=re.escape("'a': numbers are different: 1 != 1.000001")):
        assert_json_close({"a": 1}, {"a": 1.000001}, rtol=1e-10)

    # Nested failure
    with pytest.raises(AssertionError, match=re.escape("'a.b': numbers are different: 1 != 2")):
        assert_json_close({"a": {"b": 1}}, {"a": {"b": 2}})
    with pytest.raises(AssertionError, match=re.escape("'a.b[0].c[2]': numbers are different: 3 != 4")):
        assert_json_close({"a": {"b": [{"c": [1, 2, 3]}]}}, {"a": {"b": [{"c": [1, 2, 4]}]}})

    # Different types
    with pytest.raises(
        AssertionError, match=re.escape("'a': objects types are different: <class 'int'> != <class 'str'")
    ):
        assert_json_close({"a": 1}, {"a": "1"})
    with pytest.raises(
        AssertionError, match=re.escape("'a': objects types are different: <class 'str'> != <class 'int'")
    ):
        assert_json_close({"a": "1"}, {"a": 1})
    with pytest.raises(
        AssertionError, match=re.escape("'a': objects types are different: <class 'NoneType'> != <class 'int'")
    ):
        assert_json_close({"a": None}, {"a": 1})
    with pytest.raises(
        AssertionError, match=re.escape("'a': objects types are different: <class 'bool'> != <class 'int'")
    ):
        assert_json_close({"a": True}, {"a": 1})
    with pytest.raises(AssertionError, match=re.escape("objects types are different: <class 'dict'> != <class 'int'")):
        assert_json_close({"a": 0}, 0)
    with pytest.raises(AssertionError, match=re.escape("objects types are different: <class 'list'> != <class 'int'")):
        assert_json_close([0], 0)

    # Missing keys
    with pytest.raises(
        AssertionError,
        match=r"^"
        + re.escape(
            textwrap.dedent(
                """\
                dictionaries keys are different: dict_keys(['a']) != dict_keys(['b'])
                Keys in obj1 not in obj2: {'a'}
                Keys in obj2 not in obj1: {'b'}"""
            )
        )
        + r"$",
    ):
        assert_json_close({"a": 1}, {"b": 1})
    with pytest.raises(
        AssertionError,
        match=r"^"
        + re.escape(
            textwrap.dedent(
                """\
                dictionaries keys are different: dict_keys(['a']) != dict_keys([])
                Keys in obj1 not in obj2: {'a'}"""
            )
        )
        + r"$",
    ):
        assert_json_close({"a": 1}, {})
    with pytest.raises(
        AssertionError,
        match=r"^"
        + re.escape(
            textwrap.dedent(
                """\
                dictionaries keys are different: dict_keys([]) != dict_keys(['b'])
                Keys in obj2 not in obj1: {'b'}"""
            )
        )
        + r"$",
    ):
        assert_json_close({}, {"b": 1})
