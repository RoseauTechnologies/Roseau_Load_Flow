import numpy as np
import pytest

import roseau.load_flow as rlf
import roseau.load_flow_single as rlfs
from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode


def test_import():
    # Ensure that RLF and RLFS have nearly the same interface
    rlf_dir = set(dir(rlf)) - {"ConductorType", "InsulatorType"}
    rlfs_dir = set(dir(rlfs))

    assert rlf_dir - rlfs_dir == {
        # Multi-phase elements
        "Ground",
        "PotentialRef",
        "GroundConnection",
        # Sequences
        "NegativeSequence",
        "PositiveSequence",
        "ZeroSequence",
        "ALPHA",
        "ALPHA2",
        "converters",
        # Symmetrical components
        "sym",
        # Underscore things
        "__getattr__",
        "__about__",
        "_solvers",
        # Unrelated imports
        "Any",
        "importlib",
    }
    # conftest is not included in wheels
    assert rlfs_dir - rlf_dir <= {"conftest"}


def test_incompatible_phase_tech():
    ground_m = rlf.Ground(id="Ground M")
    bus1_m = rlf.Bus(id="Bus1 M", phases="abcn")
    bus2_m = rlf.Bus(id="Bus2 M", phases="abcn")
    bus1_s = rlfs.Bus(id="Bus1 S")
    bus2_s = rlfs.Bus(id="Bus2 S")
    lp_m = rlf.LineParameters(id="LP M", z_line=0.1 * np.eye(4))
    lp_s = rlfs.LineParameters(id="LP S", z_line=0.1)
    tp_m = rlf.TransformerParameters(id="TP M", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.1, ym=0.1j)
    tp_s = rlfs.TransformerParameters(id="TP S", vg="Dyn11", uhv=20e3, ulv=400, sn=100e3, z2=0.1, ym=0.1j)

    # single-phase sources and loads
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.VoltageSource(id="Src S", bus=bus1_m, voltage=230)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase source 'Src S' to multi-phase bus 'Bus1 M'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.PowerLoad(id="Ld S", bus=bus2_m, power=1e3)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase load 'Ld S' to multi-phase bus 'Bus2 M'."

    # multi-phase sources and loads
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.VoltageSource(id="Src M", bus=bus1_s, voltages=230)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase source 'Src M' to single-phase bus 'Bus1 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.PowerLoad(id="Ld M", bus=bus2_s, powers=1e3)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase load 'Ld M' to single-phase bus 'Bus2 S'."

    # single-phase lines
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Line(id="Ln S", bus1=bus1_m, bus2=bus2_s, parameters=lp_s, length=0.1)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase line 'Ln S' to multi-phase bus 'Bus1 M'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Line(id="Ln S", bus1=bus1_s, bus2=bus2_m, parameters=lp_s, length=0.1)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase line 'Ln S' to multi-phase bus 'Bus2 M'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Line(id="Ln S", bus1=bus1_s, bus2=bus2_s, parameters=lp_m, length=0.1)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase line 'Ln S' to multi-phase parameters 'LP M'."

    # multi-phase lines
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Line(id="Ln M", bus1=bus1_s, bus2=bus2_m, parameters=lp_m, length=0.1)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase line 'Ln M' to single-phase bus 'Bus1 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Line(id="Ln M", bus1=bus1_m, bus2=bus2_s, parameters=lp_m, length=0.1)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase line 'Ln M' to single-phase bus 'Bus2 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Line(id="Ln M", bus1=bus1_m, bus2=bus2_m, parameters=lp_s, length=0.1)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase line 'Ln M' to single-phase parameters 'LP S'."

    # single-phase transformers
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Transformer(id="Tr S", bus_hv=bus1_m, bus_lv=bus2_s, parameters=tp_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase transformer 'Tr S' to multi-phase bus 'Bus1 M'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Transformer(id="Tr S", bus_hv=bus1_s, bus_lv=bus2_m, parameters=tp_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase transformer 'Tr S' to multi-phase bus 'Bus2 M'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Transformer(id="Tr S", bus_hv=bus1_s, bus_lv=bus2_s, parameters=tp_m)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase transformer 'Tr S' to multi-phase parameters 'TP M'."

    # multi-phase transformers
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Transformer(id="Tr M", bus_hv=bus1_s, bus_lv=bus2_m, parameters=tp_m)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase transformer 'Tr M' to single-phase bus 'Bus1 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Transformer(id="Tr M", bus_hv=bus1_m, bus_lv=bus2_s, parameters=tp_m)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase transformer 'Tr M' to single-phase bus 'Bus2 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Transformer(id="Tr M", bus_hv=bus1_m, bus_lv=bus2_m, parameters=tp_s)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase transformer 'Tr M' to single-phase parameters 'TP S'."

    # single-phase switches
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Switch(id="Sw S", bus1=bus1_m, bus2=bus2_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase switch 'Sw S' to multi-phase bus 'Bus1 M'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.Switch(id="Sw S", bus1=bus1_s, bus2=bus2_m)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase switch 'Sw S' to multi-phase bus 'Bus2 M'."

    # multi-phase switches
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Switch(id="Sw M", bus1=bus1_s, bus2=bus2_m)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase switch 'Sw M' to single-phase bus 'Bus1 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.Switch(id="Sw M", bus1=bus1_m, bus2=bus2_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase switch 'Sw M' to single-phase bus 'Bus2 S'."

    # ground connections and potential references
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.PotentialRef(id="PRef", element=bus1_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase potential ref 'PRef' to single-phase bus 'Bus1 S'."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.GroundConnection(id="GC", ground=ground_m, element=bus1_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase ground connection 'GC' to single-phase bus 'Bus1 S'."

    # single-pahse network
    bus_m = rlf.Bus(id="Bus M", phases="abcn")
    source_m = rlf.VoltageSource(id="Src M", bus=bus_m, voltages=230)
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.ElectricalNetwork.from_element(bus_m)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase bus 'Bus M' to single-phase network."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlfs.ElectricalNetwork(buses=[bus_m], sources=[source_m], lines=[], transformers=[], switches=[], loads=[])  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect multi-phase bus 'Bus M' to single-phase network."

    # multi-phase network
    bus_s = rlfs.Bus(id="Bus S")
    source_s = rlfs.VoltageSource(id="Src S", bus=bus_s, voltage=230)
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.ElectricalNetwork.from_element(bus_s)  # type: ignore
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase bus 'Bus S' to multi-phase network."
    with pytest.raises(RoseauLoadFlowException) as e:
        rlf.ElectricalNetwork(
            buses=[bus_s],  # type: ignore
            sources=[source_s],  # type: ignore
            lines=[],
            transformers=[],
            switches=[],
            loads=[],
            grounds=[],
            potential_refs=[],
            ground_connections=[],
        )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT
    assert e.value.msg == "Cannot connect single-phase bus 'Bus S' to multi-phase network."
