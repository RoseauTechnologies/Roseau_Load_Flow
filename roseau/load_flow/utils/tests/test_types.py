import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils.types import ConductorType, InsulatorType, LineType

TYPES = [ConductorType, InsulatorType, LineType]
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


def test_insulator_type():
    assert InsulatorType.from_string("") == InsulatorType.UNKNOWN
    assert InsulatorType.from_string("nan") == InsulatorType.UNKNOWN


def test_conductor_type():
    with pytest.raises(RoseauLoadFlowException) as e:
        ConductorType.from_string("")
    assert "cannot be converted into a ConductorType" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE
    with pytest.raises(RoseauLoadFlowException) as e:
        ConductorType.from_string("nan")
    assert "cannot be converted into a ConductorType" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE
