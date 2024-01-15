"""
This module provides helper functions to convert from one representation to another.

Available functions:

* convert between phasor and symmetrical components
* convert potentials to voltages
"""
from collections.abc import Sequence

import numpy as np
import pandas as pd

from roseau.load_flow.typing import ComplexArray

ALPHA = np.exp(2 / 3 * np.pi * 1j)
"""complex: Phasor rotation operator `alpha`, which rotates a phasor vector counterclockwise by 120
degrees when multiplied by it."""

A = np.array(
    [
        [1, 1, 1],
        [1, ALPHA**2, ALPHA],
        [1, ALPHA, ALPHA**2],
    ],
    dtype=np.complex128,
)
"""numpy.ndarray[complex]: "A" matrix: transformation matrix from phasor to symmetrical components."""

_A_INV = np.linalg.inv(A)


def phasor_to_sym(v_abc: Sequence[complex]) -> ComplexArray:
    """Compute the symmetrical components `(0, +, -)` from the phasor components `(a, b, c)`."""
    v_abc_array = np.array(v_abc)
    orig_shape = v_abc_array.shape
    v_012 = _A_INV @ v_abc_array.reshape((3, 1))
    return v_012.reshape(orig_shape)


def sym_to_phasor(v_012: Sequence[complex]) -> ComplexArray:
    """Compute the phasor components `(a, b, c)` from the symmetrical components `(0, +, -)`."""
    v_012_array = np.array(v_012)
    orig_shape = v_012_array.shape
    v_abc = A @ v_012_array.reshape((3, 1))
    return v_abc.reshape(orig_shape)


def series_phasor_to_sym(s_abc: pd.Series) -> pd.Series:
    """Compute the symmetrical components `(0, +, -)` from the phasor components `(a, b, c)` of a series.

    Args:
        s_abc:
            Series of phasor components (voltage, current, ...). The series must have a
            multi-index with a `'phase'` level containing the phases in order (a -> b -> c).

    Returns:
        Series of the symmetrical components representing the input phasor series. The series has
        a multi-index with the phase level replaced by a `'sequence'` level of values
        `('zero', 'pos', 'neg')`.

    Example:
        Say we have a pandas series of three-phase voltages of every bus in the network:

        >>> voltage
        bus_id  phase
        vs      an       200000000000.0+0.00000000j
                bn      -10000.000000-17320.508076j
                cn      -10000.000000+17320.508076j
        bus     an       19999.00000095+0.00000000j
                bn       -9999.975000-17320.464775j
                cn       -9999.975000+17320.464775j
        Name: voltage, dtype: complex128

        We can get the `zero`, `positive`, and `negative` sequences of the voltage using:

        >>> voltage_sym_components = series_phasor_to_sym(voltage)
        >>> voltage_sym_components
        bus_id  sequence
        bus     zero        3.183231e-12-9.094947e-13j
                pos         1.999995e+04+3.283594e-12j
                neg        -1.796870e-07-2.728484e-12j
        vs      zero        5.002221e-12-9.094947e-13j
                pos         2.000000e+04+3.283596e-12j
                neg        -1.796880e-07-1.818989e-12j
        Name: voltage, dtype: complex128

        We can now access each sequence of the symmetrical components individually:

        >>> voltage_sym_components.loc[:, "zero"]  # get zero sequence values
        bus_id
        bus     3.183231e-12-9.094947e-13j
        vs      5.002221e-12-9.094947e-13j
        Name: voltage, dtype: complex128

    """
    if not isinstance(s_abc, pd.Series):
        raise TypeError("Input must be a pandas Series.")
    s_012: pd.Series = (
        s_abc.unstack("phase")
        .apply(lambda x: phasor_to_sym(x).flatten(), axis="columns", result_type="expand")
        .rename(columns={0: "zero", 1: "pos", 2: "neg"})
        .stack()
    )
    s_012.name = s_abc.name
    s_012.index = s_012.index.set_names("sequence", level=-1).set_levels(
        s_012.index.levels[-1].astype(pd.CategoricalDtype(categories=["zero", "pos", "neg"], ordered=True)), level=-1
    )
    return s_012


def calculate_voltages(potentials: ComplexArray, phases: str) -> ComplexArray:
    """Calculate the voltages between phases given the potentials of each phase.

    Args:
        potentials:
            Array of the complex potentials of each phase.

        phases:
            String of the phases in order. If a neutral exists, it must be the last.

    Returns:
        Array of the voltages between phases. If a neutral exists, the voltages are Phase-Neutral.
        Otherwise, the voltages are Phase-Phase.

    Example:
        >>> potentials = 230 * np.array([1, np.exp(-2j*np.pi/3), np.exp(2j*np.pi/3), 0], dtype=np.complex128)
        >>> calculate_voltages(potentials, "abcn")
        array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j])
        >>> potentials = np.array([230, 230 * np.exp(-2j*np.pi/3)], dtype=np.complex128)
        >>> calculate_voltages(potentials, "ab")
        array([345.+199.18584287j])
        >>> calculate_voltages(np.array([230, 0], dtype=np.complex128), "an")
        array([230.+0.j])
    """
    assert len(potentials) == len(phases), "Number of potentials must match number of phases."
    if "n" in phases:  # Van, Vbn, Vcn
        # we know "n" is the last phase
        voltages = potentials[:-1] - potentials[-1]
    else:  # Vab, Vbc, Vca
        if len(phases) == 2:
            # V = potentials[0] - potentials[1] (but as array)
            voltages = potentials[:1] - potentials[1:]
        else:
            assert phases == "abc"
            voltages = np.array(
                [potentials[0] - potentials[1], potentials[1] - potentials[2], potentials[2] - potentials[0]],
                dtype=np.complex128,
            )
    return voltages


def _calculate_voltage_phases(phases: str) -> list[str]:
    if "n" in phases:  # "an", "bn", "cn"
        return [p + "n" for p in phases[:-1]]
    else:  # "ab", "bc", "ca"
        if len(phases) == 2:
            return [phases]
        else:
            return [p1 + p2 for p1, p2 in zip(phases, np.roll(list(phases), -1), strict=True)]


_voltage_cache: dict[str, list[str]] = {}
for _phases in ("ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn"):
    _voltage_cache[_phases] = _calculate_voltage_phases(_phases)


def calculate_voltage_phases(phases: str) -> list[str]:
    """Calculate the composite phases of the voltages given the phases of an element.

    Args:
        phases:
            String of the phases in order. If a neutral exists, it must be the last.

    Returns:
        List of the composite phases of the voltages.

    Example:
        >>> calculate_voltage_phases("an")
        ['an']
        >>> calculate_voltage_phases("ab")
        ['ab']
        >>> calculate_voltage_phases("abc")
        ['ab', 'bc', 'ca']
        >>> calculate_voltage_phases("abcn")
        ['an', 'bn', 'cn']
    """
    return _voltage_cache[phases]
