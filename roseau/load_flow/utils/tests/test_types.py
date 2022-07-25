import pytest

from roseau.load_flow.utils.exceptions import ThundersValueError
from roseau.load_flow.utils.types import ConductorType, IsolationType, LineModel, LineType, TransformerType

TYPES = [
    ConductorType,
    IsolationType,
    LineModel,
    LineType,
    TransformerType,
]
TYPES_IDS = [x.__name__ for x in TYPES]


@pytest.mark.parametrize(scope="module", argnames="t", argvalues=TYPES, ids=TYPES_IDS)
def test_types_basic(t):
    for x in t:
        assert t.from_string(str(x)) == x
        assert "." not in str(x)


def test_line_type():
    assert LineType.from_string("") == LineType.UNKNOWN
    assert LineType.from_string("nan") == LineType.UNKNOWN
    assert LineType.from_string("Aérien") == LineType.OVERHEAD
    assert LineType.from_string("Aerien") == LineType.OVERHEAD
    assert LineType.from_string("galerie") == LineType.OVERHEAD
    assert LineType.from_string("Souterrain") == LineType.UNDERGROUND
    assert LineType.from_string("torsadé") == LineType.TWISTED
    assert LineType.from_string("Torsade") == LineType.TWISTED


def test_isolation_type():
    assert IsolationType.from_string("") == IsolationType.UNKNOWN
    assert IsolationType.from_string("nan") == IsolationType.UNKNOWN


def test_conductor_type():
    assert ConductorType.from_string("") == ConductorType.UNKNOWN
    assert ConductorType.from_string("nan") == ConductorType.UNKNOWN


def test_transformer_type():
    valid_windings = ("y", "yn", "z", "zn", "d")
    valid_phase_displacements = (0, 5, 6, 11)
    valid_types = {"dd", "yy", "yny", "yyn", "ynyn", "dz", "dzn", "dy", "dyn", "yd", "ynd", "yz", "ynz", "yzn", "ynzn"}
    valid_full_types = {
        "dd0",
        "dd6",
        "yy0",
        "yy6",
        "yny0",
        "yny6",
        "yyn0",
        "yyn6",
        "ynyn0",
        "ynyn6",
        "dz0",
        "dz6",
        "dzn0",
        "dzn6",
        "dy5",
        "dy11",
        "dyn5",
        "dyn11",
        "yd5",
        "yd11",
        "ynd5",
        "ynd11",
        "yz5",
        "yz11",
        "ynz5",
        "ynz11",
        "yzn5",
        "yzn11",
        "ynzn5",
        "ynzn11",
    }

    for winding1 in valid_windings:
        for winding2 in valid_windings:
            t = f"{winding1}{winding2}"
            if t in valid_types:
                assert not TransformerType.validate_windings(t)
                w1, w2, p = TransformerType.extract_windings(t)
                assert w1 == winding1.upper()
                assert w2 == winding2
                assert p is None
                for phase_displacement in valid_phase_displacements:
                    t = f"{winding1}{winding2}{phase_displacement}"
                    if t in valid_full_types:
                        assert TransformerType.validate_windings(t)
                        w1, w2, p = TransformerType.extract_windings(t)
                        assert w1 == winding1.upper()
                        assert w2 == winding2
                        assert p == phase_displacement
                    else:
                        assert not TransformerType.validate_windings(t)
                        with pytest.raises(ThundersValueError):
                            TransformerType.extract_windings(t)
            else:
                assert not TransformerType.validate_windings(t)
                with pytest.raises(ThundersValueError):
                    TransformerType.extract_windings(t)

    for x in TransformerType:
        s = str(x)
        w1, w2, phase_displacement = TransformerType.extract_windings(s)
        assert f"{w1}{w2}" == s
        assert phase_displacement is None


def test_line_model():
    assert LineModel.from_string("") == LineModel.UNKNOWN
    assert LineModel.from_string("nan") == LineModel.UNKNOWN

    # With neutral
    with_neutral = LineModel.with_neutral()
    without_neutral = LineModel.without_neutral()
    for x in LineModel:
        if x == LineModel.UNKNOWN:
            assert x not in without_neutral
            assert x not in with_neutral
            continue
        if x in (LineModel.LV_EXACT, LineModel.ZY_NEUTRAL, LineModel.Z_NEUTRAL, LineModel.SYM_NEUTRAL):
            assert x in with_neutral
            assert x not in without_neutral
        else:
            assert x not in with_neutral
            assert x in without_neutral

    # With Shunt
    with_shunt = LineModel.with_shunt()
    without_shunt = LineModel.without_shunt()
    for x in LineModel:
        if x == LineModel.UNKNOWN:
            assert x not in without_shunt
            assert x not in with_shunt
            continue
        if x in (LineModel.LV_EXACT, LineModel.SYM, LineModel.SYM_NEUTRAL, LineModel.ZY, LineModel.ZY_NEUTRAL):
            assert x in with_shunt
            assert x not in without_shunt
        else:
            assert x not in with_shunt
            assert x in without_shunt
