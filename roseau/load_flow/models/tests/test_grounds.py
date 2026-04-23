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
        GroundConnection(ground=ground1, element=tr)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect transformer 'tr' to the ground. Did you mean to connect one of its sides?"
    gc8 = GroundConnection(ground=ground1, element=tr.side_lv, phase="n")
    assert gc8 in ground1.connections
    assert gc8.id == "transformer 'tr' LV side phase 'n' to ground 'ground1'"
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=tr.side_hv, phase="n")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in HV side phases 'abc' of transformer 'tr'."
    gc9 = GroundConnection(ground=ground1, element=tr.side_hv, phase="a")
    assert gc9 in ground1.connections

    # Lines and switches
    lp = LineParameters("lp", z_line=[[0.1, 0], [0, 0.1]])
    ln = Line("ln", bus1=bus1, bus2=bus2, parameters=lp, phases="an", length=1)
    sw = Switch("sw", bus1=bus2, bus2=bus3, phases="bc")
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=ln)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect line 'ln' to the ground. Did you mean to connect one of its sides?"
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=sw)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect switch 'sw' to the ground. Did you mean to connect one of its sides?"
    with pytest.raises(RoseauLoadFlowException) as e:
        GroundConnection(ground=ground1, element=sw.side1)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phase 'n' is not present in side (1) phases 'bc' of switch 'sw'."
    gc10 = GroundConnection(ground=ground1, element=ln.side1, phase="a")
    assert gc10 in ground1.connections
    assert gc10.id == "line 'ln' side (1) phase 'a' to ground 'ground1'"
    gc11 = GroundConnection(ground=ground1, element=sw.side2, phase="b")
    assert gc11 in ground1.connections
    assert gc11.id == "switch 'sw' side (2) phase 'b' to ground 'ground1'"


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
        GroundConnection(element=tr.side_hv, ground=ground),
        GroundConnection(element=tr.side_lv, ground=ground, phase="b"),
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

    with pytest.warns(
        DeprecationWarning, match=r"`Ground.connect` is deprecated, use the `GroundConnection` class instead."
    ):
        ground.connect(bus, phase="a")
    assert len(ground.connections) == 1
    assert ground.connections[0].element is bus
    assert ground.connections[0].phase == "a"
    assert ground.connections[0].side is None


def test_ground_connection_repr():
    ground = Ground("Ground")
    bus = Bus("Bus", phases="an")
    gc = GroundConnection(ground=ground, element=bus)
    assert repr(gc) == (
        "<GroundConnection: id=\"bus 'Bus' phase 'n' to ground 'Ground'\", ground='Ground', "
        "element=<bus 'Bus'>, impedance=0j, phase='n', on_connected='raise'>"
    )
    bus2 = Bus("Bus2", phases="an")
    sw = Switch("Sw", bus1=bus, bus2=bus2)
    gc2 = GroundConnection(id="GC2", ground=ground, element=sw.side1)
    assert repr(gc2) == (
        "<GroundConnection: id='GC2', ground='Ground', element=<switch 'Sw' side (1)>, "
        "impedance=0j, phase='n', on_connected='raise'>"
    )
