import numpy as np

from roseau.load_flow.units import Q_
from roseau.load_flow.utils.types import ConductorType, InsulatorType, LineType

PI = np.pi
"""The famous constant :math:`\\pi`."""

MU_0 = Q_(1.25663706212e-6, "H/m")
"""Magnetic permeability of the vacuum (H/m)."""

EPSILON_0 = Q_(8.8541878128e-12, "F/m")
"""Permittivity of the vacuum (F/m)."""

F = Q_(50.0, "Hz")
"""Network frequency :math:`=50` (Hz)."""

OMEGA = Q_(2 * PI * F, "rad/s")
"""Pulsation :math:`\\omega = 2 \\pi f` (rad/s)."""

RHO = {
    ConductorType.CU: Q_(1.72e-8, "ohm*m"),
    ConductorType.AL: Q_(2.82e-8, "ohm*m"),
    ConductorType.AM: Q_(3.26e-8, "ohm*m"),
    ConductorType.AA: Q_(4.0587e-8, "ohm*m"),
    ConductorType.LA: Q_(3.26e-8, "ohm*m"),
}
"""Resistivity of common conductor materials (ohm.m)."""

CX = {
    LineType.OVERHEAD: Q_(0.35, "ohm/km"),
    LineType.UNDERGROUND: Q_(0.1, "ohm/km"),
    LineType.TWISTED: Q_(0.1, "ohm/km"),
}
"""Reactance parameter for a typical line in France (Ohm/km)."""

MU_R = {
    ConductorType.CU: Q_(1.2566e-8, "H/m"),
    ConductorType.AL: Q_(1.2566e-8, "H/m"),
    ConductorType.AM: Q_(1.2566e-8, "H/m"),
    ConductorType.AA: Q_(np.nan, "H/m"),  # TODO
    ConductorType.LA: Q_(np.nan, "H/m"),  # TODO
}
"""Magnetic permeability of common conductor materials (H/m)."""

DELTA_P = {
    ConductorType.CU: Q_(9.3, "mm"),
    ConductorType.AL: Q_(112, "mm"),
    ConductorType.AM: Q_(12.9, "mm"),
    ConductorType.AA: Q_(np.nan, "mm"),  # TODO
    ConductorType.LA: Q_(np.nan, "mm"),  # TODO
}
"""Skin effect of common conductor materials (mm)."""

TAN_D = {
    InsulatorType.PVC: Q_(600e-4),
    InsulatorType.HDPE: Q_(6e-4),
    InsulatorType.LDPE: Q_(6e-4),
    InsulatorType.PEX: Q_(30e-4),
    InsulatorType.EPR: Q_(125e-4),
}
"""Loss angles of common insulator materials."""

EPSILON_R = {
    InsulatorType.PVC: Q_(6.5),
    InsulatorType.HDPE: Q_(2.3),
    InsulatorType.LDPE: Q_(2.2),
    InsulatorType.PEX: Q_(2.5),
    InsulatorType.EPR: Q_(3.1),
}
"""Relative permittivity of common insulator materials."""
