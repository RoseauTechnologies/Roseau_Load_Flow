"""Roseau load flow testing utilities."""

import numbers

import numpy as np


def assert_json_close(obj1: object, obj2: object, *, rtol=1e-7, atol=0, prefix: str = "") -> None:  # noqa: C901
    """Assert that two JSON data structures are close, i.e same structure and all close values.

    This function is used to compare two JSON data structures, which can be dictionaries, lists,
    strings, booleans, or numbers.

    The comparison is done recursively, and the function raises an AssertionError if the two
    structures are different. The comparison is done with a tolerance for floating point numbers.
    """
    __tracebackhide__ = True
    this_prefix = f"{prefix!r}: " if prefix else ""

    if obj1 is None:
        assert obj2 is None, f"{this_prefix}objects types are different: {type(obj1)} != {type(obj2)}"
        return
    elif isinstance(obj1, str):
        if not isinstance(obj2, str):
            raise AssertionError(f"{this_prefix}objects types are different: {type(obj1)} != {type(obj2)}")
        assert obj1 == obj2, f"{this_prefix}strings are different: {obj1} != {obj2}"
    elif isinstance(obj1, (bool, np.bool_)):
        if not isinstance(obj2, (bool, np.bool_)):
            raise AssertionError(f"{this_prefix}objects types are different: {type(obj1)} != {type(obj2)}")
        assert obj1 == obj2, f"{this_prefix}booleans are different: {obj1} != {obj2}"
    elif isinstance(obj1, dict):
        if not isinstance(obj2, dict):
            raise AssertionError(f"{this_prefix}objects types are different: {type(obj1)} != {type(obj2)}")
        if obj1.keys() != obj2.keys():
            raise AssertionError(f"{this_prefix}dictionaries keys are different: {obj1.keys()} != {obj2.keys()}")
        for key in obj1:
            assert_json_close(
                obj1[key], obj2[key], rtol=rtol, atol=atol, prefix=f"{prefix}.{key}" if prefix else f"{key}"
            )
    elif isinstance(obj1, (tuple, list)):
        if not isinstance(obj2, (tuple, list)):
            raise AssertionError(f"{this_prefix}objects types are different: {type(obj1)} != {type(obj2)}")
        if len(obj1) != len(obj2):
            raise AssertionError(f"{this_prefix}lists have different sizes: {len(obj1)} != {len(obj2)}")
        for i, (v1, v2) in enumerate(zip(obj1, obj2, strict=True)):
            assert_json_close(v1, v2, rtol=rtol, atol=atol, prefix=f"{prefix}[{i}]")
    elif isinstance(obj1, numbers.Number):
        if not isinstance(obj2, numbers.Number):
            raise AssertionError(f"{this_prefix}objects types are different: {type(obj1)} != {type(obj2)}")
        if not np.isclose(obj1, obj2, rtol=rtol, atol=atol).all():  # type: ignore
            raise AssertionError(f"{this_prefix}numbers are different: {obj1} != {obj2}")
    else:
        raise NotImplementedError(f"{this_prefix}unsupported type: {type(obj1)}")
