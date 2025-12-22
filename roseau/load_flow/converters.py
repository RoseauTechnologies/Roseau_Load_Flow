"""
This module provides helper functions to convert from one representation to another.

Available functions:

* convert potentials to voltages
"""

import logging

import numpy as np

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.typing import ComplexArray, ComplexArrayLike1D
from roseau.load_flow.units import Q_, ureg_wraps

logger = logging.getLogger(__name__)


def _calculate_voltages(potentials: ComplexArrayLike1D, phases: str) -> ComplexArray:
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
    return _calculate_voltages(np.asarray(potentials), phases)  # type: ignore


_VOLTAGE_PHASES_CACHE = {
    "a": ["a"],
    "b": ["b"],
    "c": ["c"],
    "n": ["n"],
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
