import numpy as np

from roseau.load_flow.utils.types import ConductorType, IsolationType
from roseau.load_flow.utils.units import Q_

PI: float = np.pi
"""The famous constant."""

MU_0: float = Q_(4 * PI * 1e-7, "H/m")
"""magnetic permeability of the vacuum (H/m)"""

EPSILON_0: float = Q_(1e-9 / (36 * PI), "F/m")
"""Relative permittivity of the vacuum (F/m)"""

F: float = Q_(50.0, "Hz")
"""Network frequency (Hz)"""

OMEGA: float = Q_(2 * PI * F, "rad/s")
"""Pulsation (rad/s)"""

RHO: dict[ConductorType, float] = {
    ConductorType.CU: Q_(1.72e-8, "ohm*m"),
    ConductorType.AL: Q_(2.82e-8, "ohm*m"),
    ConductorType.AM: Q_(3.26e-8, "ohm*m"),
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,
}  # TODO
"""Resistivity (ohm.m)"""

MU_R: dict[ConductorType, float] = {
    ConductorType.CU: Q_(1.2566e-8, "H/m"),
    ConductorType.AL: Q_(1.2566e-8, "H/m"),
    ConductorType.AM: Q_(1.2566e-8, "H/m"),
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,
}  # TODO

"""Magnetic permeability (H/m)"""

DELTA_P: dict[ConductorType, float] = {
    ConductorType.CU: Q_(9.3, "mm"),
    ConductorType.AL: Q_(112, "mm"),
    ConductorType.AM: Q_(12.9, "mm"),
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,
}  # TODO

"""Skin effect (mm)"""

TAN_D: dict[IsolationType, float] = {
    IsolationType.PVC: Q_(600e-4),
    IsolationType.HDPE: Q_(6e-4),
    IsolationType.LDPE: Q_(6e-4),
    IsolationType.PEX: Q_(30e-4),
    IsolationType.EPR: Q_(125e-4),
}
"""Loss angles"""

EPSILON_R: dict[IsolationType, float] = {
    IsolationType.PVC: Q_(6.5),
    IsolationType.HDPE: Q_(2.3),
    IsolationType.LDPE: Q_(2.2),
    IsolationType.PEX: Q_(2.5),
    IsolationType.EPR: Q_(3.1),
}
"""Relative permittivity of the isolation"""

LV_MV_LIMIT: float = Q_(1000.0, "V")  # Volts
"""The limit between low-voltages and high voltages. 1000.0V exactly is low voltages."""
