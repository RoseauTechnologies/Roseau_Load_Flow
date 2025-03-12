import numpy.testing as npt
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    Ground,
    GroundConnection,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Switch,
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
    gc1 = GroundConnection(ground=ground1, element=bus1)
    assert ground1.connections == [gc1]
    assert gc1.id == "bus 'bus1' phase 'n' to ground 'ground1'"
    g1_nc = len(ground1.connections)
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=bus3)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in phases 'abc' of bus 'bus3'."
    assert len(ground1.connections) == g1_nc

    # Cannot connect to the same phase
    g1_nc = len(ground1.connections)
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=bus1, phase="n")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Ground 'ground1' is already connected to phase 'n' of bus 'bus1'."
    assert len(ground1.connections) == g1_nc

    # Connect to a specific phase
    gc2 = GroundConnection(ground=ground1, element=bus3, phase="a")
    assert gc2 in ground1.connections

    # Connect to another phase raises an error by default
    g1_nc = len(ground1.connections)
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=bus3, phase="b")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_GROUND_ID
    assert e.value.msg == "Ground 'ground1' is already connected to phase 'a' of bus 'bus3'."
    assert len(ground1.connections) == g1_nc

    # But the error can turn into a warning
    with pytest.warns(UserWarning, match=r"Ground 'ground1' is already connected to phase 'a' of bus 'bus3'."):
        gc3 = GroundConnection(ground=ground1, element=bus3, phase="b", on_connected="warn")
    assert gc3 in ground1.connections

    # Or totally ignored
    gc4 = GroundConnection(ground=ground1, element=bus3, phase="c", on_connected="ignore")
    assert gc4 in ground1.connections

    # Connecting another ground to the same phase is fine
    gc5 = GroundConnection(ground=ground2, element=bus3, phase="c")
    assert gc5 in ground2.connections

    # Cannot use side terminal elements
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=bus1, side="HV")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE
    assert e.value.msg == "Side cannot be used with bus elements, only with branches."

    # Loads and sources
    load = PowerLoad("load", bus=bus2, phases="abcn", powers=3e3, connect_neutral=False)
    source = VoltageSource("source", bus=bus2, phases="abcn", voltages=230)
    gc6 = GroundConnection(ground=ground1, element=load, phase="n")  # Connect to the floating neutral
    assert gc6 in ground1.connections
    gc7 = GroundConnection(ground=ground1, element=source, phase="n")
    assert gc7 in ground1.connections

    # Transformers
    tp = TransformerParameters("tp", vg="Yzn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    tr = Transformer("tr", bus_hv=bus1, bus_lv=bus2, parameters=tp)
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=tr)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE
    assert e.value.msg == "Side is missing for transformer 'tr', expected one of ('HV', 'LV')."
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=tr, side="BT")  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE
    assert e.value.msg == "Invalid side 'BT' for transformer 'tr', expected one of ('HV', 'LV')."
    gc8 = GroundConnection(ground=ground1, element=tr, side="LV", phase="n")
    assert gc8 in ground1.connections
    assert gc8.id == "transformer 'tr' LV phase 'n' to ground 'ground1'"
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=tr, side="HV", phase="n")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in HV phases 'abc' of transformer 'tr'."
    gc9 = GroundConnection(ground=ground1, element=tr, side="HV", phase="a")
    assert gc9 in ground1.connections

    # Lines and switches
    lp = LineParameters("lp", z_line=[[0.1, 0], [0, 0.1]])
    ln = Line("ln", bus1=bus1, bus2=bus2, parameters=lp, phases="an", length=1)
    sw = Switch("sw", bus1=bus2, bus2=bus3, phases="bc")
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=ln)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE
    assert e.value.msg == "Side is missing for line 'ln', expected one of (1, 2)."
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=sw)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_BRANCH_SIDE
    assert e.value.msg == "Side is missing for switch 'sw', expected one of (1, 2)."
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=sw, side=1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in phases 1 'bc' of switch 'sw'."
    gc10 = GroundConnection(ground=ground1, element=ln, side=1, phase="a")
    assert gc10 in ground1.connections
    assert gc10.id == "line 'ln' phase 1 'a' to ground 'ground1'"
    gc11 = GroundConnection(ground=ground1, element=sw, side=2, phase="b")
    assert gc11 in ground1.connections
    assert gc11.id == "switch 'sw' phase 2 'b' to ground 'ground1'"


def test_impedant_ground():
    bus = Bus("bus", phases="abcn")
    ground = Ground("ground")
    gc = GroundConnection(ground=ground, element=bus)
    npt.assert_allclose(gc.impedance.m, 0)
    assert "Switch" in type(gc._cy_element).__name__

    # Non-zero impedance
    gc.impedance = 0.5 + 0.1j
    npt.assert_allclose(gc.impedance.m, 0.5 + 0.1j)
    assert "Line" in type(gc._cy_element).__name__

    # Change its value
    gc.impedance = 0.2
    npt.assert_allclose(gc.impedance.m, 0.2)
    assert "Line" in type(gc._cy_element).__name__

    # Zero again
    gc.impedance = 0
    npt.assert_allclose(gc.impedance.m, 0)
    assert "Switch" in type(gc._cy_element).__name__


def test_ground_connections_to_from_dict_roundtrip():
    ground = Ground("ground")
    pref = PotentialRef("pref", element=ground)
    bus1 = Bus("bus1", phases="abcn")
    bus2 = Bus("bus2", phases="abcn")
    source = VoltageSource("source", bus=bus1, phases="abcn", voltages=230)
    load = PowerLoad("load", bus=bus2, phases="abcn", powers=3e3, connect_neutral=False)
    tp = TransformerParameters("tp", vg="Ynzn11", uhv=20e3, ulv=400, sn=160e3, z2=0.01, ym=0.01j)
    tr = Transformer("tr", bus_hv=bus1, bus_lv=bus2, parameters=tp)
    connections = [
        GroundConnection(element=bus1, ground=ground),
        GroundConnection(element=bus2, ground=ground, phase="a"),
        GroundConnection(element=tr, ground=ground, side="HV"),
        GroundConnection(element=tr, ground=ground, side="LV", phase="b"),
        GroundConnection(element=load, ground=ground),
        GroundConnection(element=source, ground=ground, phase="c"),
    ]

    en = ElectricalNetwork(
        buses=[bus1, bus2],
        grounds=[ground],
        sources=[source],
        loads=[load],
        transformers=[tr],
        lines=[],
        switches=[],
        potential_refs=[pref],
        ground_connections=connections,
    )
    en_dict = en.to_dict()
    en2 = ElectricalNetwork.from_dict(en_dict)
    ground2 = en2.grounds["ground"]
    assert_json_close(ground2.to_dict(), ground.to_dict())

    connections1 = [gc.to_dict() for gc in ground.connections]
    connections2 = [gc.to_dict() for gc in ground2.connections]
    assert_json_close(connections1, connections2)


def test_ground_deprecations():
    ground = Ground("ground")
    bus = Bus("bus", phases="abcn")
    load = PowerLoad("load", bus=bus, phases="abcn", powers=3e3, connect_neutral=False)

    with pytest.warns(
        DeprecationWarning, match=r"`Ground.connect` is deprecated, use the `GroundConnection` class instead."
    ):
        ground.connect(bus, phase="a")
    assert len(ground.connections) == 1
    assert ground.connections[0].element is bus
    assert ground.connections[0].phase == "a"
    assert ground.connections[0].side is None

    GroundConnection(ground=ground, element=load, phase="n")
    with pytest.warns(
        DeprecationWarning, match=r"`Ground.connected_buses` is deprecated, use `Ground.connections` instead."
    ):
        connected_buses = ground.connected_buses
    assert connected_buses == {"bus": "a"}
