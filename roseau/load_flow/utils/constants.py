import numpy as np

from roseau.load_flow.units import Q_
from roseau.load_flow.utils.types import ConductorType, InsulationType, LineType

PI = np.pi
"""The famous constant :math:`\\pi`."""

MU_0 = Q_(4 * PI * 1e-7, "H/m")
"""magnetic permeability of the vacuum (H/m)."""

EPSILON_0 = Q_(1e-9 / (36 * PI), "F/m")
"""Relative permittivity of the vacuum (F/m)."""

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
"""Resistivity of certain conductor materials (ohm.m)."""

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
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,  # TODO
}
"""Magnetic permeability of certain conductor materials (H/m)."""

DELTA_P = {
    ConductorType.CU: Q_(9.3, "mm"),
    ConductorType.AL: Q_(112, "mm"),
    ConductorType.AM: Q_(12.9, "mm"),
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,  # TODO
}
"""Skin effect of certain conductor materials (mm)."""

TAN_D = {
    InsulationType.PVC: Q_(600e-4),
    InsulationType.HDPE: Q_(6e-4),
    InsulationType.LDPE: Q_(6e-4),
    InsulationType.PEX: Q_(30e-4),
    InsulationType.EPR: Q_(125e-4),
}
"""Loss angles of certain insulation materials."""

EPSILON_R = {
    InsulationType.PVC: Q_(6.5),
    InsulationType.HDPE: Q_(2.3),
    InsulationType.LDPE: Q_(2.2),
    InsulationType.PEX: Q_(2.5),
    InsulationType.EPR: Q_(3.1),
}
"""Relative permittivity of certain insulation materials."""
