import numpy as np
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow import (
    Bus,
    DeltaWyeTransformer,
    ElectricalNetwork,
    FlexibleLoad,
    FlexibleParameter,
    Ground,
    PotentialReference,
    SimplifiedLine,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.utils.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils.units import Q_


def test_to_dict():
    ground = Ground()
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        voltages=voltages,
    )
    bus = Bus(id="load bus", n=4)
    ground.connect(bus)
    p_ref = PotentialReference(element=ground)

    # Same type name twice
    line_characteristics1 = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    line_characteristics2 = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))

    line1 = SimplifiedLine(id="line1", n=4, bus1=vs, bus2=bus, line_characteristics=line_characteristics1, length=10)
    line2 = SimplifiedLine(id="line2", n=4, bus1=vs, bus2=bus, line_characteristics=line_characteristics2, length=10)
    en = ElectricalNetwork([vs, bus], [line1, line2], [], [p_ref, ground])
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are line characteristics type name duplicates" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.JSON_LINE_CHARACTERISTICS_DUPLICATES

    en.remove_element("line1")
    en.remove_element("line2")
    transformer_characteristics1 = TransformerCharacteristics(
        type_name="test", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3, psc=2350, vsc=4
    )
    transformer_characteristics2 = TransformerCharacteristics(
        type_name="test", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3, psc=2350, vsc=4
    )
    transformer1 = DeltaWyeTransformer(
        id="Transformer1", bus1=vs, bus2=bus, transformer_characteristics=transformer_characteristics1
    )
    transformer2 = DeltaWyeTransformer(
        id="Transformer2", bus1=vs, bus2=bus, transformer_characteristics=transformer_characteristics2
    )
    en.add_element(transformer1)
    en.add_element(transformer2)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are transformer characteristics type name duplicates" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_CHARACTERISTICS_DUPLICATES


def test_from_dict():
    ground = Ground()
    vn = Q_(0.4 / np.sqrt(3), "kV")
    voltages = vn * [1, np.exp(-2 / 3 * np.pi * 1j), np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        voltages=voltages,
    )
    load_bus = Bus(id="load bus", n=4)
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    line = SimplifiedLine(
        id="line", n=4, bus1=vs, bus2=load_bus, line_characteristics=line_characteristics, length=10  # km
    )

    pa = FlexibleParameter.p_max_u_production(240, 250, 300)
    pb = FlexibleParameter.pq_u_production(250, 260, 210, 220, 240, 250, 300)
    pc = FlexibleParameter.p_max_u_consumption(210, 220, 300)

    flexible_load = FlexibleLoad("flexible load", 4, load_bus, [-100 + 50j, -100 + 50j, 100 + 50j], [pa, pb, pc])
    fpc = FlexibleParameter.constant()
    power_load = FlexibleLoad("power load", 4, load_bus, [100 + 0j, 0j, 0j], [fpc, fpc, fpc])
    p_ref = PotentialReference(ground)

    en = ElectricalNetwork([vs, load_bus], [line], [flexible_load, power_load], [p_ref, ground])
    en.solve_load_flow(max_iterations=50)
    buses_results_1, branches_results_1 = en.results

    en_dict = en.to_dict()
    en2 = en.from_dict(en_dict)
    en2.solve_load_flow()
    buses_results_2, branches_results_2 = en2.results

    # Check
    assert_frame_equal(buses_results_1, buses_results_2, check_like=True)
    assert_frame_equal(branches_results_1, branches_results_2, check_like=True, atol=1e-2, rtol=1e-5)
