import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineParameters, Switch, VoltageSource


def test_switch_loop():
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    bus3 = Bus("bus3", phases="abcn")

    Switch("switch1", bus1, bus2, phases="abcn")
    lp = LineParameters("test", z_line=np.eye(4, dtype=complex))
    Line(id="line", bus1=bus1, bus2=bus3, phases="abcn", parameters=lp, length=10)

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch2", bus1, bus2, phases="abcn")
    assert "There is a loop of switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch2", bus2, bus1, phases="abcn")
    assert "There is a loop of switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    Switch("switch2", bus2, bus3, phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch3", bus1, bus3, phases="abcn")
    assert "There is a loop of switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.SWITCHES_LOOP


def test_switch_connection():
    ground = Ground("ground")
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    ground.connect(bus1)
    ground.connect(bus2)
    VoltageSource("vs1", bus1, voltages=[230 + 0j, -115 + 200j, 115 - 200j], phases="abcn")
    VoltageSource("vs2", bus2, voltages=[230 + 0j, -115 + 200j, 115 - 200j], phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch", bus1, bus2, phases="abcn")
    assert "are connected with the switch" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION
