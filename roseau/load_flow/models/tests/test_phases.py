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
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        PowerLoad("load1", bus, phases=ph, powers=[100] * n)

    # Not in bus
    bus.phases = "ab"
    for phase, missing, n in (("abc", "c", 3), ("abn", "n", 2), ("an", "n", 1)):
        with pytest.raises(RoseauLoadFlowException) as e:
            PowerLoad("load1", bus, phases=phase, powers=[100] * n)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == f"Phases ['{missing}'] of load 'load1' are not in bus 'bus' phases 'ab'"

    # Default
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        bus.phases = ph
        load = PowerLoad("load1", bus, phases=ph, powers=[100] * n)
        assert load.phases == ph

    # Floating neutral (disallowed by default)
    class PowerLoadEngine(PowerLoad):
        _floating_neutral_allowed = True

    bus.phases = "ab"
    PowerLoadEngine("load1", bus, phases="abn", powers=[100, 100])
    # single-phase floating neutral does not make sense
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoadEngine("load1", bus, phases="an", powers=[100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['n'] of load 'load1' are not in bus 'bus' phases 'ab'"


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
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        VoltageSource("source1", bus, phases=ph, voltages=[100] * n)

    # Not in bus
    bus.phases = "ab"
    for phase, missing, n in (("abc", "c", 3), ("abn", "n", 2), ("an", "n", 1)):
        with pytest.raises(RoseauLoadFlowException) as e:
            VoltageSource("source1", bus, phases=phase, voltages=[100] * n)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == f"Phases ['{missing}'] of source 'source1' are not in bus 'bus' phases 'ab'"

    # Default
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        bus.phases = ph
        vs = VoltageSource("source1", bus, voltages=[100] * n)
        assert vs.phases == ph

    # Floating neutral (disallowed by default)
    class VoltageSourceEngine(VoltageSource):
        _floating_neutral_allowed = True

    bus.phases = "ab"
    VoltageSourceEngine("source1", bus, phases="abn", voltages=[100, 100])
    # single-phase floating neutral does not make sense
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSourceEngine("source1", bus, phases="an", voltages=[100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['n'] of source 'source1' are not in bus 'bus' phases 'ab'"


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
    bus2.phases = "ca"
    lp = LineParameters("test", z_line=10 * np.eye(2, dtype=complex))
    line = Line("line1", bus1, bus2, parameters=lp, length=10)
    assert line.phases == line.phases1 == line.phases2 == "ca"

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
    bus2 = Bus("bus-2", phases="ca")
    switch = Switch("switch1", bus1, bus2)
    assert switch.phases == switch.phases1 == switch.phases2 == "ca"


def test_transformer_three_phases():
    bus1 = Bus("bus-1", phases="abcn")
    bus2 = Bus("bus-2", phases="abcn")

    assert Transformer.allowed_phases == Bus.allowed_phases

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
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "abc"
    assert transformer.phases2 == "abcn"

    # Intersection
    bus1.phases = "abcn"
    bus2.phases = "abcn"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "abc"
    assert transformer.phases2 == "abcn"


def test_transformer_single_phases():
    bus1 = Bus("bus-1", phases="an")
    bus2 = Bus("bus-2", phases="an")

    # Not allowed
    tp = TransformerParameters.from_name("160kVA", "single")
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer("tr1", bus1, bus2, phases1=ph, phases2=ph, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Transformer of id 'tr1' got invalid phases1 '{ph}', allowed values are")

    # Allowed
    Transformer("tr1", bus1, bus2, phases1="an", phases2="an", parameters=tp)

    # Not in bus
    bus2.phases = "ab"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer("tr1", bus1, bus2, phases1="an", phases2="an", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) ['n'] of transformer 'tr1' are not in phases 'ab' of bus 'bus-2'."

    # Default
    bus1.phases = "ab"
    bus2.phases = "ab"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ab"
    assert transformer.phases2 == "ab"

    # Intersection
    bus1.phases = "abcn"
    bus2.phases = "ab"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ab"
    assert transformer.phases2 == "ab"

    bus1.phases = "abc"
    bus2.phases = "bcn"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "bc"
    assert transformer.phases2 == "bc"

    bus1.phases = "abc"
    bus2.phases = "ca"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ca"
    assert transformer.phases2 == "ca"

    # Cannot be deduced
    bus1.phases = "abc"
    bus2.phases = "abc"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."

    bus1.phases = "abcn"
    bus2.phases = "abn"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."

    bus1.phases = "abcn"
    bus2.phases = "a"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."


def test_transformer_split_phases():
    bus1 = Bus("bus-1", phases="ab")
    bus2 = Bus("bus-2", phases="abn")

    # Not allowed
    tp = TransformerParameters.from_name("160kVA", "split")
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer("tr1", bus1, bus2, phases1=ph, phases2=ph, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Transformer of id 'tr1' got invalid phases1 '{ph}', allowed values are")

    # Allowed
    Transformer("tr1", bus1, bus2, phases1="ab", phases2="abn", parameters=tp)

    # Not in bus 1
    bus1.phases = "acn"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer("tr1", bus1, bus2, phases1="ab", phases2="abn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) ['b'] of transformer 'tr1' are not in phases 'acn' of bus 'bus-1'."

    # Not in bus 2
    bus1.phases = "abc"
    bus2.phases = "acn"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer("tr1", bus1, bus2, phases1="ab", phases2="abn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) ['b'] of transformer 'tr1' are not in phases 'acn' of bus 'bus-2'."

    # Default
    bus1.phases = "ab"
    bus2.phases = "abn"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ab"
    assert transformer.phases2 == "abn"

    # Intersection
    bus1.phases = "abcn"
    bus2.phases = "can"
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ca"
    assert transformer.phases2 == "can"

    # Cannot be deduced
    bus1.phases = "abc"
    bus2.phases = "abcn"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."

    bus1.phases = "a"
    bus2.phases = "abn"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."

    bus1.phases = "ab"
    bus2.phases = "ab"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."

    bus1.phases = "ab"
    bus2.phases = "abc"
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."


def test_voltage_phases():
    # Bus
    bus = Bus("bus", phases="abcn")
    assert bus.voltage_phases == ["an", "bn", "cn"]

    bus = Bus("bus", phases="bcn")
    assert bus.voltage_phases == ["bn", "cn"]

    bus = Bus("bus", phases="bn")
    assert bus.voltage_phases == ["bn"]

    bus = Bus("bus", phases="abc")
    assert bus.voltage_phases == ["ab", "bc", "ca"]

    bus = Bus("bus", phases="ab")
    assert bus.voltage_phases == ["ab"]

    # Load
    bus = Bus("bus", phases="abcn")
    load = PowerLoad("load", bus, powers=[100, 100, 100], phases="abcn")
    assert load.voltage_phases == ["an", "bn", "cn"]

    load = PowerLoad("load", bus, powers=[100, 100], phases="bcn")
    assert load.voltage_phases == ["bn", "cn"]

    load = PowerLoad("load", bus, powers=[100], phases="bn")
    assert load.voltage_phases == ["bn"]

    load = PowerLoad("load", bus, powers=[100, 100, 100], phases="abc")
    assert load.voltage_phases == ["ab", "bc", "ca"]

    load = PowerLoad("load", bus, powers=[100], phases="ab")
    assert load.voltage_phases == ["ab"]

    # Source
    bus = Bus("bus", phases="abcn")
    load = VoltageSource("vs", bus, voltages=[100, 100, 100], phases="abcn")
    assert load.voltage_phases == ["an", "bn", "cn"]

    load = VoltageSource("vs", bus, voltages=[100, 100], phases="bcn")
    assert load.voltage_phases == ["bn", "cn"]

    load = VoltageSource("vs", bus, voltages=[100], phases="bn")
    assert load.voltage_phases == ["bn"]

    load = VoltageSource("vs", bus, voltages=[100, 100, 100], phases="abc")
    assert load.voltage_phases == ["ab", "bc", "ca"]

    load = VoltageSource("vs", bus, voltages=[100], phases="ab")
    assert load.voltage_phases == ["ab"]
