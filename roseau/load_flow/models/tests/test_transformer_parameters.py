import numpy as np
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import TransformerParameters


def test_transformer_parameters():
    # Example in the "transformers" document of Victor.
    # Yzn11 - 50kVA
    data = {
        "id": "Yzn11 - 50kVA",
        "psc": 1350.0,  # W
        "p0": 145.0,  # W
        "i0": 1.8 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 50 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "yzn11",
    }
    tp = TransformerParameters.from_dict(data)

    z2, ym, k, orientation = tp.to_zyk()
    r_iron = 20e3**2 / 145  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((1.8 / 100 * 50e3) ** 2 - 145**2))  # H *rad/s
    z2_norm = 4 / 100 * 400**2 / 50e3
    r2 = 1350 * 400**2 / 50e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = 400 / (np.sqrt(3.0) * 20e3)
    orientation_expected = 1.0

    assert np.isclose(z2.m_as("ohm"), z2_expected)
    assert np.isclose(ym.m_as("S"), ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

    # Dyn11 - 100kVA
    data = {
        "id": "Dyn11 - 100kVA",
        "psc": 2150.0,  # W
        "p0": 210.0,  # W
        "i0": 3.5 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 100 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    tp = TransformerParameters.from_dict(data)
    z2, ym, k, orientation = tp.to_zyk()
    r_iron = 20e3**2 / 210  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((3.5 / 100 * 100e3) ** 2 - 210**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 100e3
    r2 = 2150 * 400**2 / 100e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = (400 / np.sqrt(3)) / 20e3
    orientation_expected = 1.0

    assert np.isclose(z2.m_as("ohm"), z2_expected)
    assert np.isclose(ym.m_as("S"), ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

    # Dyn5 - 160kVA
    data = {
        "id": "Dyn5 - 160kVA",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn5",
    }
    tp = TransformerParameters.from_dict(data)
    z2, ym, k, orientation = tp.to_zyk()
    r_iron = 20e3**2 / 460  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((5.6 / 100 * 160e3) ** 2 - 460**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 160e3
    r2 = 2350 * 400**2 / 160e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = 400 / np.sqrt(3) / 20e3
    orientation_expected = -1.0

    assert np.isclose(z2.m_as("ohm"), z2_expected)
    assert np.isclose(ym.m_as("S"), ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

    # Check that there is an error if the winding is not good
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dtotoyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "Transformer windings cannot be extracted from the string" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS

    # UHV == ULV...
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 400,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the low voltages higher than the high voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES

    # UHV < ULV...
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 350,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the low voltages higher than the high voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES

    # Bad i0
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the 'current during off-load test' i0" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS

    # Bad vsc
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4,  # %
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the 'voltages on LV side during short circuit test' vsc" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS


def test_from_name():
    # Bad ones
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_name("toto", "Dyn11")
    assert "The transformer type name does not follow the syntax rule" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX

    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_name("A160kVA", "Dyn11")
    assert "The transformer type name does not follow the syntax rule" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX

    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_name("160kVA", "totoDyn11")
    assert "Transformer windings cannot be extracted from the string" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS

    # Good ones
    TransformerParameters.from_name("160kVA", "Dyn11")
    TransformerParameters.from_name("H61_50kVA", "Dyn11")
