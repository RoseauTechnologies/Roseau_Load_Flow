import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

from roseau.load_flow.sym import phasor_to_sym, series_phasor_to_sym, sym_to_phasor
from roseau.load_flow.utils import SequenceDtype


def test_phasor_to_sym():
    # Tests verified with https://phillipopambuh.info/portfolio/calculator--symmetrical_components.html
    va = 230 + 0j
    vb = 230 * np.e ** (1j * 4 * np.pi / 3)
    vc = 230 * np.e ** (1j * 2 * np.pi / 3)

    # Test balanced direct system: positive sequence
    expected = np.array([0, 230, 0], dtype=complex)
    assert np.allclose(phasor_to_sym([va, vb, vc]), expected)
    # Also test numpy array input with different shapes
    assert np.allclose(phasor_to_sym(np.array([va, vb, vc])), expected)
    assert np.allclose(phasor_to_sym(np.array([[va], [vb], [vc]])), expected.reshape((3, 1)))

    # Test balanced indirect system: negative sequence
    expected = np.array([0, 0, 230], dtype=complex)
    assert np.allclose(phasor_to_sym([va, vc, vb]), expected)

    # Test unbalanced system: zero sequence
    expected = np.array([230, 0, 0], dtype=complex)
    assert np.allclose(phasor_to_sym([va, va, va]), expected)

    # Test unbalanced system: general case
    va = 200 + 0j
    expected = np.array([10 * np.exp(1j * np.pi), 220, 10 * np.exp(1j * np.pi)], dtype=complex)
    assert np.allclose(phasor_to_sym([va, vb, vc]), expected)


def test_sym_to_phasor():
    # Tests verified with https://phillipopambuh.info/portfolio/calculator--symmetrical_components.html
    va = 230 + 0j
    vb = 230 * np.e ** (1j * 4 * np.pi / 3)
    vc = 230 * np.e ** (1j * 2 * np.pi / 3)

    # Test balanced direct system: positive sequence
    expected = np.array([va, vb, vc], dtype=complex)
    assert np.allclose(sym_to_phasor([0, va, 0]), expected)
    # Also test numpy array input with different shapes
    assert np.allclose(sym_to_phasor(np.array([0, va, 0])), expected)
    assert np.allclose(sym_to_phasor(np.array([[0], [va], [0]])), expected.reshape((3, 1)))

    # Test balanced indirect system: negative sequence
    expected = np.array([va, vc, vb], dtype=complex)
    assert np.allclose(sym_to_phasor([0, 0, va]), expected)

    # Test unbalanced system: zero sequence
    expected = np.array([va, va, va], dtype=complex)
    assert np.allclose(sym_to_phasor([va, 0, 0]), expected)

    # Test unbalanced system: general case
    va = 200 + 0j
    expected = np.array([va, vb, vc], dtype=complex)
    assert np.allclose(sym_to_phasor([10 * np.e ** (1j * np.pi), 220, 10 * np.e ** (1j * np.pi)]), expected)


def test_phasor_sym_roundtrip():
    va = 230 + 0j
    vb = 230 * np.e ** (1j * 4 * np.pi / 3)
    vc = 230 * np.e ** (1j * 2 * np.pi / 3)

    # Test balanced direct system: positive sequence
    assert np.allclose(sym_to_phasor(phasor_to_sym([va, vb, vc])), np.array([va, vb, vc]))

    # Test balanced indirect system: negative sequence
    assert np.allclose(sym_to_phasor(phasor_to_sym([va, vc, vb])), np.array([va, vc, vb]))

    # Test unbalanced system: zero sequence
    assert np.allclose(sym_to_phasor(phasor_to_sym([va, va, va])), np.array([va, va, va]))

    # Test unbalanced system: general case
    va = 200 + 0j
    assert np.allclose(sym_to_phasor(phasor_to_sym([va, vb, vc])), np.array([va, vb, vc]))


def test_series_phasor_to_sym():
    va = 230 + 0j
    vb = 230 * np.exp(1j * 4 * np.pi / 3)
    vc = 230 * np.exp(1j * 2 * np.pi / 3)

    # Test with different phases per bus, different systems, different magnitudes
    # fmt: off
    voltage_data = {
        # Direct system (positive sequence)
        ("bus1", "a"): va, ("bus1", "b"): vb, ("bus1", "c"): vc,
        # Indirect system (negative sequence)
        ("bus2", "an"): va / 2, ("bus2", "bn"): vc / 2, ("bus2", "cn"): vb / 2,
        # Unbalanced system (zero sequence)
        ("bus3", "ab"): va, ("bus3", "bc"): va, ("bus3", "ca"): va,
    }
    expected_sym_data = [
        0, va, 0,  # Direct system (positive sequence)
        0, 0, va / 2,  # Indirect system (negative sequence)
        va, 0, 0,  # Unbalanced system (zero sequence)
    ]
    # fmt: on
    expected_sym_index = pd.MultiIndex.from_arrays(
        [
            pd.Index(["bus1", "bus1", "bus1", "bus2", "bus2", "bus2", "bus3", "bus3", "bus3"]),
            pd.CategoricalIndex(
                ["zero", "pos", "neg", "zero", "pos", "neg", "zero", "pos", "neg"], dtype=SequenceDtype
            ),
        ],
        names=["bus_id", "sequence"],
    )
    voltage = pd.Series(voltage_data, name="voltage").rename_axis(index=["bus_id", "phase"])
    expected = pd.Series(data=expected_sym_data, index=expected_sym_index, name="voltage")
    assert_series_equal(series_phasor_to_sym(voltage), expected, check_exact=False)
