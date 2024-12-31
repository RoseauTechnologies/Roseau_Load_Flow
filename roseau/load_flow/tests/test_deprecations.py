import importlib

import pytest

from roseau.load_flow import Insulator, Material, constants, converters, utils


def test_moved_names():
    # utils -> constants
    for name in (
        "ALPHA",
        "ALPHA2",
        "PI",
        "MU_0",
        "EPSILON_0",
        "F",
        "OMEGA",
        "RHO",
        "MU_R",
        "DELTA_P",
        "TAN_D",
        "EPSILON_R",
    ):
        with pytest.warns(
            FutureWarning,
            match=f"Importing {name} from 'roseau.load_flow.utils' is deprecated. Use 'rlf.constants.{name}' instead.",
        ):
            getattr(utils, name)
    # utils -> sym
    for name in ("PositiveSequence", "NegativeSequence", "ZeroSequence"):
        with pytest.warns(
            FutureWarning,
            match=f"Importing {name} from 'roseau.load_flow.utils' is deprecated. Use 'rlf.sym.{name}' instead.",
        ):
            getattr(utils, name)
    # utils -> types
    for name in ("LineType", "Material", "Insulator"):
        with pytest.warns(
            FutureWarning,
            match=f"Importing {name} from 'roseau.load_flow.utils' is deprecated. Use 'rlf.types.{name}' instead.",
        ):
            getattr(utils, name)
    # constants -> sym
    for name in ("PositiveSequence", "NegativeSequence", "ZeroSequence"):
        with pytest.warns(
            FutureWarning,
            match=f"'rlf.constants.{name}' is deprecated. Use 'rlf.sym.{name}' instead.",
        ):
            getattr(constants, name)
    # converters -> sym
    for name in ("phasor_to_sym", "sym_to_phasor", "series_phasor_to_sym"):
        with pytest.warns(
            FutureWarning,
            match=f"'rlf.converters.{name}' is deprecated. Use 'rlf.sym.{name}' instead.",
        ):
            getattr(converters, name)


def test_renamed_classes():
    with pytest.warns(FutureWarning, match="The `ConductorType` class is deprecated. Use `Material` instead."):
        from roseau.load_flow import ConductorType
    assert ConductorType is Material
    with pytest.warns(FutureWarning, match="The `InsulatorType` class is deprecated. Use `Insulator` instead."):
        from roseau.load_flow import InsulatorType
    assert InsulatorType is Insulator


def test_non_existent_name():
    from roseau import load_flow

    for mod in (utils, constants, converters, load_flow):
        with pytest.raises(AttributeError, match=f"module '{mod.__name__}' has no attribute 'non_existent_name'"):
            _ = mod.non_existent_name


def test_deprecated_utils_modules():
    with pytest.warns(
        FutureWarning,
        match="Module 'roseau.load_flow.utils.constants' is deprecated. Use 'rlf.constants' directly instead.",
    ):
        importlib.import_module("roseau.load_flow.utils.constants")
    with pytest.warns(
        FutureWarning,
        match="Module 'roseau.load_flow.utils.types' is deprecated. Use 'rlf.types' directly instead.",
    ):
        importlib.import_module("roseau.load_flow.utils.types")
