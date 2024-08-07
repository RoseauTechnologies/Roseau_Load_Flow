"""
This module provides helper functions to convert from one representation to another.

Available functions:

* convert between phasor and symmetrical components
* convert potentials to voltages
"""

import logging

import numpy as np
import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike1D
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils.constants import NegativeSequence, PositiveSequence, ZeroSequence
from roseau.load_flow.utils.types import SequenceDtype

logger = logging.getLogger(__name__)

A = np.array([ZeroSequence, PositiveSequence, NegativeSequence], dtype=np.complex128)
"""numpy.ndarray[complex]: "A" matrix: transformation matrix from phasor to symmetrical components."""

_A_INV = np.linalg.inv(A)
_SEQ_INDEX = pd.CategoricalIndex(["zero", "pos", "neg"], name="sequence", dtype=SequenceDtype)


def phasor_to_sym(v_abc: ComplexArrayLike1D) -> ComplexArray:
    """Compute the symmetrical components `(0, +, -)` from the phasor components `(a, b, c)`."""
    v_abc_array = np.asarray(v_abc)
    orig_shape = v_abc_array.shape
    v_012 = _A_INV @ v_abc_array.reshape((3, 1))
    return v_012.reshape(orig_shape)


def sym_to_phasor(v_012: ComplexArrayLike1D) -> ComplexArray:
    """Compute the phasor components `(a, b, c)` from the symmetrical components `(0, +, -)`."""
    v_012_array = np.asarray(v_012)
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
        lambda s: pd.Series(_A_INV @ s, index=_SEQ_INDEX, dtype=np.complex128)
    )
    return s_012


def _calculate_voltages(potentials: ComplexArray, phases: str) -> ComplexArray:
    if len(potentials) != len(phases):
        msg = (
            f"Number of potentials must match number of phases, got {len(potentials)} potentials "
            f"and {len(phases)} phases."
        )
        logger.error(msg)
        raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE)
    if "n" in phases:  # V_an, V_bn, V_cn, V_abcn
        # we know "n" is the last phase
        voltages = potentials[:-1] - potentials[-1]
    elif len(phases) == 2:  # V_ab, V_bc, V_ca
        # V = potentials[0] - potentials[1] (but as array)
        voltages = potentials[:1] - potentials[1:]
    else:  # V_abc
        assert phases == "abc"
        voltages = np.array(
            [potentials[0] - potentials[1], potentials[1] - potentials[2], potentials[2] - potentials[0]],
            dtype=np.complex128,
        )
    return voltages


@ureg_wraps("V", ("V", None))
def calculate_voltages(potentials: ComplexArrayLike1D, phases: str) -> Q_[ComplexArray]:
    """Calculate the voltages between phases given the potentials of each phase.

    Args:
        potentials:
            Array-like of the complex potentials of each phase.

        phases:
            String of the phases in order. Can be one of:
            "ab", "bc", "ca", "an", "bn", "cn", "abn", "bcn", "can", "abc", "abcn".

    Returns:
        Array of the voltages between phases. If a neutral exists, the voltages are Phase-To-Neutral.
        Otherwise, the voltages are Phase-To-Phase.

    Example:
        >>> potentials = 230 * np.array([1, np.exp(-2j * np.pi / 3), np.exp(2j * np.pi / 3), 0], dtype=np.complex128)
        >>> calculate_voltages(potentials, "abcn")
        array([ 230.  +0.j        , -115.-199.18584287j, -115.+199.18584287j]) <Unit('volt')>
        >>> potentials = np.array([230, 230 * np.exp(-2j * np.pi / 3)], dtype=np.complex128)
        >>> calculate_voltages(potentials, "ab")
        array([345.+199.18584287j]) <Unit('volt')>
        >>> calculate_voltages(np.array([230, 0], dtype=np.complex128), "an")
        array([230.+0.j]) <Unit('volt')>
    """
    calculate_voltage_phases(phases)  # check if phases are valid
    return _calculate_voltages(np.asarray(potentials), phases)


_VOLTAGE_PHASES_CACHE = {
    "ab": ["ab"],
    "bc": ["bc"],
    "ca": ["ca"],
    "an": ["an"],
    "bn": ["bn"],
    "cn": ["cn"],
    "abn": ["an", "bn"],
    "bcn": ["bn", "cn"],
    "can": ["cn", "an"],
    "abc": ["ab", "bc", "ca"],
    "abcn": ["an", "bn", "cn"],
}
_PHASE_SIZES = {ph: len(ph_list) for ph, ph_list in _VOLTAGE_PHASES_CACHE.items()}


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
    try:
        return _VOLTAGE_PHASES_CACHE[phases]
    except KeyError:
        msg = f"Invalid phases '{phases}'. Must be one of {', '.join(_VOLTAGE_PHASES_CACHE)}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg, code=RoseauLoadFlowExceptionCode.BAD_PHASE) from None
