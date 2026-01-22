import pytest

from roseau.load_flow import Insulator, Material


def test_renamed_classes():
    with pytest.warns(FutureWarning, match="The `ConductorType` class is deprecated. Use `Material` instead."):
        from roseau.load_flow import ConductorType
    assert ConductorType is Material
    with pytest.warns(FutureWarning, match="The `InsulatorType` class is deprecated. Use `Insulator` instead."):
        from roseau.load_flow import InsulatorType
    assert InsulatorType is Insulator


def test_non_existent_name():
    from roseau import load_flow

    with pytest.raises(AttributeError, match=f"module '{load_flow.__name__}' has no attribute 'non_existent_name'"):
        _ = load_flow.non_existent_name
