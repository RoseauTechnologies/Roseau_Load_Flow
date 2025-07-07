import pytest

from roseau.load_flow_single.models import (
    AbstractBranch,
    AbstractConnectable,
    AbstractDisconnectable,
    AbstractLoad,
    AbstractTerminal,
    Bus,
    Element,
)


def test_abstract_classes():
    with pytest.raises(TypeError, match="Can't instantiate abstract class Element"):
        Element("element_id")  # type: ignore
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractBranch"):
        AbstractBranch(id="branch_id", bus1=bus1, bus2=bus2, n=2)  # type: ignore
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractTerminal"):
        AbstractTerminal(id="terminal_id")  # type: ignore
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractConnectable"):
        AbstractConnectable(id="connectable_id", bus=bus1)  # type: ignore
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractDisconnectable"):
        AbstractDisconnectable(id="disconnectable_id", bus=bus1)  # type: ignore
    with pytest.raises(TypeError, match="Can't instantiate abstract class AbstractLoad"):
        AbstractLoad(id="load_id", bus=bus1)  # type: ignore
