import warnings

import pytest

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single.models import Bus, Line, LineParameters, Switch, VoltageSource


def test_switch_loop():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    bus3 = Bus(id="bus3")

    Switch(id="sw1", bus1=bus1, bus2=bus2)
    lp = LineParameters(id="test", z_line=1.0)
    Line(id="line", bus1=bus1, bus2=bus3, parameters=lp, length=10)

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
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    VoltageSource(id="vs1", bus=bus1, voltage=400 + 0j)
    VoltageSource(id="vs2", bus=bus2, voltage=400 + 0j)
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch", bus1=bus1, bus2=bus2)
    assert e.value.msg == (
        "Connecting switch 'switch' between buses 'bus1' and 'bus2' that both have a voltage source is not allowed."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION


def test_different_voltage_levels():
    bus1 = Bus(id="bus1", nominal_voltage=240)
    bus2 = Bus(id="bus2", nominal_voltage=240)
    bus3 = Bus(id="bus3")
    bus4 = Bus(id="bus4", nominal_voltage=400)
    with warnings.catch_warnings(action="error"):
        Switch(id="sw good", bus1=bus1, bus2=bus2)  # OK
        Switch(id="sw good2", bus1=bus1, bus2=bus3)  # OK
    with pytest.warns(
        UserWarning, match=r"Switch 'sw bad' connects buses with different nominal voltages: 240.0 V and 400.0 V."
    ):
        Switch(id="sw bad", bus1=bus1, bus2=bus4)
