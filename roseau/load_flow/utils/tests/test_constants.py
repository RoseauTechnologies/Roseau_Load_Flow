from roseau.load_flow.utils.constants import DELTA_P, EPSILON_R, MU_R, RHO, TAN_D
from roseau.load_flow.utils.types import Insulator, Material


def test_constants():
    for x in Material:
        assert x in MU_R
        assert x in RHO
        assert x in DELTA_P

    for x in Insulator:
        assert x in TAN_D
        assert x in EPSILON_R
