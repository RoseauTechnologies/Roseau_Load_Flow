import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    AbstractBranch,
    AbstractLoad,
    Bus,
    CurrentLoad,
    Element,
    Line,
    LineParameters,
    PowerLoad,
    Switch,
)


def test_abstract_classes():
    with pytest.raises(TypeError, match="Can't instantiate abstract class Element"):
        Element("element_id")
    bus1 = Bus("bus1", phases="an")
    bus2 = Bus("bus2", phases="an")
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractBranch"):
        AbstractBranch("branch_id", bus1=bus1, bus2=bus2, phases1="an", phases2="an")
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractLoad"):
        AbstractLoad("load_id", bus=bus1, phases="an")


def test_invalid_element_override():
    bus1 = Bus("bus1", phases="an")
    bus2 = Bus("bus2", phases="an")
    PowerLoad("load", bus2, powers=[1000])

    # Different load type, same ID
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus2, currents=[3])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "A Load of ID 'load' is already connected to Bus 'bus2'."

    lp = LineParameters("lp", z_line=np.eye(2, dtype=complex))
    Line("branch", bus1, bus2, parameters=lp, length=1)

    # Different branch class, same ID
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("branch", bus1, bus2)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "A Branch of ID 'branch' is already connected to Bus 'bus1'."

    CurrentLoad("load", bus1, currents=[3])
