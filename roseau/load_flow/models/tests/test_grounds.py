import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    Ground,
    PotentialRef,
    PowerLoad,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.testing import assert_json_close


def test_ground_connections():
    ground1 = Ground("ground1")
    ground2 = Ground("ground2")
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    bus3 = Bus("bus3", phases="abc")

    # Default phase is n, if available
    bus1.connect_ground(ground1)
    assert ground1.connections == [{"element": bus1, "phase": "n", "side": ""}]
    with pytest.raises(RoseauLoadFlowException) as e:
        bus3.connect_ground(ground1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in the phases of bus 'bus3'."

    # Cannot connect to the same phase
    with pytest.raises(RoseauLoadFlowException) as e:
        bus1.connect_ground(ground1, phase="n")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Ground 'ground1' is already connected to phase 'n' of bus 'bus1'."

    # Connect to a specific phase
    bus3.connect_ground(ground1, phase="a")
    assert {"element": bus3, "phase": "a", "side": ""} in ground1.connections

    # Connect to another phase raises an error by default
    with pytest.raises(RoseauLoadFlowException) as e:
        bus3.connect_ground(ground1, phase="b")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_GROUND_ID
    assert e.value.msg == "Ground 'ground1' is already connected to phase 'a' of bus 'bus3'."
    assert {"element": bus3, "phase": "b", "side": ""} not in ground1.connections

    # But the error can turn into a warning
    with pytest.warns(UserWarning, match=r"Ground 'ground1' is already connected to phase 'a' of bus 'bus3'."):
        bus3.connect_ground(ground1, phase="b", on_connected="warn")
    assert {"element": bus3, "phase": "b", "side": ""} in ground1.connections

    # Or totally ignored
    bus3.connect_ground(ground1, phase="c", on_connected="ignore")
    assert {"element": bus3, "phase": "c", "side": ""} in ground1.connections

    # Connecting another ground to the same phase is fine
    bus3.connect_ground(ground2, phase="c")
    assert {"element": bus3, "phase": "c", "side": ""} in ground2.connections

    # Loads and sources can also be connected to grounds
    load = PowerLoad("load", bus=bus2, phases="abcn", powers=3e3, connect_neutral=False)
    source = VoltageSource("source", bus=bus2, phases="abcn", voltages=230)
    load.connect_ground(ground1, phase="n")  # Connect to the floating neutral
    assert {"element": load, "phase": "n", "side": ""} in ground1.connections
    source.connect_ground(ground1, phase="n")
    assert {"element": source, "phase": "n", "side": ""} in ground1.connections

    # Transformers can also be connected to grounds
    tp = TransformerParameters("tp", vg="Yzn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    tr = Transformer("tr", bus_hv=bus1, bus_lv=bus2, parameters=tp)
    tr.connect_ground_lv(ground1, phase="n")
    assert {"element": tr, "phase": "n", "side": "LV"} in ground1.connections
    with pytest.raises(RoseauLoadFlowException) as e:
        tr.connect_ground_hv(ground1, phase="n")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in the HV phases of transformer 'tr'."
    tr.connect_ground_hv(ground1, phase="a")
    assert {"element": tr, "phase": "a", "side": "HV"} in ground1.connections


def test_ground_to_from_dict_roundtrip():
    ground = Ground("ground")
    PotentialRef("pref", element=ground)
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    source = VoltageSource("source", bus=bus1, phases="abcn", voltages=230)
    load = PowerLoad("load", bus=bus2, phases="abcn", powers=3e3, connect_neutral=False)
    tp = TransformerParameters("tp", vg="Ynzn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    tr = Transformer("tr", bus_hv=bus1, bus_lv=bus2, parameters=tp)
    bus1.connect_ground(ground)
    bus2.connect_ground(ground, phase="a")
    tr.connect_ground_hv(ground)
    tr.connect_ground_lv(ground, phase="b")
    load.connect_ground(ground)
    source.connect_ground(ground, phase="c")

    en = ElectricalNetwork.from_element(bus1)
    en2 = ElectricalNetwork.from_dict(en.to_dict())
    ground2 = en2.grounds["ground"]
    assert_json_close(ground2.to_dict(), ground.to_dict())

    connections1 = [(c["element"].element_type, c["element"].id, c["phase"], c["side"]) for c in ground.connections]
    connections2 = [(c["element"].element_type, c["element"].id, c["phase"], c["side"]) for c in ground2.connections]
    assert_json_close(connections1, connections2)
