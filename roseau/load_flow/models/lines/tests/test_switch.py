import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineCharacteristics, Switch


def test_switch_loop():
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))

    bus1 = Bus("bus1", 4)
    bus2 = Bus("bus2", 4)
    bus3 = Bus("bus3", 4)

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
    vs1 = Bus(id="source1", n=4, ground=ground, source_voltages=[230 + 0j, -115 + 200j, 115 - 200j])
    vs2 = Bus(id="source2", n=4, ground=ground, source_voltages=[230 + 0j, -115 + 200j, 115 - 200j])
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch", 4, vs1, vs2)
    assert "are connected with the switch" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SOURCES_CONNECTION
