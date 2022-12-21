import numpy as np
import pytest

from roseau.load_flow import Line
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    Ground,
    LineParameters,
    PotentialRef,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork


def test_to_dict():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    p_ref = PotentialRef("pref", element=ground)
    vs = VoltageSource("vs", source_bus, phases="abcn", voltages=voltages)

    # Same id, different line parameters -> fail
    lp1 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex))
    lp2 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex) * 1.1)

    line1 = Line("line1", source_bus, load_bus, phases="abcn", ground=ground, parameters=lp1, length=10)
    line2 = Line("line2", source_bus, load_bus, phases="abcn", ground=ground, parameters=lp2, length=10)
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        branches=[line1, line2],
        loads=[],
        voltage_sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are multiple line parameters with id 'test'" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_LINE_PARAMETERS_DUPLICATES

    # Same id, same line parameters -> ok
    lp2 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex))
    line2.update_parameters(lp2)
    en.to_dict()

    # Same id, different transformer parameters -> fail
    en.remove_element(line1)
    en.remove_element(line2)
    tp1 = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    tp2 = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=200 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer1 = Transformer(id="Transformer1", bus1=source_bus, bus2=load_bus, parameters=tp1)
    transformer2 = Transformer(id="Transformer2", bus1=source_bus, bus2=load_bus, parameters=tp2)
    en.add_element(transformer1)
    en.add_element(transformer2)
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are multiple transformer parameters with id 't'" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_PARAMETERS_DUPLICATES

    # Same id, same transformer parameters -> ok
    tp2 = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer2.update_parameters(tp2)
    en.to_dict()
