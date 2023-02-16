import numpy as np
import pytest
from pint import DimensionalityError

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Line, LineParameters
from roseau.load_flow.units import Q_


def test_lines_length():
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus1", phases="abcn")
    lp = LineParameters("lp", z_line=np.eye(4, dtype=complex))

    # Negative value for length in the constructor
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=-5)
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(-5, "m"))
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # Test on the length setter
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "m"))
    with pytest.raises(RoseauLoadFlowException) as e:
        line.length = -6.5
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        line.length = Q_(-6.5, "cm")
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE


def test_lines_units():
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus1", phases="abcn")
    lp = LineParameters("lp", z_line=np.eye(4, dtype=complex))

    # Good unit constructor
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "km"))
    assert np.isclose(line._length, 5)

    # Good unit setter
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    assert np.allclose(line._length, 5)
    line.length = Q_(6.5, "m")
    assert np.isclose(line._length, 6.5e-3)

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "A"))

    # Bad unit setter
    line = Line("line", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        line.length = Q_(6.5, "A")
