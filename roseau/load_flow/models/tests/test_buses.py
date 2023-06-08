import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow import (
    Bus,
    ElectricalNetwork,
    PotentialRef,
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

    with pytest.raises(RoseauLoadFlowException) as e:
        bus.short_circuit("a", "n")
    assert "Phase 'n' is not in the phases" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PHASE
    with pytest.raises(RoseauLoadFlowException) as e:
        bus.short_circuit("n", "a")
    assert "Phase 'n' is not in the phases" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PHASE

    assert bus._short_circuit is None
    bus.short_circuit("c", "a", "b")
    assert bus._short_circuit == ("c", "a", "b")

    bus_dict = bus.to_dict()
    bus2 = Bus.from_dict(bus_dict)
    assert bus2._short_circuit == ("c", "a", "b")

    with pytest.raises(RoseauLoadFlowException) as e:
        bus.short_circuit("a", "b")
    assert "A short circuit has already been made on bus" in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.MULTIPLE_SHORT_CIRCUITS

    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    bus = Bus("bus", phases="abcn")
    bus.short_circuit("a", "n")
    _ = VoltageSource(id="vs", bus=bus, voltages=voltages)
    _ = PotentialRef(id="pref", element=bus)
    en = ElectricalNetwork.from_element(initial_bus=bus)
    df = pd.DataFrame.from_records(
        data=[("bus", "abcn", "an")],
        columns=["bus_id", "phases", "short_circuit"],
    )
    assert_frame_equal(en.short_circuits_frame, df)
