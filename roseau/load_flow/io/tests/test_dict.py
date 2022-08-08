import numpy as np
import pytest

from roseau.load_flow import (
    Bus,
    DeltaWyeTransformer,
    ElectricalNetwork,
    Ground,
    PotentialRef,
    SimplifiedLine,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.models.lines.line_characteristics import LineCharacteristics
from roseau.load_flow.utils.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode


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
    p_ref = PotentialRef(element=ground)

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

    # Good one
    en.remove_element(transformer2.id)
    en.to_dict()
