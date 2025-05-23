import pytest

from roseau.load_flow.constants import DELTA_P, EPSILON_R, MU_R, RHO, TAN_D
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
    with pytest.raises(ValueError, match=r"is not a valid LineType"):
        LineType("")
    with pytest.raises(ValueError, match=r"is not a valid LineType"):
        LineType("nan")

    # spellchecker:off
    assert LineType("oVeRhEaD") == LineType.OVERHEAD
    assert LineType("o") == LineType.OVERHEAD
    assert LineType("uNdErGrOuNd") == LineType.UNDERGROUND
    assert LineType("u") == LineType.UNDERGROUND
    assert LineType("tWiStEd") == LineType.TWISTED
    assert LineType("T") == LineType.TWISTED
    # spellchecker:on


def test_insulator():
    assert Insulator("pex") == Insulator.XLPE


def test_material():
    with pytest.raises(ValueError, match=r"is not a valid Material"):
        Material("")
    with pytest.raises(ValueError, match=r"is not a valid Material"):
        Material("nan")
