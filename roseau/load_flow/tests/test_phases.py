import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    Line,
    LineParameters,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)


def test_buses_phases():
    assert Bus.allowed_phases == frozenset(
        {
            # LINE-LINE
            "ab",
            "bc",
            "ca",
            # LINE-NEUTRAL
            "an",
            "bn",
            "cn",
            # LINE-LINE-NEUTRAL
            "abn",
            "bcn",
            "can",
            # LINE-LINE-LINE
            "abc",
            # LINE-LINE-LINE-NEUTRAL
            "abcn",
        }
    )

    # Not allowed
    for ph in ("a", "n", "ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Bus("bus1", phases=ph)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == (
            f"Bus of id 'bus1' got invalid phases '{ph}', allowed values are: "
            f"['ab', 'abc', 'abcn', 'abn', 'an', 'bc', 'bcn', 'bn', 'ca', 'can', 'cn']"
        )

    # Allowed
    for ph in ("ab", "abc", "abcn"):
        Bus("bus1", phases=ph)


def test_loads_phases():
    bus = Bus("bus", phases="abcn")

    assert PowerLoad.allowed_phases == Bus.allowed_phases

    # Not allowed
    for ph in ("a", "n", "ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            PowerLoad("load1", bus, phases=ph, powers=[100, 100, 100])
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"PowerLoad of id 'load1' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph in ("ab", "abc", "abcn"):
        PowerLoad("load1", bus, phases=ph, powers=[100] * len(set(ph) - {"n"}))

    # Not in bus
    bus.phases = "ab"
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load1", bus, phases="abc", powers=[100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['c'] of load 'load1' are not in bus 'bus' phases 'ab'"

    # "n" not in bus is allowed though
    PowerLoad("load1", bus, phases="abn", powers=[100, 100])
    # unless it is a single phase load
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load1", bus, phases="an", powers=[100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['n'] of load 'load1' are not in bus 'bus' phases 'ab'"

    # Default
    for ph in ("ab", "abc", "abcn"):
        bus.phases = ph
        load = PowerLoad("load1", bus, phases=ph, powers=[100] * len(set(ph) - {"n"}))
        assert load.phases == ph


def test_sources_phases():
    bus = Bus("bus", phases="abcn")

    assert VoltageSource.allowed_phases == Bus.allowed_phases

    # Not allowed
    for ph in ("a", "n", "ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            VoltageSource("source1", bus, phases=ph, voltages=[100, 100, 100])
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"VoltageSource of id 'source1' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph in ("ab", "abc", "abcn"):
        VoltageSource("source1", bus, phases=ph, voltages=[100] * len(set(ph) - {"n"}))

    # Not in bus
    bus.phases = "ab"
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource("source1", bus, phases="abc", voltages=[100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['c'] of source 'source1' are not in bus 'bus' phases 'ab'"

    # "n" not in bus is allowed though
    VoltageSource("source1", bus, phases="abn", voltages=[100, 100])
    # unless it is a single phase source
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource("source1", bus, phases="an", voltages=[100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['n'] of source 'source1' are not in bus 'bus' phases 'ab'"

    # Default
    for ph in ("ab", "abc", "abcn"):
        bus.phases = ph
        vs = VoltageSource("source1", bus, voltages=[100] * len(set(ph) - {"n"}))
        assert vs.phases == ph


def test_lines_phases():
    bus1 = Bus("bus-1", phases="abcn")
    bus2 = Bus("bus-2", phases="abcn")

    assert Line.allowed_phases == Bus.allowed_phases | {"a", "b", "c", "n"}

    # Not allowed
    lp = LineParameters("test", z_line=10 * np.eye(4, dtype=complex))
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Line("line1", bus1, bus2, phases=ph, parameters=lp, length=10)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Line of id 'line1' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph in ("ab", "abc", "a", "n"):
        lp = LineParameters("test", z_line=10 * np.eye(len(ph), dtype=complex))
        Line("line1", bus1, bus2, phases=ph, parameters=lp, length=10)

    # Not in bus
    bus1.phases = "abc"
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line1", bus1, bus2, phases="abcn", parameters=lp, length=10)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert (
        e.value.msg
        == "Phases ['n'] of line 'line1' are not in the common phases ['a', 'b', 'c'] of buses 'bus-1' and 'bus-2'."
    )

    # Default
    bus1.phases = "abcn"
    bus2.phases = "ab"
    lp = LineParameters("test", z_line=10 * np.eye(2, dtype=complex))
    line = Line("line1", bus1, bus2, parameters=lp, length=10)
    assert line.phases == line.phases1 == line.phases2 == "ab"

    # Bad default
    lp = LineParameters("test", z_line=10 * np.eye(3, dtype=complex))  # bad
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line1", bus1, bus2, parameters=lp, length=10)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert e.value.msg == "Incorrect z_line dimensions for line 'line1': (3, 3) instead of (2, 2)"


def test_switches_phases():
    assert Switch.allowed_phases == Line.allowed_phases  # same as lines

    # Not allowed
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        bus1 = Bus("bus-1", phases="abcn")
        bus2 = Bus("bus-2", phases="abcn")
        with pytest.raises(RoseauLoadFlowException) as e:
            Switch("switch1", bus1, bus2, phases=ph)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Switch of id 'switch1' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph in ("ab", "abc", "a", "n"):
        bus1 = Bus("bus-1", phases="abcn")
        bus2 = Bus("bus-2", phases="abcn")
        Switch("switch1", bus1, bus2, phases=ph)

    # Not in bus
    bus1 = Bus("bus-1", phases="abc")
    bus2 = Bus("bus-2", phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch("switch1", bus1, bus2, phases="abcn")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert (
        e.value.msg
        == "Phases ['n'] of switch 'switch1' are not in the common phases ['a', 'b', 'c'] of buses 'bus-1' and 'bus-2'."
    )

    # Default
    bus1 = Bus("bus-1", phases="abcn")
    bus2 = Bus("bus-2", phases="ab")
    switch = Switch("switch1", bus1, bus2)
    assert switch.phases == switch.phases1 == switch.phases2 == "ab"


def test_transformer_phases():
    bus1 = Bus("bus-1", phases="abcn")
    bus2 = Bus("bus-2", phases="abcn")

    assert Transformer.allowed_phases == {"abc", "abcn"}

    # Not allowed
    tp = TransformerParameters.from_name("H61_50kVA", "Dyn11")
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer("tr1", bus1, bus2, phases1=ph, phases2=ph, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Transformer of id 'tr1' got invalid phases1 '{ph}', allowed values are")

    # Allowed
    Transformer("tr1", bus1, bus2, phases1="abc", phases2="abcn", parameters=tp)

    # Not in bus
    bus2.phases = "abc"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer("tr1", bus1, bus2, phases1="abc", phases2="abcn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) ['n'] of transformer 'tr1' are not in phases 'abc' of bus 'bus-2'."

    # Not in transformer
    bus1.phases = "abcn"
    bus2.phases = "abcn"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer("tr1", bus1, bus2, phases1="abcn", phases2="abcn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) 'abcn' of transformer 'tr1' are not compatible with its winding 'D'."

    # Default
    bus1.phases = "abc"
    bus2.phases = "abcn"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp, length=10)
    assert transformer.phases1 == "abc"
    assert transformer.phases2 == "abcn"

    # Intersection
    bus1.phases = "abcn"
    bus2.phases = "abcn"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp, length=10)
    assert transformer.phases1 == "abc"
    assert transformer.phases2 == "abcn"
