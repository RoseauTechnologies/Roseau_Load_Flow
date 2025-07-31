import numpy as np
import pytest

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import TransformerParameters as MultiTransformerParameters
from roseau.load_flow_single.models import TransformerParameters


def test_from_roseau_load_flow():
    lp_m = MultiTransformerParameters.from_open_and_short_circuit_tests(
        id="TP", vg="Yzn11", sn=50e3, uhv=20e3, ulv=400, p0=145, i0=0.018, psc=1350, vsc=0.04
    )
    lp_s = TransformerParameters.from_roseau_load_flow(lp_m)
    assert np.isclose(lp_s.z2.m, lp_m.z2.m)
    assert np.isclose(lp_s.ym.m, lp_m.ym.m)
    assert lp_s.vg == lp_m.vg
    assert lp_s.id == lp_m.id
    assert np.isclose(lp_s.sn.m, lp_m.sn.m)
    assert np.isclose(lp_s.uhv.m, lp_m.uhv.m)
    assert np.isclose(lp_s.ulv.m, lp_m.ulv.m)
    assert np.isclose(lp_s.p0.m, lp_m.p0.m)
    assert np.isclose(lp_s.i0.m, lp_m.i0.m)
    assert np.isclose(lp_s.psc.m, lp_m.psc.m)
    assert np.isclose(lp_s.vsc.m, lp_m.vsc.m)

    lp_m_bad = MultiTransformerParameters.from_open_and_short_circuit_tests(
        id="Bad TP", vg="Ii0", sn=10e3, uhv=230, ulv=230, p0=90, i0=0.001, psc=280, vsc=0.028
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_roseau_load_flow(lp_m_bad)
    assert e.value.code == RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == (
        "Multi-phase transformer parameters with id 'Bad TP' and vector group 'Ii0' cannot be "
        "converted to `rlfs.TransformerParameters`. It must be three-phase."
    )
