import numpy as np

from roseau.load_flow.models import Bus, Transformer, TransformerParameters


def test_res_violated():
    bus1 = Bus("bus1", phases="abc")
    bus2 = Bus("bus2", phases="abcn")
    tp = TransformerParameters.from_tests(
        id="tp", psc=1350.0, p0=145.0, i0=1.8 / 100, ulv=400, uhv=20000, sn=50 * 1e3, vsc=4 / 100, type="yzn11"
    )
    transformer = Transformer(id="transformer", bus1=bus1, bus2=bus2, parameters=tp)
    direct_seq = np.exp([0, -2 / 3 * np.pi * 1j, 2 / 3 * np.pi * 1j])
    direct_seq_neutral = np.concatenate([direct_seq, [0]])

    bus1._res_potentials = 20_000 * direct_seq
    bus2._res_potentials = 230 * direct_seq_neutral
    transformer._res_currents = 0.8 * direct_seq, -65 * direct_seq_neutral

    # No limits
    assert transformer.res_violated is None

    # No constraint violated
    tp.max_power = 50_000
    assert transformer.res_violated is False

    # Two violations
    tp.max_power = 40_000
    assert transformer.res_violated is True

    # Primary side violation
    tp.max_power = 47_900
    assert transformer.res_violated is True

    # Secondary side violation
    tp.max_power = 50_000
    transformer._res_currents = 0.8 * direct_seq, -80 * direct_seq_neutral
    assert transformer.res_violated is True
