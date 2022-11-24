import numpy as np
import pytest

from roseau.load_flow import Line
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    DeltaWyeTransformer,
    Ground,
    LineCharacteristics,
    PotentialRef,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork


def test_to_dict():
    ground = Ground()
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        source_voltages=voltages,
    )
    bus = Bus(id="load bus", n=4)
    ground.connect(bus)
    p_ref = PotentialRef(element=ground)

    # Same type name, different characteristics -> fail
    lc1 = LineCharacteristics("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex))
    lc2 = LineCharacteristics("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex) * 1.1)

    line1 = Line(id="line1", n=4, bus1=vs, bus2=bus, ground=ground, line_characteristics=lc1, length=10)
    line2 = Line(id="line2", n=4, bus1=vs, bus2=bus, ground=ground, line_characteristics=lc2, length=10)
    en = ElectricalNetwork([vs, bus], [line1, line2], [], [p_ref, ground])
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are line characteristics duplicates" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.JSON_LINE_CHARACTERISTICS_DUPLICATES

    # Same type name, same characteristics -> ok
    lc2 = LineCharacteristics("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex))
    line2.update_characteristics(line_characteristics=lc2)
    en.to_dict()

    # Same transformer type name, different characteristics -> fail
    en.remove_element("line1")
    en.remove_element("line2")
    transformer_characteristics1 = TransformerCharacteristics(
        type_name="t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer_characteristics2 = TransformerCharacteristics(
        type_name="t", windings="Dyn11", uhv=20000, ulv=400, sn=200 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
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
    assert "There are transformer characteristics duplicates" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_CHARACTERISTICS_DUPLICATES

    # Same type name, same characteristics -> ok
    transformer_characteristics2 = TransformerCharacteristics(
        type_name="t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer2.update_characteristics(transformer_characteristics=transformer_characteristics2)
    en.to_dict()
