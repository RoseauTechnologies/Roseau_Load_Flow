import cmath

import numpy as np

from roseau.load_flow.units import Q_
from roseau.load_flow.utils.types import ConductorType, InsulatorType

PI: float = cmath.pi
"""The famous mathematical constant :math:`\\pi = 3.141592\\ldots`."""

ALPHA: complex = cmath.exp(2 / 3 * PI * 1j)
"""complex: Phasor rotation operator :math:`\\alpha`, which rotates a phasor vector counterclockwise
by 120 degrees when multiplied by it."""

ALPHA2: complex = ALPHA**2
"""complex: Phasor rotation operator :math:`\\alpha^2`, which rotates a phasor vector clockwise by
120 degrees when multiplied by it."""

PositiveSequence = np.array([1, ALPHA2, ALPHA], dtype=np.complex128)
"""numpy.ndarray[complex]: Unit positive sequence components of a three-phase system."""
NegativeSequence = np.array([1, ALPHA, ALPHA2], dtype=np.complex128)
"""numpy.ndarray[complex]: Unit negative sequence components of a three-phase system."""
ZeroSequence = np.array([1, 1, 1], dtype=np.complex128)
"""numpy.ndarray[complex]: Unit zero sequence components of a three-phase system."""

MU_0: Q_[float] = Q_(1.25663706212e-6, "H/m")
"""Magnetic permeability of the vacuum :math:`\\mu_0 = 4 \\pi \\times 10^{-7}` (H/m)."""

EPSILON_0: Q_[float] = Q_(8.8541878128e-12, "F/m")
"""Vacuum permittivity :math:`\\varepsilon_0 =  8.8541878128 \\times 10^{-12}` (F/m)."""

F: Q_[float] = Q_(50.0, "Hz")
"""Network frequency :math:`f = 50` (Hz)."""

OMEGA: Q_[float] = Q_(2 * PI * F, "rad/s")
"""Angular frequency :math:`\\omega = 2 \\pi f` (rad/s)."""

RHO: dict[ConductorType, Q_[float]] = {
    ConductorType.CU: Q_(1.7241e-8, "ohm*m"),  # IEC 60287-1-1 Table 1
    ConductorType.AL: Q_(2.8264e-8, "ohm*m"),  # IEC 60287-1-1 Table 1
    ConductorType.AM: Q_(3.26e-8, "ohm*m"),  # verified
    ConductorType.AA: Q_(4.0587e-8, "ohm*m"),  # verified (approx. AS 3607 ACSR/GZ)
    ConductorType.LA: Q_(3.26e-8, "ohm*m"),
}
"""Resistivity of common conductor materials (Ohm.m)."""

MU_R: dict[ConductorType, Q_[float]] = {
    ConductorType.CU: Q_(0.9999935849131266),
    ConductorType.AL: Q_(1.0000222328028834),
    ConductorType.AM: Q_(0.9999705074463784),
    ConductorType.AA: Q_(1.0000222328028834),  # ==AL
    ConductorType.LA: Q_(0.9999705074463784),  # ==AM
}
"""Relative magnetic permeability of common conductor materials."""

DELTA_P: dict[ConductorType, Q_[float]] = {
    ConductorType.CU: Q_(9.33, "mm"),
    ConductorType.AL: Q_(11.95, "mm"),
    ConductorType.AM: Q_(12.85, "mm"),
    ConductorType.AA: Q_(14.34, "mm"),
    ConductorType.LA: Q_(12.85, "mm"),
}
"""Skin depth of common conductor materials :math:`\\sqrt{\\dfrac{\\rho}{\\pi f \\mu_r \\mu_0}}` (mm)."""
# Skin depth is the depth at which the current density is reduced to 1/e (~37%) of the surface value.
# Generated with:
# ---------------
# def delta_p(rho, mu_r):
#     return np.sqrt(rho / (PI * F * mu_r * MU_0))
# for material in ConductorType:
#     print(material, delta_p(RHO[material], MU_R[material]).m_as("mm"))

TAN_D: dict[InsulatorType, Q_[float]] = {
    InsulatorType.PVC: Q_(1000e-4),
    InsulatorType.HDPE: Q_(10e-4),
    InsulatorType.MDPE: Q_(10e-4),
    InsulatorType.LDPE: Q_(10e-4),
    InsulatorType.XLPE: Q_(40e-4),
    InsulatorType.EPR: Q_(200e-4),
    InsulatorType.IP: Q_(100e-4),
    InsulatorType.UNKNOWN: Q_(0),
}
"""Loss angles of common insulator materials according to the IEC 60287 standard."""
# IEC 60287-1-1 Table 3. We only include the MV values.

EPSILON_R: dict[InsulatorType, Q_[float]] = {
    InsulatorType.PVC: Q_(8.0),
    InsulatorType.HDPE: Q_(2.3),
    InsulatorType.MDPE: Q_(2.3),
    InsulatorType.LDPE: Q_(2.3),
    InsulatorType.XLPE: Q_(2.5),
    InsulatorType.EPR: Q_(3.0),
    InsulatorType.IP: Q_(4.0),
    InsulatorType.UNKNOWN: Q_(1.0),
}
"""Relative permittivity of common insulator materials according to the IEC 60287 standard."""
# IEC 60287-1-1 Table 3. We only include the MV values.
