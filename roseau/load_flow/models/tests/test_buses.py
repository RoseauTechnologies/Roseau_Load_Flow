import numpy as np
import pytest

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    Ground,
    PotentialRef,
    PowerLoad,
    RoseauLoadFlowException,
    RoseauLoadFlowExceptionCode,
    VoltageSource,
)


def test_bus_potentials_of_phases():
    bus = Bus("bus", phases="abcn")
    bus._res_potentials = [1, 2, 3, 4]

    assert np.allclose(bus._get_potentials_of("abcn", warning=False), [1, 2, 3, 4])
    assert isinstance(bus._get_potentials_of("abcn", warning=False), np.ndarray)

    assert np.allclose(bus._get_potentials_of("abc", warning=False), [1, 2, 3])
    assert np.allclose(bus._get_potentials_of("ca", warning=False), [3, 1])
    assert np.allclose(bus._get_potentials_of("n", warning=False), [4])
    assert np.allclose(bus._get_potentials_of("", warning=False), [])


def test_short_circuit():
    bus = Bus("bus", phases="abc")

    # Bad parameters
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a", "n")
    assert "Phase 'n' is not in the phases" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("n", "a")
    assert "Phase 'n' is not in the phases" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a", "a")
    assert "some phases are duplicated" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a")
    assert "at least two phases (or a phase and a ground) should be given" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PHASE

    assert not bus._short_circuits
    bus.add_short_circuit("c", "a", "b")
    assert bus._short_circuits[0]["phases"] == ["c", "a", "b"]
    assert bus._short_circuits[0]["ground"] is None

    # Dict methods
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    _ = VoltageSource("vs", bus=bus, voltages=voltages)
    _ = PotentialRef("pref", element=bus)
    en = ElectricalNetwork.from_element(bus)
    en2 = ElectricalNetwork.from_dict(en.to_dict())
    assert en2.buses["bus"]._short_circuits[0]["phases"] == ["c", "a", "b"]
    assert en2.buses["bus"]._short_circuits[0]["ground"] is None

    ground = Ground("ground")
    bus.add_short_circuit("a", ground=ground)  # ok
    assert len(bus.short_circuits) == 2

    # With power load
    bus.clear_short_circuits()
    assert not bus.short_circuits
    PowerLoad(id="load", bus=bus, powers=[10, 10, 10])
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.add_short_circuit("a", "b")
    assert "is already connected on bus" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT
