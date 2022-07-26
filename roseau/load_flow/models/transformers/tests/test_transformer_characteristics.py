import numpy as np
import pytest

from roseau.load_flow import TransformerCharacteristics
from roseau.load_flow.utils import ThundersValueError
from roseau.load_flow.utils.units import Q_


def test_transformer_characteristics():
    # Example in the "transformers" document of Victor.
    # Yzn11 - 50kVA
    data = {
        "name": "Yzn11 - 50kVA",
        "psc": 1350.0,  # W
        "p0": 145.0,  # W
        "i0": 1.8 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 50 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "yzn11",
    }
    tc = TransformerCharacteristics.from_dict(data)

    z2, ym, k, orientation = tc.to_zyk()
    r_iron = 20e3**2 / 145  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((1.8 / 100 * 50e3) ** 2 - 145**2))  # H *rad/s
    z2_norm = 4 / 100 * 400**2 / 50e3
    r2 = 1350 * 400**2 / 50e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = Q_(1 / r_iron + 1 / (1j * lm_omega), "S")
    z2_expected = Q_(r2 + 1j * l2_omega, "ohm")
    k_expected = 400 / (np.sqrt(3.0) * 20e3)
    orientation_expected = 1.0

    assert np.isclose(z2, z2_expected)
    assert np.isclose(ym, ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

    # Dyn11 - 100kVA
    data = {
        "name": "Dyn11 - 100kVA",
        "psc": 2150.0,  # W
        "p0": 210.0,  # W
        "i0": 3.5 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 100 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    tc = TransformerCharacteristics.from_dict(data)
    z2, ym, k, orientation = tc.to_zyk()
    r_iron = 20e3**2 / 210  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((3.5 / 100 * 100e3) ** 2 - 210**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 100e3
    r2 = 2150 * 400**2 / 100e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = Q_(1 / r_iron + 1 / (1j * lm_omega), "S")
    z2_expected = Q_(r2 + 1j * l2_omega, "ohm")
    k_expected = (400 / np.sqrt(3)) / 20e3
    orientation_expected = 1.0

    assert np.isclose(z2, z2_expected)
    assert np.isclose(ym, ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

    # Dyn5 - 160kVA
    data = {
        "name": "Dyn5 - 160kVA",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn5",
    }
    tc = TransformerCharacteristics.from_dict(data)
    z2, ym, k, orientation = tc.to_zyk()
    r_iron = 20e3**2 / 460  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((5.6 / 100 * 160e3) ** 2 - 460**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 160e3
    r2 = 2350 * 400**2 / 160e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = Q_(1 / r_iron + 1 / (1j * lm_omega), "S")
    z2_expected = Q_(r2 + 1j * l2_omega, "ohm")
    k_expected = 400 / np.sqrt(3) / 20e3
    orientation_expected = -1.0

    assert np.isclose(z2, z2_expected)
    assert np.isclose(ym, ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

    # Check that there is an error if the winding is not good
    data = {
        "name": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dtotoyn11",
    }
    with pytest.raises(ThundersValueError) as e:
        TransformerCharacteristics.from_dict(data)
    assert "Transformer windings can not be extracted from the string" in e.value.args[0]

    # UHV == ULV...
    data = {
        "name": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 400,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(ThundersValueError) as e:
        TransformerCharacteristics.from_dict(data)
    assert "has a high voltages lower or equal than the low voltages" in e.value.args[0]

    # UHV < ULV...
    data = {
        "name": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 350,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(ThundersValueError) as e:
        TransformerCharacteristics.from_dict(data)
    assert "has a high voltages lower or equal than the low voltages" in e.value.args[0]
