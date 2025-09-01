"""Symmetrical components utilities."""

from typing import Final

import numpy as np
import pandas as pd

from roseau.load_flow.constants import ALPHA, ALPHA2
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike1D, ComplexMatrix
from roseau.load_flow.utils.dtypes import SequenceDtype

__all__ = [
    "A",
    "A_INV",
    "PositiveSequence",
    "NegativeSequence",
    "ZeroSequence",
    "phasor_to_sym",
    "sym_to_phasor",
    "series_phasor_to_sym",
]

PositiveSequence: Final[ComplexArray] = np.array([1, ALPHA2, ALPHA], dtype=np.complex128)  # type: ignore
"""numpy.ndarray[complex]: Unit vector of positive-sequence components of a three-phase system."""
NegativeSequence: Final[ComplexArray] = np.array([1, ALPHA, ALPHA2], dtype=np.complex128)  # type: ignore
"""numpy.ndarray[complex]: Unit vector of negative-sequence components of a three-phase system."""
ZeroSequence: Final[ComplexArray] = np.array([1, 1, 1], dtype=np.complex128)  # type: ignore
"""numpy.ndarray[complex]: Unit vector of zero-sequence components of a three-phase system."""

A: Final[ComplexMatrix] = np.array([ZeroSequence, PositiveSequence, NegativeSequence], dtype=np.complex128)  # type: ignore
"""numpy.ndarray[complex]: `A` matrix: transformation matrix from phasor to symmetrical components."""

A_INV: Final[ComplexMatrix] = np.linalg.inv(A)  # type: ignore
"""numpy.ndarray[complex]: Inverse of `A` matrix: transformation matrix from symmetrical to phasor components."""

_SEQ_INDEX = pd.CategoricalIndex(["zero", "pos", "neg"], name="sequence", dtype=SequenceDtype)


def phasor_to_sym(v_abc: ComplexArrayLike1D) -> ComplexArray:
    """Compute the symmetrical components `(0, +, -)` from the phasor components `(a, b, c)`."""
    v_abc_array = np.asarray(v_abc, dtype=np.complex128)
    orig_shape = v_abc_array.shape
    v_012 = A_INV @ v_abc_array.reshape((3, 1))
    return v_012.reshape(orig_shape)


def sym_to_phasor(v_012: ComplexArrayLike1D) -> ComplexArray:
    """Compute the phasor components `(a, b, c)` from the symmetrical components `(0, +, -)`."""
    v_012_array = np.asarray(v_012, dtype=np.complex128)
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
    if not isinstance(s_abc.index, pd.MultiIndex):
        raise ValueError("Input series must have a MultiIndex.")
    if "phase" not in s_abc.index.names:
        raise ValueError("Input series must have a 'phase' level in the MultiIndex.")
    level_names = [name for name in s_abc.index.names if name != "phase"]
    s_012 = s_abc.groupby(level=level_names, sort=False).apply(
        lambda s: pd.Series(A_INV @ s, index=_SEQ_INDEX, dtype=np.complex128)
    )
    return s_012
