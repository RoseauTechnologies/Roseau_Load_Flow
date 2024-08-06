from itertools import count

import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    CurrentLoad,
    Ground,
    ImpedanceLoad,
    Line,
    LineParameters,
    PotentialRef,
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
            Bus(id="bus1", phases=ph)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == (
            f"Bus of id 'bus1' got invalid phases '{ph}', allowed values are: "
            f"['ab', 'abc', 'abcn', 'abn', 'an', 'bc', 'bcn', 'bn', 'ca', 'can', 'cn']"
        )

    # Allowed
    for ph in ("ab", "abc", "abcn"):
        Bus(id="bus1", phases=ph)


def test_loads_phases():
    bus = Bus(id="bus", phases="abcn")

    assert PowerLoad.allowed_phases == Bus.allowed_phases

    load_ids = count(1)
    # Not allowed
    for ph in ("a", "n", "ba", "nc", "anb", "nabc", "acb"):
        i = next(load_ids)
        with pytest.raises(RoseauLoadFlowException) as e:
            PowerLoad(id=f"load{i}", bus=bus, phases=ph, powers=[100, 100, 100])
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"PowerLoad of id 'load{i}' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        i = next(load_ids)
        load = PowerLoad(id=f"load{i}", bus=bus, phases=ph, powers=[100] * n)
        assert not load.has_floating_neutral

    # Not in bus
    bus = Bus(id="bus", phases="ab")
    for phase, missing, n in (("abc", "c", 3), ("ca", "c", 1), ("an", "n", 1)):
        i = next(load_ids)
        with pytest.raises(RoseauLoadFlowException) as e:
            PowerLoad(id=f"load{i}", bus=bus, phases=phase, powers=[100] * n)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == f"Phases ['{missing}'] of load 'load{i}' are not in bus 'bus' phases 'ab'"

    # Default
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        i = next(load_ids)
        bus = Bus(id="bus", phases=ph)
        load = PowerLoad(id=f"load{i}", bus=bus, powers=[100] * n)
        assert load.phases == ph
        assert not load.has_floating_neutral

    # Floating neutral default behavior
    bus = Bus(id="bus", phases="ab")
    # power and impedance loads can have a floating neutral
    i = next(load_ids)
    load = PowerLoad(id=f"load{i}", bus=bus, phases="abn", powers=[100, 100])
    assert load.has_floating_neutral
    i = next(load_ids)
    load = ImpedanceLoad(id=f"load{i}", bus=bus, phases="abn", impedances=[100, 100])
    assert load.has_floating_neutral
    # current loads cannot have a floating neutral
    i = next(load_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id=f"load{i}", bus=bus, phases="abn", currents=[1.5, 1.5])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == (
        f"Constant current loads cannot have a floating neutral. CurrentLoad 'load{i}' "
        f"has phases 'abn' while bus 'bus' has phases 'ab'."
    )
    i = next(load_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        # single-phase floating neutral does not make sense
        PowerLoad(id=f"load{i}", bus=bus, phases="an", powers=[100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Phases ['n'] of load 'load{i}' are not in bus 'bus' phases 'ab'"

    # Explicitly connected neutral
    bus_ab = Bus(id="bus_ab", phases="ab")
    bus_abn = Bus(id="bus_abn", phases="abn")
    i = next(load_ids)
    with pytest.warns(UserWarning, match=rf"Neutral connection requested for load 'load{i}' with no neutral phase"):
        load = PowerLoad(id=f"load{i}", bus=bus_ab, phases="ab", powers=[100], connect_neutral=True)
    assert not load.has_floating_neutral
    i = next(load_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        # Explicitly connected neutral to a bus without neutral
        PowerLoad(id=f"load{i}", bus=bus_ab, phases="abn", powers=[100, 100], connect_neutral=True)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Phases ['n'] of load 'load{i}' are not in bus 'bus_ab' phases 'ab'"
    i = next(load_ids)
    with pytest.warns(UserWarning, match=rf"Neutral connection requested for load 'load{i}' with no neutral phase"):
        load = PowerLoad(id=f"load{i}", bus=bus_abn, phases="ab", powers=[100], connect_neutral=True)
    assert not load.has_floating_neutral
    load = PowerLoad(id=f"load{i}", bus=bus_abn, phases="abn", powers=[100, 100], connect_neutral=True)
    assert not load.has_floating_neutral

    # Explicitly disconnected neutral
    bus_ab = Bus(id="bus_ab", phases="ab")
    bus_abn = Bus(id="bus_abn", phases="abn")
    i = next(load_ids)
    load = PowerLoad(id=f"load{i}", bus=bus_ab, phases="ab", powers=[100], connect_neutral=False)
    assert not load.has_floating_neutral
    i = next(load_ids)
    load = PowerLoad(id=f"load{i}", bus=bus_ab, phases="abn", powers=[100, 100], connect_neutral=False)
    assert load.has_floating_neutral
    i = next(load_ids)
    load = PowerLoad(id=f"load{i}", bus=bus_abn, phases="ab", powers=[100], connect_neutral=False)
    assert not load.has_floating_neutral
    i = next(load_ids)
    load = PowerLoad(id=f"load{i}", bus=bus_abn, phases="abn", powers=[100, 100], connect_neutral=False)
    assert load.phases == "abn"
    assert load.has_floating_neutral


def test_sources_phases():
    bus = Bus(id="bus", phases="abcn")

    assert VoltageSource.allowed_phases == Bus.allowed_phases

    source_ids = count(1)
    # Not allowed
    for ph in ("a", "n", "ba", "nc", "anb", "nabc", "acb"):
        i = next(source_ids)
        with pytest.raises(RoseauLoadFlowException) as e:
            VoltageSource(f"source{i}", bus, phases=ph, voltages=[100, 100, 100])
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"VoltageSource of id 'source{i}' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        i = next(source_ids)
        source = VoltageSource(id=f"source{i}", bus=bus, phases=ph, voltages=[100] * n)
        assert not source.has_floating_neutral

    # Not in bus
    bus = Bus(id="bus", phases="ab")
    for phase, missing, n in (("abc", "c", 3), ("ca", "c", 1), ("an", "n", 1)):
        i = next(source_ids)
        with pytest.raises(RoseauLoadFlowException) as e:
            VoltageSource(id=f"source{i}", bus=bus, phases=phase, voltages=[100] * n)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == f"Phases ['{missing}'] of source 'source{i}' are not in bus 'bus' phases 'ab'"

    # Default
    for ph, n in (("ab", 1), ("abc", 3), ("abcn", 3)):
        i = next(source_ids)
        bus = Bus(id="bus", phases=ph)
        vs = VoltageSource(id=f"source{i}", bus=bus, voltages=[100] * n)
        assert vs.phases == ph
        assert not vs.has_floating_neutral

    # Floating neutral default behavior
    bus = Bus(id="bus", phases="ab")
    i = next(source_ids)
    source = VoltageSource(id=f"source{i}", bus=bus, phases="abn", voltages=[100, 100])
    assert source.has_floating_neutral
    i = next(source_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        # single-phase floating neutral does not make sense
        VoltageSource(id=f"source{i}", bus=bus, phases="an", voltages=[100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Phases ['n'] of source 'source{i}' are not in bus 'bus' phases 'ab'"

    # Explicitly connected neutral
    bus_ab = Bus(id="bus_ab", phases="ab")
    bus_abn = Bus(id="bus_abn", phases="abn")
    i = next(source_ids)
    with pytest.warns(UserWarning, match=rf"Neutral connection requested for source 'source{i}' with no neutral phase"):
        source = VoltageSource(id=f"source{i}", bus=bus_ab, phases="ab", voltages=[100], connect_neutral=True)
    assert not source.has_floating_neutral
    i = next(source_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        # Explicitly connected neutral to a bus without neutral
        VoltageSource(id=f"source{i}", bus=bus_ab, phases="abn", voltages=[100, 100], connect_neutral=True)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == f"Phases ['n'] of source 'source{i}' are not in bus 'bus_ab' phases 'ab'"
    i = next(source_ids)
    with pytest.warns(UserWarning, match=rf"Neutral connection requested for source 'source{i}' with no neutral phase"):
        source = VoltageSource(id=f"source{i}", bus=bus_abn, phases="ab", voltages=[100], connect_neutral=True)
    assert not source.has_floating_neutral
    source = VoltageSource(id=f"source{i}", bus=bus_abn, phases="abn", voltages=[100, 100], connect_neutral=True)
    assert not source.has_floating_neutral

    # Explicitly disconnected neutral
    bus_ab = Bus(id="bus_ab", phases="ab")
    bus_abn = Bus(id="bus_abn", phases="abn")
    i = next(source_ids)
    source = VoltageSource(id=f"source{i}", bus=bus_ab, phases="ab", voltages=[100], connect_neutral=False)
    assert not source.has_floating_neutral
    i = next(source_ids)
    source = VoltageSource(id=f"source{i}", bus=bus_ab, phases="abn", voltages=[100, 100], connect_neutral=False)
    assert source.has_floating_neutral
    i = next(source_ids)
    source = VoltageSource(id=f"source{i}", bus=bus_abn, phases="ab", voltages=[100], connect_neutral=False)
    assert not source.has_floating_neutral
    i = next(source_ids)
    source = VoltageSource(id=f"source{i}", bus=bus_abn, phases="abn", voltages=[100, 100], connect_neutral=False)
    assert source.phases == "abn"
    assert source.has_floating_neutral


def test_lines_phases():
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="abcn")

    assert Line.allowed_phases == Bus.allowed_phases | {"a", "b", "c", "n"}

    line_ids = count(1)
    # Not allowed
    lp = LineParameters(id="test", z_line=10 * np.eye(4, dtype=complex))
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        i = next(line_ids)
        with pytest.raises(RoseauLoadFlowException) as e:
            Line(id=f"line{i}", bus1=bus1, bus2=bus2, phases=ph, parameters=lp, length=10)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Line of id 'line{i}' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph in ("ab", "abc", "a", "n"):
        i = next(line_ids)
        lp = LineParameters("test", z_line=10 * np.eye(len(ph), dtype=complex))
        Line(id=f"line{i}", bus1=bus1, bus2=bus2, phases=ph, parameters=lp, length=10)

    # Not in bus
    bus1 = Bus(id="bus-1", phases="abc")
    i = next(line_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(id=f"line{i}", bus1=bus1, bus2=bus2, phases="abcn", parameters=lp, length=10)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == (
        f"Phases ['n'] of line 'line{i}' are not in the common phases ['a', 'b', 'c'] of buses 'bus-1' and 'bus-2'."
    )

    # Default
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="ca")
    i = next(line_ids)
    lp = LineParameters(id="test", z_line=10 * np.eye(2, dtype=complex))
    line = Line(id=f"line{i}", bus1=bus1, bus2=bus2, parameters=lp, length=10)
    assert line.phases == line.phases1 == line.phases2 == "ca"

    # Bad default
    lp = LineParameters(id="test", z_line=10 * np.eye(3, dtype=complex))  # bad
    i = next(line_ids)
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(id=f"line{i}", bus1=bus1, bus2=bus2, parameters=lp, length=10)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert e.value.msg == f"Incorrect z_line dimensions for line 'line{i}': (3, 3) instead of (2, 2)"


def test_switches_phases():
    assert Switch.allowed_phases == Line.allowed_phases  # same as lines

    # Not allowed
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        bus1 = Bus(id="bus-1", phases="abcn")
        bus2 = Bus(id="bus-2", phases="abcn")
        with pytest.raises(RoseauLoadFlowException) as e:
            Switch(id="switch1", bus1=bus1, bus2=bus2, phases=ph)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Switch of id 'switch1' got invalid phases '{ph}', allowed values are")

    # Allowed
    for ph in ("ab", "abc", "a", "n"):
        bus1 = Bus(id="bus-1", phases="abcn")
        bus2 = Bus(id="bus-2", phases="abcn")
        Switch(id="switch1", bus1=bus1, bus2=bus2, phases=ph)

    # Not in bus
    bus1 = Bus(id="bus-1", phases="abc")
    bus2 = Bus(id="bus-2", phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Switch(id="switch1", bus1=bus1, bus2=bus2, phases="abcn")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert (
        e.value.msg
        == "Phases ['n'] of switch 'switch1' are not in the common phases ['a', 'b', 'c'] of buses 'bus-1' and 'bus-2'."
    )

    # Default
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="ca")
    switch = Switch(id="switch1", bus1=bus1, bus2=bus2)
    assert switch.phases == switch.phases1 == switch.phases2 == "ca"


def test_transformer_three_phases():
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="abcn")

    assert Transformer.allowed_phases == Bus.allowed_phases

    # Not allowed
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="H61_50kVA", type="Dyn11", uhv=20000, ulv=400, sn=50 * 1e3, p0=145, i0=1.8 / 100, psc=1350, vsc=4 / 100
    )
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1=ph, phases2=ph, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Transformer of id 'tr1' got invalid phases1 '{ph}', allowed values are")

    # Allowed
    Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="abc", phases2="abcn", parameters=tp)

    # Not in bus
    bus2 = Bus(id="bus-2", phases="abc")
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="abc", phases2="abcn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) ['n'] of transformer 'tr1' are not in phases 'abc' of bus 'bus-2'."

    # Not in transformer
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="abcn")
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="abcn", phases2="abcn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) 'abcn' of transformer 'tr1' are not compatible with its winding 'D'."

    # Default
    bus1 = Bus(id="bus-1", phases="abc")
    bus2 = Bus(id="bus-2", phases="abcn")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "abc"
    assert transformer.phases2 == "abcn"

    # Intersection
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="abcn")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "abc"
    assert transformer.phases2 == "abcn"


def test_transformer_single_phases():
    bus1 = Bus(id="bus-1", phases="an")
    bus2 = Bus(id="bus-2", phases="an")

    # Not allowed
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="160kVA", type="single", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1=ph, phases2=ph, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Transformer of id 'tr1' got invalid phases1 '{ph}', allowed values are")

    # Allowed
    Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="an", phases2="an", parameters=tp)

    # Not in bus
    bus2 = Bus(id="bus-2", phases="ab")
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="an", phases2="an", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) ['n'] of transformer 'tr1' are not in phases 'ab' of bus 'bus-2'."

    # Default
    bus1 = Bus(id="bus-1", phases="ab")
    bus2 = Bus(id="bus-2", phases="ab")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ab"
    assert transformer.phases2 == "ab"

    # Intersection
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="ab")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ab"
    assert transformer.phases2 == "ab"

    bus1 = Bus(id="bus-1", phases="abc")
    bus2 = Bus(id="bus-2", phases="bcn")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "bc"
    assert transformer.phases2 == "bc"

    bus1 = Bus(id="bus-1", phases="abc")
    bus2 = Bus(id="bus-2", phases="ca")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ca"
    assert transformer.phases2 == "ca"

    # Cannot be deduced
    for ph1, ph2 in (
        ("abc", "abc"),
        ("abcn", "abn"),
        ("abcn", "abc"),
    ):
        bus1 = Bus(id="bus-1", phases=ph1)
        bus2 = Bus(id="bus-2", phases=ph2)
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == (
            "Phases (1) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."
        )


def test_transformer_center_phases():
    bus1 = Bus(id="bus-1", phases="ab")
    bus2 = Bus(id="bus-2", phases="abn")

    # Not allowed
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="160kVA", type="center", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    for ph in ("ba", "nc", "anb", "nabc", "acb"):
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1=ph, phases2=ph, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg.startswith(f"Transformer of id 'tr1' got invalid phases1 '{ph}', allowed values are")

    # Allowed
    Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="ab", phases2="abn", parameters=tp)

    # Not in bus 1
    bus1 = Bus(id="bus-1", phases="can")
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="ab", phases2="abn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (1) ['b'] of transformer 'tr1' are not in phases 'can' of bus 'bus-1'."

    # Not in bus 2
    bus1 = Bus(id="bus-1", phases="abc")
    bus2 = Bus(id="bus-2", phases="can")
    with pytest.raises(RoseauLoadFlowException) as e:
        Transformer(id="tr1", bus1=bus1, bus2=bus2, phases1="ab", phases2="abn", parameters=tp)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases (2) ['b'] of transformer 'tr1' are not in phases 'can' of bus 'bus-2'."

    # Default
    bus1 = Bus(id="bus-1", phases="ab")
    bus2 = Bus(id="bus-2", phases="abn")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ab"
    assert transformer.phases2 == "abn"

    # Intersection
    bus1 = Bus(id="bus-1", phases="abcn")
    bus2 = Bus(id="bus-2", phases="can")
    transformer = Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
    assert transformer.phases1 == "ca"
    assert transformer.phases2 == "can"

    # Cannot be deduced
    for ph1, ph2, err_ph in (
        ("abc", "abcn", 1),
        ("ca", "abn", 1),
        ("ab", "ab", 2),
        ("ab", "abc", 2),
    ):
        bus1 = Bus(id="bus-1", phases=ph1)
        bus2 = Bus(id="bus-2", phases=ph2)
        with pytest.raises(RoseauLoadFlowException) as e:
            Transformer(id="tr1", bus1=bus1, bus2=bus2, parameters=tp)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
        assert e.value.msg == (
            f"Phases ({err_ph}) of transformer 'tr1' cannot be deduced from the buses, they need to be specified."
        )


def test_voltage_phases():
    # Bus
    bus = Bus(id="bus", phases="abcn")
    assert bus.voltage_phases == ["an", "bn", "cn"]

    bus = Bus(id="bus", phases="bcn")
    assert bus.voltage_phases == ["bn", "cn"]

    bus = Bus(id="bus", phases="bn")
    assert bus.voltage_phases == ["bn"]

    bus = Bus(id="bus", phases="abc")
    assert bus.voltage_phases == ["ab", "bc", "ca"]

    bus = Bus(id="bus", phases="ab")
    assert bus.voltage_phases == ["ab"]

    # Load
    bus = Bus(id="bus", phases="abcn")
    load = PowerLoad(id="load1", bus=bus, powers=[100, 100, 100], phases="abcn")
    assert load.voltage_phases == ["an", "bn", "cn"]

    load = PowerLoad(id="load2", bus=bus, powers=[100, 100], phases="bcn")
    assert load.voltage_phases == ["bn", "cn"]

    load = PowerLoad(id="load3", bus=bus, powers=[100], phases="bn")
    assert load.voltage_phases == ["bn"]

    load = PowerLoad(id="load4", bus=bus, powers=[100, 100, 100], phases="abc")
    assert load.voltage_phases == ["ab", "bc", "ca"]

    load = PowerLoad(id="load5", bus=bus, powers=[100], phases="ab")
    assert load.voltage_phases == ["ab"]

    # Source
    bus = Bus(id="bus", phases="abcn")
    load = VoltageSource(id="vs1", bus=bus, voltages=[100, 100, 100], phases="abcn")
    assert load.voltage_phases == ["an", "bn", "cn"]

    load = VoltageSource(id="vs2", bus=bus, voltages=[100, 100], phases="bcn")
    assert load.voltage_phases == ["bn", "cn"]

    load = VoltageSource(id="vs3", bus=bus, voltages=[100], phases="bn")
    assert load.voltage_phases == ["bn"]

    load = VoltageSource(id="vs4", bus=bus, voltages=[100, 100, 100], phases="abc")
    assert load.voltage_phases == ["ab", "bc", "ca"]

    load = VoltageSource(id="vs5", bus=bus, voltages=[100], phases="ab")
    assert load.voltage_phases == ["ab"]


def test_potential_ref_phases():
    bus_abc = Bus(id="bus_abc", phases="abc")
    bus_abcn = Bus(id="bus_abcn", phases="abcn")
    ground = Ground(id="ground")

    # Default behavior
    assert PotentialRef(id="ref1", element=bus_abc).phases == "abc"
    assert PotentialRef(id="ref2", element=bus_abcn).phases == "n"
    assert PotentialRef(id="ref3", element=ground).phases is None

    # Explicit phases
    assert PotentialRef(id="ref4", element=bus_abc, phases="a").phases == "a"
    assert PotentialRef(id="ref5", element=bus_abc, phases="ab").phases == "ab"
    assert PotentialRef(id="ref6", element=bus_abcn, phases="ab").phases == "ab"
    assert PotentialRef(id="ref7", element=bus_abcn, phases="abcn").phases == "abcn"

    # Not allowed
    with pytest.raises(RoseauLoadFlowException) as e:
        PotentialRef(id="ref8", element=bus_abc, phases="an")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Phases ['n'] of potential reference 'ref8' are not in bus 'bus_abc' phases 'abc'"
    with pytest.raises(RoseauLoadFlowException) as e:
        PotentialRef(id="ref9", element=ground, phases="n")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Potential reference 'ref9' connected to the ground cannot have a phase."

    # Deprecated
    with pytest.warns(DeprecationWarning, match=r"The 'phase' argument is deprecated, use 'phases' instead"):
        assert PotentialRef(id="ref10", element=bus_abc, phase="a").phases == "a"
