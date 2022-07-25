import numpy as np

from roseau.load_flow.utils.types import ConductorType, IsolationType

PI: float = np.pi
"""The famous constant."""

MU_0: float = 4 * PI * 1e-7
"""magnetic permeability of the vacuum (H/m)"""

EPSILON_0: float = 1e-9 / (36 * PI)
"""Relative permittivity of the vacuum (F/m)"""

F: float = 50.0
"""Network frequency (Hz)"""

OMEGA: float = 2 * PI * F
"""Pulsation (rad/s)"""

RHO: dict[ConductorType, float] = {
    ConductorType.CU: 1.72e-8,
    ConductorType.AL: 2.82e-8,
    ConductorType.AM: 3.26e-8,
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,
}  # TODO
"""Resistivity (ohm.m)"""

MU_R: dict[ConductorType, float] = {
    ConductorType.CU: 1.2566e-8,
    ConductorType.AL: 1.2566e-8,
    ConductorType.AM: 1.2566e-8,
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,
}  # TODO

"""Magnetic permeability (H/m)"""

DELTA_P: dict[ConductorType, float] = {
    ConductorType.CU: 9.3,
    ConductorType.AL: 112,
    ConductorType.AM: 12.9,
    ConductorType.AA: np.nan,  # TODO
    ConductorType.LA: np.nan,
}  # TODO

"""Skin effect (mm)"""

TAN_D: dict[IsolationType, float] = {
    IsolationType.PVC: 600e-4,
    IsolationType.HDPE: 6e-4,
    IsolationType.LDPE: 6e-4,
    IsolationType.PEX: 30e-4,
    IsolationType.EPR: 125e-4,
}
"""Loss angles"""

EPSILON_R: dict[IsolationType, float] = {
    IsolationType.PVC: 6.5,
    IsolationType.HDPE: 2.3,
    IsolationType.LDPE: 2.2,
    IsolationType.PEX: 2.5,
    IsolationType.EPR: 3.1,
}
"""Relative permittivity of the isolation"""

LV_MV_LIMIT: float = 1000.0  # Volts
"""The limit between low-voltages and high voltages. 1000.0V exactly is low voltages."""
