import pytest

from roseau.load_flow.constants import DELTA_P, EPSILON_R, MU_R, RHO, TAN_D
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.types import Insulator, LineType, Material

TYPES = [Material, Insulator, LineType]
TYPES_IDS = [x.__name__ for x in TYPES]


def test_types_of_constants():
    for x in Material:
        assert x in MU_R
        assert x in RHO
        assert x in DELTA_P

    for x in Insulator:
        assert x in TAN_D
        assert x in EPSILON_R


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


def test_insulator():
    assert Insulator("pex") == Insulator.XLPE


def test_material():
    with pytest.raises(RoseauLoadFlowException) as e:
        Material("")
    assert "cannot be converted into a Material" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MATERIAL
    with pytest.raises(RoseauLoadFlowException) as e:
        Material("nan")
    assert "cannot be converted into a Material" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MATERIAL
