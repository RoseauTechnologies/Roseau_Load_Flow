import numpy as np

from roseau.load_flow.units import Q_
from roseau.load_flow.utils.types import ConductorType, InsulatorType, LineType

PI = np.pi
"""The famous mathematical constant :math:`\\pi = 3.141592\\ldots`."""

MU_0 = Q_(1.25663706212e-6, "H/m")
"""Magnetic permeability of the vacuum :math:`\\mu_0 = 4 \\pi \\times 10^{-7}` (H/m)."""

EPSILON_0 = Q_(8.8541878128e-12, "F/m")
"""Vacuum permittivity :math:`\\varepsilon_0 =  8.8541878128 \\times 10^{-12}` (F/m)."""

F = Q_(50.0, "Hz")
"""Network frequency :math:`f = 50` (Hz)."""

OMEGA = Q_(2 * PI * F, "rad/s")
"""Angular frequency :math:`\\omega = 2 \\pi f` (rad/s)."""

CX = {
    LineType.OVERHEAD: Q_(0.35, "ohm/km"),
    LineType.UNDERGROUND: Q_(0.1, "ohm/km"),
    LineType.TWISTED: Q_(0.1, "ohm/km"),
}
"""Coiffier's reactance parameter for a typical line in France (Ohm/km)."""

RHO = {
    ConductorType.CU: Q_(1.72e-8, "ohm*m"),  # verified
    ConductorType.AL: Q_(2.65e-8, "ohm*m"),  # verified
    ConductorType.AM: Q_(3.26e-8, "ohm*m"),  # verified
    ConductorType.AA: Q_(4.0587e-8, "ohm*m"),  # verified (approx. AS 3607 ACSR/GZ)
    ConductorType.LA: Q_(3.26e-8, "ohm*m"),
}
"""Resistivity of common conductor materials (Ohm.m)."""

MU_R = {
    ConductorType.CU: Q_(0.9999935849131266),
    ConductorType.AL: Q_(1.0000222328028834),
    ConductorType.AM: Q_(0.9999705074463784),
    ConductorType.AA: Q_(1.0000222328028834),  # ==AL
    ConductorType.LA: Q_(0.9999705074463784),  # ==AM
}
"""Relative magnetic permeability of common conductor materials."""

DELTA_P = {
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

TAN_D = {it: Q_(np.nan) for it in InsulatorType}
"""Loss angles of common insulator materials."""
TAN_D |= {
    InsulatorType.PVC: Q_(600e-4),
    InsulatorType.HDPE: Q_(6e-4),
    InsulatorType.MDPE: Q_(6e-4),
    InsulatorType.LDPE: Q_(6e-4),
    InsulatorType.XLPE: Q_(30e-4),
    InsulatorType.EPR: Q_(125e-4),
}

EPSILON_R = {it: Q_(np.nan) for it in InsulatorType}
"""Relative permittivity of common insulator materials."""
EPSILON_R |= {
    InsulatorType.PVC: Q_(6.5),
    InsulatorType.HDPE: Q_(2.3),
    InsulatorType.MDPE: Q_(2.3),
    InsulatorType.LDPE: Q_(2.2),
    InsulatorType.XLPE: Q_(2.5),
    InsulatorType.EPR: Q_(3.1),
}
