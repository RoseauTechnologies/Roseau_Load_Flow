import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineCharacteristics, Switch, VoltageSource


def test_switch_loop():
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))

    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    bus3 = Bus("bus3", phases="abcn")

    _ = Switch("switch1", 4, bus1, bus2)
    _ = Line(id="line", n=4, bus1=bus1, bus2=bus3, line_characteristics=line_characteristics, length=10)

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch2", 4, bus1, bus2)
    assert "There is a loop of switch" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch2", 4, bus2, bus1)
    assert "There is a loop of switch" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.SWITCHES_LOOP

    _ = Switch("switch2", 4, bus2, bus3)
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch3", 4, bus1, bus3)
    assert "There is a loop of switch" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.SWITCHES_LOOP


def test_switch_connection():
    ground = Ground()
    bus1 = Bus("bus1", phases="abcn", ground=ground)
    bus2 = Bus("bus2", phases="abcn", ground=ground)
    _ = VoltageSource("vs1", phases="abcn", bus=bus1, voltages=[230 + 0j, -115 + 200j, 115 - 200j])
    _ = VoltageSource("vs2", phases="abcn", bus=bus2, voltages=[230 + 0j, -115 + 200j, 115 - 200j])
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch", 4, bus1=bus1, bus2=bus2)
    assert "are connected with the switch" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION
