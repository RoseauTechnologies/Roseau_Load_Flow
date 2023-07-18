import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils.types import ConductorType, InsulationType, LineModel, LineType

TYPES = [
    ConductorType,
    InsulationType,
    LineModel,
    LineType,
]
TYPES_IDS = [x.__name__ for x in TYPES]


@pytest.mark.parametrize(scope="module", argnames="t", argvalues=TYPES, ids=TYPES_IDS)
def test_types_basic(t):
    for x in t:
        assert t.from_string(str(x)) == x
        assert "." not in str(x)


def test_line_type():
    with pytest.raises(RoseauLoadFlowException) as e:
        LineType.from_string("")
    assert "cannot be converted into a LineType" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LINE_TYPE
    with pytest.raises(RoseauLoadFlowException) as e:
        LineType.from_string("nan")
    assert "cannot be converted into a LineType" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LINE_TYPE

    assert LineType.from_string("Aérien") == LineType.OVERHEAD
    assert LineType.from_string("Aerien") == LineType.OVERHEAD
    assert LineType.from_string("galerie") == LineType.OVERHEAD
    assert LineType.from_string("Souterrain") == LineType.UNDERGROUND
    assert LineType.from_string("torsadé") == LineType.TWISTED
    assert LineType.from_string("Torsade") == LineType.TWISTED


def test_insulation_type():
    assert InsulationType.from_string("") == InsulationType.UNKNOWN
    assert InsulationType.from_string("nan") == InsulationType.UNKNOWN


def test_conductor_type():
    with pytest.raises(RoseauLoadFlowException) as e:
        ConductorType.from_string("")
    assert "cannot be converted into a ConductorType" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE
    with pytest.raises(RoseauLoadFlowException) as e:
        ConductorType.from_string("nan")
    assert "cannot be converted into a ConductorType" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE


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
