import numpy as np
import pytest

from roseau.load_flow.converters import calculate_voltages, kron_reduction
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


def test_kron_reduction():
    nxn = np.array(
        [
            [10, 2, 3, 4],
            [2, 20, 5, 6],
            [3, 5, 30, 7],
            [4, 6, 7, 40],
        ],
        dtype=np.complex128,
    )
    reduced = kron_reduction(nxn)
    expected = np.array(
        # New_ij = Old_ij - Old_in * Old_nj / Old_nn; i, j ∈ {1,...,n-1}
        [
            [10 - 4 * 4 / 40, 2 - 4 * 6 / 40, 3 - 4 * 7 / 40],
            [2 - 6 * 4 / 40, 20 - 6 * 6 / 40, 5 - 6 * 7 / 40],
            [3 - 7 * 4 / 40, 5 - 7 * 6 / 40, 30 - 7 * 7 / 40],
        ],
        dtype=np.complex128,
    )
    np.testing.assert_allclose(reduced, expected)

    with pytest.raises(ValueError, match=r"Matrix must be square, got shape \(3, 4\)."):
        kron_reduction(nxn[:3, :4])
