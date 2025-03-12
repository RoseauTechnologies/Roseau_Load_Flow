"""Physical and mathematical constants used in the load flow calculations."""

import cmath
import math
from typing import Final

from roseau.load_flow.types import Insulator, Material
from roseau.load_flow.units import Q_

__all__ = [
    # Mathematical constants
    "SQRT3",
    "ALPHA",
    "ALPHA2",
    "PI",
    "CLOCK_PHASE_SHIFT",
    # Physical constants
    "MU_0",
    "MU_R",
    "EPSILON_0",
    "EPSILON_R",
    "F",
    "OMEGA",
    "RHO",
    "TAN_D",
    "DELTA_P",
]

SQRT3: Final = math.sqrt(3)
"""The square root of 3."""

ALPHA: Final = cmath.exp(2 / 3 * cmath.pi * 1j)
"""complex: Phasor rotation operator :math:`\\alpha`, which rotates a phasor vector counterclockwise
by 120 degrees when multiplied by it."""

ALPHA2: Final = ALPHA**2
"""complex: Phasor rotation operator :math:`\\alpha^2`, which rotates a phasor vector clockwise by
120 degrees when multiplied by it."""

PI: Final = math.pi
"""The famous mathematical constant :math:`\\pi = 3.141592\\ldots`."""

CLOCK_PHASE_SHIFT: Final = {clock: cmath.exp(-1j * clock * cmath.pi / 6) for clock in (0, 1, 2, 4, 5, 6, 7, 8, 10, 11)}
"""Phase shift for each clock number in the transformer vector group notation."""

MU_0: Final = Q_(1.25663706212e-6, "H/m")
"""Magnetic permeability of the vacuum :math:`\\mu_0 = 4 \\pi \\times 10^{-7}` (H/m)."""

EPSILON_0: Final = Q_(8.8541878128e-12, "F/m")
"""Vacuum permittivity :math:`\\varepsilon_0 =  8.8541878128 \\times 10^{-12}` (F/m)."""

F: Final = Q_(50.0, "Hz")
"""Network frequency :math:`f = 50` (Hz)."""

OMEGA: Final = Q_(2 * PI * F, "rad/s")
"""Angular frequency :math:`\\omega = 2 \\pi f` (rad/s)."""

RHO: Final[dict[Material, Q_[float]]] = {
    Material.CU: Q_(1.7241e-8, "ohm*m"),  # IEC 60287-1-1 Table 1
    Material.AL: Q_(2.8264e-8, "ohm*m"),  # IEC 60287-1-1 Table 1
    Material.AM: Q_(3.26e-8, "ohm*m"),  # verified
    Material.AA: Q_(4.0587e-8, "ohm*m"),  # verified (approx. AS 3607 ACSR/GZ)
    Material.LA: Q_(3.26e-8, "ohm*m"),
}
"""Resistivity of common conductor materials (Ohm.m)."""

MU_R: Final[dict[Material, Q_[float]]] = {
    Material.CU: Q_(0.9999935849131266),
    Material.AL: Q_(1.0000222328028834),
    Material.AM: Q_(0.9999705074463784),
    Material.AA: Q_(1.0000222328028834),  # ==AL
    Material.LA: Q_(0.9999705074463784),  # ==AM
}
"""Relative magnetic permeability of common conductor materials."""

DELTA_P: Final[dict[Material, Q_[float]]] = {
    Material.CU: Q_(9.33, "mm"),
    Material.AL: Q_(11.95, "mm"),
    Material.AM: Q_(12.85, "mm"),
    Material.AA: Q_(14.34, "mm"),
    Material.LA: Q_(12.85, "mm"),
}
"""Skin depth of common conductor materials :math:`\\sqrt{\\dfrac{\\rho}{\\pi f \\mu_r \\mu_0}}` (mm)."""
# Skin depth is the depth at which the current density is reduced to 1/e (~37%) of the surface value.
# Generated with:
# ---------------
# def delta_p(rho, mu_r):
#     return np.sqrt(rho / (PI * F * mu_r * MU_0))
# for material in Material:
#     print(material, delta_p(RHO[material], MU_R[material]).m_as("mm"))

TAN_D: Final[dict[Insulator, Q_[float]]] = {
    Insulator.PVC: Q_(1000e-4),
    Insulator.HDPE: Q_(10e-4),
    Insulator.MDPE: Q_(10e-4),
    Insulator.LDPE: Q_(10e-4),
    Insulator.XLPE: Q_(40e-4),
    Insulator.EPR: Q_(200e-4),
    Insulator.IP: Q_(100e-4),
    Insulator.NONE: Q_(0),
}
"""Loss angles of common insulator materials according to the IEC 60287 standard."""
# IEC 60287-1-1 Table 3. We only include the MV values.

EPSILON_R: Final[dict[Insulator, Q_[float]]] = {
    Insulator.PVC: Q_(8.0),
    Insulator.HDPE: Q_(2.3),
    Insulator.MDPE: Q_(2.3),
    Insulator.LDPE: Q_(2.3),
    Insulator.XLPE: Q_(2.5),
    Insulator.EPR: Q_(3.0),
    Insulator.IP: Q_(4.0),
    Insulator.NONE: Q_(1.0),
}
"""Relative permittivity of common insulator materials according to the IEC 60287 standard."""
# IEC 60287-1-1 Table 3. We only include the MV values.


def __getattr__(name: str):
    import warnings

    from roseau.load_flow.utils import find_stack_level

    if name in ("PositiveSequence", "NegativeSequence", "ZeroSequence"):
        warnings.warn(
            f"'rlf.constants.{name}' is deprecated. Use 'rlf.sym.{name}' instead.",
            category=FutureWarning,
            stacklevel=find_stack_level(),
        )
        from roseau.load_flow import sym

        return getattr(sym, name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
