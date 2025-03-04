import warnings

import pytest

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single.models import Bus, Line, LineParameters, Switch, VoltageSource


def test_switch_loop():
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    bus3 = Bus(id="bus3")

    Switch(id="switch1", bus1=bus1, bus2=bus2)
    lp = LineParameters(id="test", z_line=1.0)
    Line(id="line", bus1=bus1, bus2=bus3, parameters=lp, length=10)

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch2", bus1=bus1, bus2=bus2)
    assert e.value.msg == (
        "Connecting switch 'switch2' between buses 'bus1' and 'bus2' creates a switch loop. Current "
        "flow in several switch-only branches between buses cannot be computed."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch3", bus1=bus2, bus2=bus1)
    assert "Connecting switch 'switch3' between buses 'bus2' and 'bus1' creates a switch loop." in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    Switch(id="switch4", bus1=bus2, bus2=bus3)
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch5", bus1=bus1, bus2=bus3)
    assert "Connecting switch 'switch5' between buses 'bus1' and 'bus3' creates a switch loop." in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP


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
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Switch(id="sw good", bus1=bus1, bus2=bus2)  # OK
        Switch(id="sw good2", bus1=bus1, bus2=bus3)  # OK
    with pytest.warns(
        UserWarning, match=r"Switch 'sw bad' connects buses with different nominal voltages: 240.0 V and 400.0 V."
    ):
        Switch(id="sw bad", bus1=bus1, bus2=bus4)
