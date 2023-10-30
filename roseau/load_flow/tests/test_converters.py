import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

from roseau.load_flow.converters import phasor_to_sym, series_phasor_to_sym, sym_to_phasor
from roseau.load_flow.utils import PhaseDtype


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
    vb = 230 * np.e ** (1j * 4 * np.pi / 3)
    vc = 230 * np.e ** (1j * 2 * np.pi / 3)

    index = pd.MultiIndex.from_tuples(
        [("bus1", "a"), ("bus1", "b"), ("bus1", "c"), ("bus2", "a"), ("bus2", "b"), ("bus2", "c")],
        names=["bus_id", "phase"],
    )
    index = index.set_levels(index.levels[-1].astype(PhaseDtype), level=-1)
    voltage = pd.Series([va, vb, vc, va / 2, vb / 2, vc / 2], index=index, name="voltage")

    seq_dtype = pd.CategoricalDtype(categories=["zero", "pos", "neg"], ordered=True)
    sym_index = index.set_levels(["zero", "pos", "neg"], level=-1)
    sym_index = sym_index.set_names("sequence", level=-1).set_levels(sym_index.levels[-1].astype(seq_dtype), level=-1)
    expected = pd.Series([0, va, 0, 0, va / 2, 0], index=sym_index, name="voltage")

    assert_series_equal(series_phasor_to_sym(voltage), expected)
