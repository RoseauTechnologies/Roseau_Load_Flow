from roseau.load_flow.utils.constants import DELTA_P, EPSILON_R, MU_R, RHO, TAN_D
from roseau.load_flow.utils.types import ConductorType, InsulatorType


def test_constants():
    for x in ConductorType:
        assert x in MU_R
        assert x in RHO
        assert x in DELTA_P

    for x in InsulatorType:
        if x == InsulatorType.UNKNOWN:
            continue
        assert x in TAN_D
        assert x in EPSILON_R
