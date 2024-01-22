import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils.types import ConductorType, InsulatorType, LineType

TYPES = [ConductorType, InsulatorType, LineType]
TYPES_IDS = [x.__name__ for x in TYPES]


@pytest.mark.parametrize(scope="module", argnames="t", argvalues=TYPES, ids=TYPES_IDS)
def test_types_basic(t):
    for x in t:
        assert t(str(x)) == x
        assert "." not in str(x)


def test_line_type():
    with pytest.raises(RoseauLoadFlowException) as e:
        LineType("")
    assert "cannot be converted into a LineType" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_TYPE
    with pytest.raises(RoseauLoadFlowException) as e:
        LineType("nan")
    assert "cannot be converted into a LineType" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_TYPE

    assert LineType("oVeRhEaD") == LineType.OVERHEAD
    assert LineType("o") == LineType.OVERHEAD
    assert LineType("uNdErGrOuNd") == LineType.UNDERGROUND
    assert LineType("u") == LineType.UNDERGROUND
    assert LineType("tWiStEd") == LineType.TWISTED
    assert LineType("T") == LineType.TWISTED


def test_insulator_type():
    assert InsulatorType("") == InsulatorType.UNKNOWN
    assert InsulatorType("nan") == InsulatorType.UNKNOWN
    assert InsulatorType("pex") == InsulatorType.XLPE


def test_conductor_type():
    with pytest.raises(RoseauLoadFlowException) as e:
        ConductorType("")
    assert "cannot be converted into a ConductorType" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE
    with pytest.raises(RoseauLoadFlowException) as e:
        ConductorType("nan")
    assert "cannot be converted into a ConductorType" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONDUCTOR_TYPE
