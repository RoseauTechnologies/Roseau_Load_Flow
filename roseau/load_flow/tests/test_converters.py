import numpy as np

from roseau.load_flow.converters import calculate_voltages
from roseau.load_flow.units import Q_, ureg


def test_calculate_voltages():
    potentials = 230 * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3), 0], dtype=np.complex128)
    voltages = calculate_voltages(potentials, "abcn").m
    np.testing.assert_allclose(voltages, np.array([230.0 + 0.0j, -115.0 - 199.18584287j, -115.0 + 199.18584287j]))
    potentials = np.array([230, 230 * np.exp(-2j * np.pi / 3)], dtype=np.complex128)
    voltages = calculate_voltages(potentials, "ab").m
    np.testing.assert_allclose(voltages, np.array([345.0 + 199.18584287j]))
    voltages = calculate_voltages(np.array([230, 0], dtype=np.complex128), "an").m
    np.testing.assert_allclose(voltages, np.array([230.0 + 0.0j]))

    # Quantities
    voltages = calculate_voltages(Q_([20, 0], "kV"), "an")
    np.testing.assert_allclose(voltages.m, np.array([20000.0 + 0.0j]))
    assert voltages.units == ureg.Unit("V")

    # Array-like
    voltages = calculate_voltages([230, 0], "an")
    np.testing.assert_allclose(voltages.m, np.array([230.0 + 0.0j]))
    voltages = calculate_voltages([230, 0], "ab")
    np.testing.assert_allclose(voltages.m, np.array([230.0 + 0.0j]))
    voltages = calculate_voltages([230, 230j, -230j], "abc")
    np.testing.assert_allclose(voltages.m, np.array([230.0 - 230.0j, 460.0j, -230.0 - 230.0j]))
    voltages = calculate_voltages([230, 230j, -230j, 0], "abcn")
    np.testing.assert_allclose(voltages.m, np.array([230.0, 230.0j, -230.0j]))
