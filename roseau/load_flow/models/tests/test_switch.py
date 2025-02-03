import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineParameters, Switch, VoltageSource


def test_switch_loop():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    bus3 = Bus(id="bus3", phases="abcn")

    Switch(id="switch1", bus1=bus1, bus2=bus2, phases="abcn")
    lp = LineParameters(id="test", z_line=np.eye(4, dtype=complex))
    Line(id="line", bus1=bus1, bus2=bus3, phases="abcn", parameters=lp, length=10)

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch2", bus1=bus1, bus2=bus2, phases="abcn")
    assert "There is a loop of switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch3", bus1=bus2, bus2=bus1, phases="abcn")
    assert "There is a loop of switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    Switch(id="switch4", bus1=bus2, bus2=bus3, phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch5", bus1=bus1, bus2=bus3, phases="abcn")
    assert "There is a loop of switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP


def test_switch_connection():
    ground = Ground("ground")
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    bus1.connect_ground(ground)
    bus2.connect_ground(ground)
    VoltageSource(id="vs1", bus=bus1, voltages=[230 + 0j, -115 + 200j, 115 - 200j], phases="abcn")
    VoltageSource(id="vs2", bus=bus2, voltages=[230 + 0j, -115 + 200j, 115 - 200j], phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch", bus1=bus1, bus2=bus2, phases="abcn")
    assert "are connected with the switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION
