from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd

Vector = npt.NDArray[np.complex_]

ALPHA = np.e ** (2 / 3 * np.pi * 1j)
"""Phasor rotation operator `alpha`, which rotates a phasor vector counterclockwise by 120 degrees
when multiplied by it."""

A = np.array(
    [
        [1, 1, 1],
        [1, ALPHA**2, ALPHA],
        [1, ALPHA, ALPHA**2],
    ],
    dtype=np.complex_,
)
""""A" matrix: transformation matrix from phasor to symmetrical components."""


def phasor_to_sym(v_abc: Sequence[complex]) -> Vector:
    """Compute the symmetrical components `(0, +, -)` from the phasor components `(a, b, c)`."""
    v_012 = np.linalg.inv(A) @ np.asarray(v_abc).reshape((3, 1))
    return v_012


def sym_to_phasor(v_012: Sequence[complex]) -> Vector:
    """Compute the phasor components `(a, b, c)` from the symmetrical components `(0, +, -)`."""
    v_abc = A @ np.asarray(v_012).reshape((3, 1))
    return v_abc


def series_phasor_to_sym(s_abc: pd.Series) -> pd.Series:
    """Compute the symmetrical components `(0, +, -)` from the phasor components `(a, b, c)` of a series.

    Args:
        s_abc:
            Series of phasor components (voltage, current, ...). The series must have a
            multi-index with a `'phase'` level of values `('a', 'b', 'c')`.

    Returns:
        Series of the symmetrical components representing the input phasor series. The series has
        a multi-index with the phase level replaced by a `'sequence'` level of values
        `('zero', 'pos', 'neg')`.

    Example:
        >>> voltage
        bus_id  phase
        vs      a        200000000000.0+0.00000000j
                b       -10000.000000-17320.508076j
                c       -10000.000000+17320.508076j
        bus     a        19999.00000095+0.00000000j
                b        -9999.975000-17320.464775j
                c        -9999.975000+17320.464775j
        Name: voltage, dtype: complex128

        >>> series_phasor_to_sym(voltage)
        bus_id  sequence
        bus     zero        3.183231e-12-9.094947e-13j
                pos         1.999995e+04+3.283594e-12j
                neg        -1.796870e-07-2.728484e-12j
        vs      zero        5.002221e-12-9.094947e-13j
                pos         2.000000e+04+3.283596e-12j
                neg        -1.796880e-07-1.818989e-12j
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
