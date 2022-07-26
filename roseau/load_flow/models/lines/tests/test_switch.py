import numpy as np
import pytest

from roseau.load_flow import Bus, Ground, LineCharacteristics, SimplifiedLine, Switch, VoltageSource
from roseau.load_flow.utils import ThundersValueError


def test_switch_loop():
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))

    bus1 = Bus("bus1", 4)
    bus2 = Bus("bus2", 4)
    bus3 = Bus("bus3", 4)

    _ = Switch("switch1", 4, bus1, bus2)
    _ = SimplifiedLine(id="line", n=4, bus1=bus1, bus2=bus3, line_characteristics=line_characteristics, length=10)

    with pytest.raises(ThundersValueError) as e:
        Switch("switch2", 4, bus1, bus2)
    assert "There is a loop of switch" in e.value.args[0]

    with pytest.raises(ThundersValueError) as e:
        Switch("switch2", 4, bus2, bus1)
    assert "There is a loop of switch" in e.value.args[0]

    _ = Switch("switch2", 4, bus2, bus3)
    with pytest.raises(ThundersValueError) as e:
        Switch("switch3", 4, bus1, bus3)
    assert "There is a loop of switch" in e.value.args[0]


def test_switch_connection():
    ground = Ground()
    vs1 = VoltageSource(id="source1", n=4, ground=ground, voltages=[230 + 0j, -115 + 200j, 115 - 200j])
    vs2 = VoltageSource(id="source2", n=4, ground=ground, voltages=[230 + 0j, -115 + 200j, 115 - 200j])
    with pytest.raises(ThundersValueError) as e:
        Switch("switch", 4, vs1, vs2)
    assert "are connected with the switch" in e.value.args[0]
