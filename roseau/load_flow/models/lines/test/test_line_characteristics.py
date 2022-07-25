import numpy as np
import numpy.linalg as nplin
import numpy.testing as npt
import pytest

from roseau.load_flow import LineCharacteristics
from roseau.load_flow.models.buses.buses import Bus
from roseau.load_flow.models.core.core import Ground
from roseau.load_flow.models.lines.lines import ShuntLine
from roseau.load_flow.utils.exceptions import ThundersValueError
from roseau.load_flow.utils.types import ConductorType, IsolationType, LineModel, LineType


def test_line_characteristics():
    bus = Bus(id_="junction", n=4)
    ground = Ground()

    # Real element off the diagonal (Z)
    z_line = np.ones(shape=(4, 4), dtype=np.complex_)
    y_shunt = np.eye(4, dtype=np.complex_)

    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line", n=4, bus1=bus, bus2=bus, ground=ground, line_characteristics=line_characteristics, length=2.5
        )
    assert e.value.args[0] == "The line impedance matrix of 'test' has off-diagonal elements with a non-zero real part."

    # Real element off the diagonal (Y)

    z_line = np.eye(3, dtype=np.complex_)
    y_shunt = np.ones(shape=(3, 3), dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line", n=3, bus1=bus, bus2=bus, ground=ground, line_characteristics=line_characteristics, length=2.5
        )
    assert (
        e.value.args[0] == "The shunt admittance matrix of 'test' has off-diagonal elements with a non-zero real part."
    )

    # Negative real values (Z)
    z_line = 2 * np.eye(4, dtype=np.complex_)
    z_line[1, 1] = -3
    y_shunt = -2 * np.eye(4, dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line", n=4, bus1=bus, bus2=bus, ground=ground, line_characteristics=line_characteristics, length=2.4
        )
    assert e.value.args[0] == "Some real part coefficients of the line impedance matrix of 'test' are negative..."

    # Negative real values (Y)
    y_shunt = 2 * np.eye(3, dtype=np.complex_)
    y_shunt[1, 1] = -3
    with pytest.raises(ThundersValueError):
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line", n=4, bus1=bus, bus2=bus, ground=ground, line_characteristics=line_characteristics, length=2.4
        )
    assert e.value.args[0] == "Some real part coefficients of the line impedance matrix of 'test' are negative..."

    # Bad shape (LV - Z)
    z_line = np.eye(4, dtype=np.complex_)[:, :2]
    y_shunt = np.eye(4, dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line", n=4, bus1=bus, bus2=bus, ground=ground, line_characteristics=line_characteristics, length=2.4
        )
    assert e.value.args[0] == "Incorrect z_line dimensions for line characteristics 'test': (4, 2)"

    # Bad shape (LV - Y)
    z_line = np.eye(4, dtype=np.complex_)
    y_shunt = np.eye(3, dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line",
            n=4,
            bus1=bus,
            bus2=bus,
            ground=ground,
            line_characteristics=line_characteristics,
            length=2.4,
        )
    assert e.value.args[0] == "Incorrect y_shunt dimensions for line 'line': (3, 3) instead of (4, 4)"

    # Bad shape (MV - Z)
    z_line = np.eye(4, dtype=np.complex_)[:, :2]
    y_shunt = np.eye(3, dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line",
            n=3,
            bus1=bus,
            bus2=bus,
            ground=ground,
            line_characteristics=line_characteristics,
            length=2.4,
        )
    assert e.value.args[0] == "Incorrect z_line dimensions for line characteristics 'test': (4, 2)"

    # Bad shape (MV - Y)
    z_line = np.eye(3, dtype=np.complex_)
    y_shunt = np.eye(6, dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line",
            n=3,
            bus1=bus,
            bus2=bus,
            ground=ground,
            line_characteristics=line_characteristics,
            length=2.4,
        )
    assert e.value.args[0] == "Incorrect y_shunt dimensions for line 'line': (6, 6) instead of (3, 3)"

    # LV line with not zero shunt admittance
    z_line = np.eye(3, dtype=np.complex_)
    y_shunt = np.eye(3, dtype=np.complex_)
    with pytest.raises(ThundersValueError) as e:
        line_characteristics = LineCharacteristics("test", z_line, y_shunt)
        ShuntLine(
            id_="line",
            n=4,
            bus1=bus,
            bus2=bus,
            ground=ground,
            line_characteristics=line_characteristics,
            length=2.4,
        )
    assert e.value.args[0] == "Incorrect z_line dimensions for line 'line': (3, 3) instead of (4, 4)"


def test_bad_model():
    # Unknown line model
    data = {"model": "unknown", "name": "test"}
    with pytest.raises(ThundersValueError):
        LineCharacteristics.from_dict(data=data)


def test_lv_exact():
    line_data = {
        "name": "test",
        "type": LineType.OVERHEAD,
        "section": 150,
        "section_n": 70,
        "dpp": 0,
        "dpn": 0,
        "height": 10,
        "dext": 0.04,
        "dsh": 0.04,
        "conductor": ConductorType.AL,
        "isolation": IsolationType.PEX,
        "model": LineModel.LV_EXACT,
    }

    # Working example
    z_line, y_shunt, model = LineCharacteristics.lv_exact_to_zy(type_name="test", line_data=line_data)
    y_line_expected = np.array(
        [
            [3.3915102901533754, -1.2233003903972888, -1.2233003903972615, -0.7121721195595286],
            [-1.2233003903972892, 3.391510290153375, -1.2233003903972615, -0.7121721195595287],
            [-1.2233003903972615, -1.2233003903972612, 3.391510290153371, -0.7121721195595507],
            [-0.7121721195595287, -0.7121721195595287, -0.7121721195595507, 2.098835790241813],
        ]
    ) + 1j * np.array(
        [
            [-1.5097083093938377, 0.29317485508286, 0.2931748550828966, -0.05601082045448763],
            [0.29317485508285984, -1.509708309393838, 0.29317485508289676, -0.0560108204544873],
            [0.2931748550828965, 0.2931748550828968, -1.509708309393831, -0.056010820454528876],
            [-0.056010820454487645, -0.05601082045448755, -0.056010820454528834, -0.3005121042954534],
        ]
    )
    npt.assert_allclose(z_line, nplin.inv(y_line_expected))
    y_shunt_expected = np.array(
        [
            [
                9.88365369e-08 + 4.88246547e-05j,
                -0.00000000e00 - 1.92652134e-06j,
                -0.00000000e00 - 1.92555213e-06j,
                -0.00000000e00 - 1.20270689e-05j,
            ],
            [
                -0.00000000e00 - 1.92652134e-06j,
                9.88365369e-08 + 4.88246547e-05j,
                -0.00000000e00 - 1.92555213e-06j,
                -0.00000000e00 - 1.20270689e-05j,
            ],
            [
                -0.00000000e00 - 1.92555213e-06j,
                -0.00000000e00 - 1.92555213e-06j,
                9.88422745e-08 + 4.88265397e-05j,
                -0.00000000e00 - 1.20280106e-05j,
            ],
            [
                -0.00000000e00 - 1.20270689e-05j,
                -0.00000000e00 - 1.20270689e-05j,
                -0.00000000e00 - 1.20280106e-05j,
                2.13032359e-07 + 1.07092935e-04j,
            ],
        ]
    )
    npt.assert_allclose(y_shunt, y_shunt_expected)
    assert model == LineModel.LV_EXACT

    line_data = {
        "name": "test",
        "type": LineType.UNDERGROUND,
        "section": 150,
        "section_n": 70,
        "dpp": 0,
        "dpn": 0,
        "height": -1.5,
        "dext": 0.049,
        "dsh": 0.04,
        "conductor": ConductorType.AL,
        "isolation": IsolationType.PVC,
        "model": LineModel.LV_EXACT,
    }

    # Working example
    z_line, y_shunt, model = LineCharacteristics.lv_exact_to_zy(type_name="test", line_data=line_data)
    y_line_expected = np.array(
        [
            [3.218429448662283, -1.329262437638587, -1.0144886997705809, -0.6708409749422017],
            [-1.329262437638587, 3.3132903818151664, -1.3292624376385969, -0.5071931750041125],
            [-1.0144886997705809, -1.329262437638597, 3.218429448662286, -0.6708409749421965],
            [-0.6708409749422021, -0.5071931750041122, -0.6708409749421965, 2.0134069034544098],
        ]
    ) + 1j * np.array(
        [
            [-1.6513767151219196, 0.16540589778392523, 0.4929007890271932, -0.038590931317931176],
            [0.16540589778392534, -1.5534190611819065, 0.1654058977839179, 0.20837873067712712],
            [0.49290078902719336, 0.16540589778391795, -1.6513767151219172, -0.03859093131792596],
            [-0.03859093131793137, 0.20837873067712717, -0.03859093131792582, -0.6182914857776997],
        ]
    )
    npt.assert_allclose(z_line, nplin.inv(y_line_expected))
    y_shunt_expected = np.array(
        [
            [
                1.90627193e-05 + 4.58276186e-04j,
                -0.00000000e00 - 7.47170855e-05j,
                -0.00000000e00 - 2.09865188e-05j,
                -0.00000000e00 - 4.48605942e-05j,
            ],
            [
                -0.00000000e00 - 7.47170855e-05j,
                2.06105773e-05 + 4.99042392e-04j,
                -0.00000000e00 - 7.47170855e-05j,
                -0.00000000e00 - 6.09859898e-06j,
            ],
            [
                -0.00000000e00 - 2.09865188e-05j,
                -0.00000000e00 - 7.47170855e-05j,
                1.90627193e-05 + 4.58276186e-04j,
                -0.00000000e00 - 4.48605942e-05j,
            ],
            [
                -0.00000000e00 - 4.48605942e-05j,
                -0.00000000e00 - 6.09859898e-06j,
                -0.00000000e00 - 4.48605942e-05j,
                1.26671519e-05 + 3.06938986e-04j,
            ],
        ]
    )

    npt.assert_allclose(y_shunt, y_shunt_expected)
    assert model == LineModel.LV_EXACT


def test_sym():
    # With the bad model of PwF
    line_data = {
        "name": "NKBA NOR  25.00 kV",
        "un": 25000.0,
        "in": 277.0000100135803,
        "r0": 0.0,
        "x0": 0.0,
        "r1": 1.0,
        "x1": 1.0,
        "rn": 0.0,
        "xn": 0.0,
        "xpn": 0.0,
        "b0": 0.0,
        "g0": 0.0,
        "b1": 1e-06,
        "g1": 0.0,
        "bn": 0.0,
        "bpn": 0.0,
        "model": LineModel.SYM,
    }

    z_line, y_shunt, model = LineCharacteristics.sym_to_zy(type_name="NKBA NOR  25.00 kV", line_data=line_data)
    z_line_expected = (1 + 1j) * np.eye(3)
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = 1e-6j * np.eye(3)
    npt.assert_allclose(y_shunt, y_shunt_expected)
    assert model == LineModel.SYM

    line_data = {
        "name": "NKBA 4x150   1.00 kV",
        "un": 1000.0,
        "in": 361.0000014305115,
        "r0": 0.5,
        "x0": 0.3050000071525574,
        "r1": 0.125,
        "x1": 0.0860000029206276,
        "rn": 0.0,
        "xn": 0.0,
        "xpn": 0.0,
        "b0": 0.0,
        "g0": 0.0,
        "b1": 0.0,
        "g1": 0.0,
        "bn": 0.0,
        "bpn": 0.0,
        "model": LineModel.SYM_NEUTRAL,
    }

    z_line, y_shunt, model = LineCharacteristics.sym_to_zy(type_name="NKBA 4x150   1.00 kV", line_data=line_data)
    z_line_expected = np.array(
        [
            [0.25 + 0.159j, 0.125 + 0.073j, 0.125 + 0.073j],
            [0.125 + 0.073j, 0.25 + 0.159j, 0.125 + 0.073j],
            [0.125 + 0.073j, 0.125 + 0.073j, 0.25 + 0.159j],
        ],
        dtype=np.complex_,
    )
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = np.zeros(shape=(3, 3), dtype=np.complex_)
    npt.assert_allclose(y_shunt, y_shunt_expected)
    assert model == LineModel.SYM  # Downgraded model because of PwF bad data

    # First line
    line_data = {
        "name": "sym_neutral_underground_line_example",
        "un": 400.0,
        "in": 150,
        "r0": 0.188,
        "x0": 0.8224,
        "r1": 0.188,
        "x1": 0.0812,
        "rn": 0.4029,
        "xn": 0.3522,
        "xpn": 0.2471,
        "b0": 0.000063134,
        "g0": 0.000010462,
        "b1": 0.00022999,
        "g1": 0.000010462,
        "bn": 0.00011407,
        "bpn": -0.000031502,
        "model": LineModel.SYM_NEUTRAL,
    }

    z_line, y_shunt, model = LineCharacteristics.sym_to_zy(
        type_name="sym_neutral_underground_line_example", line_data=line_data
    )
    z_line_expected = np.array(
        [
            [0.188 + 0.32826667j, 0.0 + 0.24706667j, 0.0 + 0.24706667j, 0.0 + 0.2471j],
            [0.0 + 0.24706667j, 0.188 + 0.32826667j, 0.0 + 0.24706667j, 0.0 + 0.2471j],
            [0.0 + 0.24706667j, 0.0 + 0.24706667j, 0.188 + 0.32826667j, 0.0 + 0.2471j],
            [
                0.0 + 0.2471j,
                0.0 + 0.2471j,
                0.0 + 0.2471j,
                0.4029 + 0.3522j,
            ],
        ]
    )
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = np.array(
        [
            [1.0462e-05 + 1.74371333e-04j, 0 - 5.56186667e-05j, 0 - 5.56186667e-05j, -0 - 3.15020000e-05j],
            [0 - 5.56186667e-05j, 1.0462e-05 + 1.74371333e-04j, 0 - 5.56186667e-05j, -0 - 3.15020000e-05j],
            [0 - 5.56186667e-05j, 0 - 5.56186667e-05j, 1.0462e-05 + 1.74371333e-04j, -0 - 3.15020000e-05j],
            [-0 - 3.15020000e-05j, -0 - 3.15020000e-05j, -0 - 3.15020000e-05j, 0 + 1.14070000e-04j],
        ]
    )
    npt.assert_allclose(y_shunt, y_shunt_expected)
    assert model == LineModel.SYM_NEUTRAL

    # Second line
    line_data = {
        "name": "sym_line_example",
        "un": 20000.0,
        "in": 309,
        "r0": 0.2,
        "x0": 0.1,
        "r1": 0.2,
        "x1": 0.1,
        "rn": 0.4029,
        "b0": 0.00014106,
        "g0": 0.0,
        "b1": 0.00014106,
        "g1": 0.0,
        "model": LineModel.SYM,
    }

    z_line, y_shunt, model = LineCharacteristics.sym_to_zy(type_name="sym_line_example", line_data=line_data)
    z_line_expected = (0.2 + 0.1j) * np.eye(3)
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = 0.00014106j * np.eye(3)
    npt.assert_allclose(y_shunt, y_shunt_expected)
    assert model == LineModel.SYM
