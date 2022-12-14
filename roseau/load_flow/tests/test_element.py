import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Line, LineCharacteristics, PowerLoad, Switch, VoltageSource


@pytest.mark.parametrize("bad_phases", ("a", "n", "ab", "an", "abn", "nabc", "acb"))
def test_only_three_phase_allowed(bad_phases):
    # Buses
    with pytest.raises(RoseauLoadFlowException) as e:
        Bus(id="bus1", phases=bad_phases)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Bus of id 'bus1' got invalid phases '{bad_phases}', allowed values are: 'abc', 'abcn'"

    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="abcn")

    # Loads
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="load1", phases=bad_phases, bus=bus1, s=[100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert (
        e.value.msg == f"PowerLoad of id 'load1' got invalid phases '{bad_phases}', allowed values are: 'abc', 'abcn'"
    )

    # Sources
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="source1", phases=bad_phases, bus=bus1, voltages=[100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert (
        e.value.msg
        == f"VoltageSource of id 'source1' got invalid phases '{bad_phases}', allowed values are: 'abc', 'abcn'"
    )

    # Lines
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(
            id="line1",
            phases=bad_phases,
            bus1=bus1,
            bus2=bus2,
            line_characteristics=LineCharacteristics("test", 10 * np.eye(4, dtype=complex)),
            length=10,
        )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Line of id 'line1' got invalid phases '{bad_phases}', allowed values are: 'abc', 'abcn'"

    # Switches
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch1", phases=bad_phases, bus1=bus1, bus2=bus2)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Switch of id 'switch1' got invalid phases '{bad_phases}', allowed values are: 'abc', 'abcn'"
