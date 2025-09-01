import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, GroundConnection, Line, LineParameters, Switch, VoltageSource


def test_switch_loop():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    bus3 = Bus(id="bus3", phases="abcn")

    Switch(id="sw1", bus1=bus1, bus2=bus2, phases="abcn")
    lp = LineParameters(id="test", z_line=np.eye(4, dtype=complex))
    Line(id="ln", bus1=bus1, bus2=bus3, phases="abcn", parameters=lp, length=10)

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="sw2", bus1=bus1, bus2=bus2)
    assert e.value.msg == (
        "Connecting switch 'sw2' between buses 'bus1' and 'bus2' creates a loop with switch 'sw1'. "
        "Current flow in several switch-only branches between buses cannot be computed."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="sw3", bus1=bus2, bus2=bus1)
    assert e.value.msg == (
        "Connecting switch 'sw3' between buses 'bus2' and 'bus1' creates a loop with switch 'sw1'. "
        "Current flow in several switch-only branches between buses cannot be computed."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    sw4 = Switch(id="sw4", bus1=bus2, bus2=bus3)
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="sw5", bus1=bus1, bus2=bus3)
    assert e.value.msg == (
        "Connecting switch 'sw5' between buses 'bus1' and 'bus3' creates a loop with switches "
        "['sw1', 'sw4']. Current flow in several switch-only branches between buses cannot be "
        "computed."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    # OK if the switch is open
    Switch(id="sw6", bus1=bus1, bus2=bus2, closed=False)
    Switch(id="sw7", bus1=bus2, bus2=bus3, closed=False)
    sw8 = Switch(id="sw8", bus1=bus1, bus2=bus3, closed=False)

    # Trying to close it raises an error
    with pytest.raises(RoseauLoadFlowException) as e:
        sw8.close()
    assert e.value.msg == (
        "Closing switch 'sw8' between buses 'bus1' and 'bus3' creates a loop with switches "
        "['sw1', 'sw4']. Current flow in several switch-only branches between buses cannot be "
        "computed. Open the other switches first."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    # Opening the other switch first allows closing the switch
    sw4.open()
    sw8.close()  # OK


def test_switch_connection():
    ground = Ground("ground")
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    GroundConnection(ground=ground, element=bus1)
    GroundConnection(ground=ground, element=bus2)
    VoltageSource(id="vs1", bus=bus1, voltages=[230 + 0j, -115 + 200j, 115 - 200j], phases="abcn")
    VoltageSource(id="vs2", bus=bus2, voltages=[230 + 0j, -115 + 200j, 115 - 200j], phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch", bus1=bus1, bus2=bus2, phases="abcn")
    assert "are connected with the switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION


def test_switch_dict_roundtrip():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    sw = Switch(id="switch", bus1=bus1, bus2=bus2, closed=False)
    sw_dict = sw.to_dict(include_results=True)
    sw_dict["bus1"] = bus1
    sw_dict["bus2"] = bus2
    sw2 = Switch.from_dict(sw_dict, include_results=True)
    assert sw2.id == sw.id
    assert sw2.bus1.id == sw.bus1.id
    assert sw2.bus2.id == sw.bus2.id
    assert sw2.closed == sw.closed
