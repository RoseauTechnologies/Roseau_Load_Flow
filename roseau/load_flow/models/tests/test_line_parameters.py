import json
import re

import numpy as np
import numpy.linalg as nplin
import numpy.testing as npt
import pandas as pd
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineParameters
from roseau.load_flow.units import Q_
from roseau.load_flow.utils import ConductorType, InsulatorType, LineType


def test_line_parameters():
    bus1 = Bus(id="junction1", phases="abcn")
    bus2 = Bus(id="junction2", phases="abcn")
    ground = Ground("ground")

    # Real element off the diagonal (Z)
    z_line = np.ones(shape=(4, 4), dtype=complex)
    y_shunt = np.eye(4, dtype=complex)
    with pytest.warns(UserWarning, match=r"z_line .* has off-diagonal elements with a non-zero"):
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)

    # Real element off the diagonal (Y)
    z_line = np.eye(3, dtype=complex)
    y_shunt = np.ones(shape=(3, 3), dtype=complex)
    with pytest.warns(UserWarning, match=r"y_shunt .* has off-diagonal elements with a non-zero"):
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)

    # Negative real values (Z)
    z_line = 2 * np.eye(4, dtype=complex)
    z_line[1, 1] = -3
    y_shunt = -2 * np.eye(4, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE
    assert e.value.msg == "The z_line matrix of line type 'test' has coefficients with negative real part."

    # Negative real values (Y)
    y_shunt = 2 * np.eye(3, dtype=complex)
    y_shunt[1, 1] = -3
    with pytest.raises(RoseauLoadFlowException):
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE
    assert e.value.msg == "The z_line matrix of line type 'test' has coefficients with negative real part."

    # Bad shape (LV - Z)
    z_line = np.eye(4, dtype=complex)[:, :2]
    y_shunt = np.eye(4, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert e.value.msg == "The z_line matrix of line type 'test' has incorrect dimensions (4, 2)."

    # Bad shape (LV - Y)
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(3, dtype=complex)
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line1", bus1, bus2, phases="abcn", ground=ground, parameters=lp, length=2.4)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE
    assert e.value.msg == "Incorrect y_shunt dimensions for line 'line1': (3, 3) instead of (4, 4)"

    # Bad shape (MV - Z)
    z_line = np.eye(4, dtype=complex)[:, :2]
    y_shunt = np.eye(3, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert e.value.msg == "The z_line matrix of line type 'test' has incorrect dimensions (4, 2)."

    # Bad shape (MV - Y)
    z_line = np.eye(3, dtype=complex)
    y_shunt = np.eye(6, dtype=complex)
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line2", bus1, bus2, phases="abc", ground=ground, parameters=lp, length=2.4)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE
    assert e.value.msg == "Incorrect y_shunt dimensions for line 'line2': (6, 6) instead of (3, 3)"

    # LV line with not zero shunt admittance
    z_line = np.eye(3, dtype=complex)
    y_shunt = np.eye(3, dtype=complex)
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    with pytest.raises(RoseauLoadFlowException) as e:
        Line("line3", bus1, bus2, phases="abcn", ground=ground, parameters=lp, length=2.4)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert e.value.msg == "Incorrect z_line dimensions for line 'line3': (3, 3) instead of (4, 4)"

    # Adding/Removing a shunt to a line is not allowed
    mat = np.eye(3, dtype=complex)
    lp1 = LineParameters("lp1", z_line=mat.copy(), y_shunt=mat.copy())
    lp2 = LineParameters("lp2", z_line=mat.copy())
    bus1 = Bus("bus1", phases="abc")
    bus2 = Bus("bus2", phases="abc")
    ground = Ground("ground")
    line1 = Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp1, length=1.0, ground=ground)
    line2 = Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp2, length=1.0, ground=None)
    with pytest.raises(RoseauLoadFlowException) as e:
        line1.parameters = lp2
    assert e.value.msg == "Cannot set line parameters without a shunt to a line that has shunt components."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_MODEL
    with pytest.raises(RoseauLoadFlowException) as e:
        line2.parameters = lp1
    assert e.value.msg == "Cannot set line parameters with a shunt to a line that does not have shunt components."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_MODEL


def test_geometry():
    # line_data = {"dpp": 0, "dpn": 0, "dsh": 0.04}

    # Working example
    z_line, y_shunt, line_type, conductor_type, insulator_type, section = LineParameters._from_geometry(
        "test",
        line_type=LineType.OVERHEAD,
        conductor_type=ConductorType.AL,
        insulator_type=InsulatorType.PEX,
        section=150,
        section_neutral=70,
        height=10,
        external_diameter=0.04,
    )

    # TODO regenerate all expected values with the IEC constants and update this test
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

    npt.assert_allclose(z_line, nplin.inv(y_line_expected), rtol=0.04, atol=0.02)
    y_shunt_expected = np.array(
        [
            [
                9.89734304e-08 + 4.88922793e-05j,
                -0.00000000e00 - 1.92918966e-06j,
                -0.00000000e00 - 1.92821912e-06j,
                -0.00000000e00 - 1.20437270e-05j,
            ],
            [
                -0.00000000e00 - 1.92918966e-06j,
                9.89734304e-08 + 4.88922793e-05j,
                -0.00000000e00 - 1.92821912e-06j,
                -0.00000000e00 - 1.20437270e-05j,
            ],
            [
                -0.00000000e00 - 1.92821912e-06j,
                -0.00000000e00 - 1.92821912e-06j,
                9.89791759e-08 + 4.88941669e-05j,
                -0.00000000e00 - 1.20446700e-05j,
            ],
            [
                -0.00000000e00 - 1.20437270e-05j,
                -0.00000000e00 - 1.20437270e-05j,
                -0.00000000e00 - 1.20446700e-05j,
                2.13327419e-07 + 1.07241264e-04j,
            ],
        ]
    )
    npt.assert_allclose(y_shunt, y_shunt_expected, rtol=0.001)

    assert line_type == LineType.OVERHEAD
    assert conductor_type == ConductorType.AL
    assert insulator_type == InsulatorType.PEX
    assert section == 150

    # line_data = {"dpp": 0, "dpn": 0, "dsh": 0.04}

    # Working example
    z_line, y_shunt, line_type, conductor_type, insulator_type, section = LineParameters._from_geometry(
        "test",
        line_type=LineType.UNDERGROUND,
        conductor_type=ConductorType.AL,
        insulator_type=InsulatorType.PVC,
        section=150,
        section_neutral=70,
        height=-1.5,
        external_diameter=0.049,
    )
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
    npt.assert_allclose(z_line, nplin.inv(y_line_expected), rtol=0.04, atol=0.02)
    y_shunt_expected = np.array(
        [
            [
                1.90891221e-05 + 4.58910922e-04j,
                -0.00000000e00 - 7.48205724e-05j,
                -0.00000000e00 - 2.10155861e-05j,
                -0.00000000e00 - 4.49227283e-05j,
            ],
            [
                -0.00000000e00 - 7.48205724e-05j,
                2.06391240e-05 + 4.99733590e-04j,
                -0.00000000e00 - 7.48205724e-05j,
                -0.00000000e00 - 6.10704585e-06j,
            ],
            [
                -0.00000000e00 - 2.10155861e-05j,
                -0.00000000e00 - 7.48205724e-05j,
                1.90891221e-05 + 4.58910922e-04j,
                -0.00000000e00 - 4.49227283e-05j,
            ],
            [
                -0.00000000e00 - 4.49227283e-05j,
                -0.00000000e00 - 6.10704585e-06j,
                -0.00000000e00 - 4.49227283e-05j,
                1.26846966e-05 + 3.07364112e-04j,
            ],
        ]
    )

    npt.assert_allclose(y_shunt, y_shunt_expected, rtol=0.3)

    assert line_type == LineType.UNDERGROUND
    assert conductor_type == ConductorType.AL
    assert insulator_type == InsulatorType.PVC
    assert section == 150


def test_sym():
    # With the bad model of PwF
    # line_data = {"id": "NKBA NOR  25.00 kV", "un": 25000.0, "in": 277.0000100135803}

    z_line, y_shunt = LineParameters._sym_to_zy(
        "NKBA NOR  25.00 kV", z0=0.0j, z1=1.0 + 1.0j, zn=0.0j, xpn=0.0, y0=0.0j, y1=1e-06j, bn=0.0, bpn=0.0
    )
    z_line_expected = (1 + 1j) * np.eye(3)
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = 1e-6j * np.eye(3)
    npt.assert_allclose(y_shunt, y_shunt_expected)

    # line_data = {"id": "NKBA 4x150   1.00 kV", "un": 1000.0, "in": 361.0000014305115}
    # Downgraded model because of PwF bad data
    z_line, y_shunt = LineParameters._sym_to_zy(
        "NKBA 4x150   1.00 kV",
        z0=0.5 + 0.3050000071525574j,
        z1=0.125 + 0.0860000029206276j,
        zn=0.0j,
        xpn=0.0,
        y0=0.0j,
        y1=0.0j,
        bn=0.0,
        bpn=0.0,
    )
    z_line_expected = np.array(
        [
            [0.25 + 0.159j, 0.125 + 0.073j, 0.125 + 0.073j],
            [0.125 + 0.073j, 0.25 + 0.159j, 0.125 + 0.073j],
            [0.125 + 0.073j, 0.125 + 0.073j, 0.25 + 0.159j],
        ],
        dtype=complex,
    )
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = np.zeros(shape=(3, 3), dtype=complex)
    npt.assert_allclose(y_shunt, y_shunt_expected)

    # First line
    # line_data = {"id": "sym_neutral_underground_line_example", "un": 400.0, "in": 150}

    z_line, y_shunt = LineParameters._sym_to_zy(
        "sym_neutral_underground_line_example",
        z0=0.188 + 0.8224j,
        z1=0.188 + 0.0812j,
        zn=0.4029 + 0.3522j,
        xpn=0.2471,
        y0=0.000010462 + 0.000063134j,
        y1=0.000010462 + 0.00022999j,
        bn=0.00011407,
        bpn=-0.000031502,
    )
    z_line_expected = np.array(
        [
            [0.188 + 0.32826667j, 0.0 + 0.24706667j, 0.0 + 0.24706667j, 0.0 + 0.2471j],
            [0.0 + 0.24706667j, 0.188 + 0.32826667j, 0.0 + 0.24706667j, 0.0 + 0.2471j],
            [0.0 + 0.24706667j, 0.0 + 0.24706667j, 0.188 + 0.32826667j, 0.0 + 0.2471j],
            [0.0 + 0.2471j, 0.0 + 0.2471j, 0.0 + 0.2471j, 0.4029 + 0.3522j],
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

    # Second line
    # line_data = {"id": "sym_line_example", "un": 20000.0, "in": 309}

    z_line, y_shunt = LineParameters._sym_to_zy(
        "sym_line_example", z0=0.2 + 0.1j, z1=0.2 + 0.1j, zn=0.4029, y0=0.00014106j, y1=0.00014106j
    )
    z_line_expected = (0.2 + 0.1j) * np.eye(3)
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = 0.00014106j * np.eye(3)
    npt.assert_allclose(y_shunt, y_shunt_expected)


def test_from_name_lv():
    with pytest.raises(RoseauLoadFlowException) as e, pytest.warns(FutureWarning):
        LineParameters.from_name_lv("totoU_Al_150")
    assert "The line type name does not follow the syntax rule." in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX

    with pytest.warns(FutureWarning):
        lp = LineParameters.from_name_lv("U_AL_150")
    assert lp.z_line.shape == (4, 4)
    assert lp.y_shunt.shape == (4, 4)
    assert (lp.z_line.real >= 0).all().all()


def test_from_name_mv():
    with pytest.raises(RoseauLoadFlowException) as e:  # , pytest.warns(FutureWarning):
        LineParameters.from_name_mv("totoU_Al_150")
    assert "The line type name does not follow the syntax rule." in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX

    lp = LineParameters.from_name_mv("U_AL_150")
    z_line_expected = (0.1767 + 0.1j) * np.eye(3)
    y_shunt_expected = 0.00014106j * np.eye(3)

    npt.assert_allclose(lp.z_line.m_as("ohm/km"), z_line_expected, rtol=0.01, atol=0.01)
    npt.assert_allclose(lp.y_shunt.m_as("S/km"), y_shunt_expected, rtol=0.01, atol=0.01)


def test_catalogue_data():
    # The catalogue data path exists
    catalogue_path = LineParameters.catalogue_path()
    assert catalogue_path.exists()

    catalogue_data = LineParameters.catalogue_data()

    # Check that the name is unique
    assert catalogue_data["name"].is_unique, "Regenerate catalogue."

    for row in catalogue_data.itertuples():
        assert re.match(r"^(?:U|O|T)_[A-Z]+_\d+(?:_\w+)?$", row.name)
        assert isinstance(row.r, float)
        assert isinstance(row.x, float)
        assert isinstance(row.b, float)
        assert isinstance(row.maximal_current, int | float)
        LineType(row.type)  # Check that the type is valid
        ConductorType(row.material)  # Check that the material is valid
        InsulatorType(row.insulator)  # Check that the insulator is valid
        assert isinstance(row.section, int | float)


def test_from_catalogue():
    # Unknown strings
    for field_name in ("name",):
        # String
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_catalogue(**{field_name: "unknown"})
        assert e.value.msg.startswith(f"No {field_name} matching 'unknown' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

        # Regexp
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_catalogue(**{field_name: r"unknown[a-z]+"})
        assert e.value.msg.startswith(f"No {field_name} matching 'unknown[a-z]+' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Unknown enums
    for field_name in ("line_type", "conductor_type", "insulator_type"):
        # String
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_catalogue(**{field_name: "invalid"})
        assert e.value.msg.startswith(f"No {field_name} matching 'invalid' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

        # Regexp
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_catalogue(**{field_name: r"invalid[a-z]+"})
        assert e.value.msg.startswith(f"No {field_name} matching 'invalid[a-z]+' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Unknown floats
    for field_name, display_name, display_unit in (("section", "cross-section", "mm²"),):
        # Without unit
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_catalogue(**{field_name: 3.1415})
        assert e.value.msg.startswith(f"No {display_name} matching 3.1 {display_unit} has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

        # With unit
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_catalogue(**{field_name: Q_(0.031415, "cm²")})
        assert e.value.msg.startswith(f"No {display_name} matching 3.1 {display_unit} has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Several line parameters
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters.from_catalogue(name=r"U_AL_.*")
    assert e.value.msg == (
        "Several line parameters matching the query (name='U_AL_.*') have been found: "
        "'U_AL_19', 'U_AL_20', 'U_AL_22', 'U_AL_25', 'U_AL_28', 'U_AL_29', 'U_AL_33', "
        "'U_AL_34', 'U_AL_37', 'U_AL_38', 'U_AL_40', 'U_AL_43', 'U_AL_48', 'U_AL_50', "
        "'U_AL_54', 'U_AL_55', 'U_AL_59', 'U_AL_60', 'U_AL_69', 'U_AL_70', 'U_AL_74', "
        "'U_AL_75', 'U_AL_79', 'U_AL_80', 'U_AL_90', 'U_AL_93', 'U_AL_95', 'U_AL_100', "
        "'U_AL_116', 'U_AL_117', 'U_AL_120', 'U_AL_147', 'U_AL_148', 'U_AL_150', 'U_AL_228', "
        "'U_AL_240', 'U_AL_288'."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND

    # Success
    lp = LineParameters.from_catalogue(name="U_AL_150")
    assert lp.id == "U_AL_150"
    assert lp.z_line.shape == (3, 3)
    assert lp.y_shunt.shape == (3, 3)
    assert lp.max_current > 0
    assert lp.line_type == LineType.UNDERGROUND
    assert lp.conductor_type == ConductorType.AL
    assert lp.insulator_type == InsulatorType.UNKNOWN
    assert lp.section.m == 150

    # Success, overridden ID
    lp = LineParameters.from_catalogue(name="U_AL_150", id="lp1")
    assert lp.id == "lp1"

    # Success, single-phase line
    lp = LineParameters.from_catalogue(name="U_AL_150", nb_phases=2)
    assert lp.z_line.shape == (2, 2)
    assert lp.y_shunt.shape == (2, 2)


def test_get_catalogue():
    # Get the entire catalogue
    catalogue = LineParameters.get_catalogue()
    assert isinstance(catalogue, pd.DataFrame)
    assert catalogue.shape == (355, 8)

    # Filter on a single attribute
    for field_name, value, expected_size in (
        ("name", r"U_AL_150.*", 1),
        ("line_type", "OvErHeAd", 122),
        ("conductor_type", "Cu", 121),
        # ("insulator_type", InsulatorType.SE, 240),
        ("section", 150, 9),
        ("section", Q_(1.5, "cm²"), 9),
    ):
        filtered_catalogue = LineParameters.get_catalogue(**{field_name: value})
        assert filtered_catalogue.shape == (expected_size, 8)

    # Filter on two attributes
    for field_name, value, expected_size in (
        ("name", r"U_AL_150.*", 1),
        ("line_type", "OvErHeAd", 122),
        ("section", 150, 9),
    ):
        filtered_catalogue = LineParameters.get_catalogue(**{field_name: value})
        assert filtered_catalogue.shape == (expected_size, 8)

    # No results
    empty_catalogue = LineParameters.get_catalogue(section=15000)
    assert empty_catalogue.shape == (0, 8)


def test_max_current():
    lp = LineParameters("test", z_line=np.eye(3))
    assert lp.max_current is None

    lp = LineParameters("test", z_line=np.eye(3), max_current=100)
    assert lp.max_current == Q_(100, "A")

    lp.max_current = 200
    assert lp.max_current == Q_(200, "A")

    lp.max_current = None
    assert lp.max_current is None

    lp.max_current = Q_(3, "kA")
    assert lp.max_current == Q_(3_000, "A")


def test_json_serialization():
    lp = LineParameters("test", z_line=np.eye(3), max_current=np.int64(100), section=np.float64(150))
    lp_dict = lp.to_dict()
    assert isinstance(lp_dict["z_line"], list)
    assert isinstance(lp_dict["max_current"], int)
    assert isinstance(lp_dict["section"], float)
    json.dumps(lp_dict)


def test_from_open_dss():
    # DSS command: `New linecode.240sq nphases=3 R1=0.127 X1=0.072 R0=0.342 X0=0.089 units=km`
    lp240sq = LineParameters.from_open_dss(
        id="linecode-240sq",
        nphases=3,
        r1=Q_(0.127, "ohm/km"),
        x1=Q_(0.072, "ohm/km"),
        r0=Q_(0.342, "ohm/km"),
        x0=Q_(0.089, "ohm/km"),
        c1=Q_(3.4, "nF/km"),
        c0=Q_(1.6, "nF/km"),
    )
    assert lp240sq.id == "linecode-240sq"
    zs_e = 0.19866666666666669 + 0.07766666666666666j
    zm_e = 0.07166666666666667 + 0.005666666666666667j
    z_line_expected = [[zs_e, zm_e, zm_e], [zm_e, zs_e, zm_e], [zm_e, zm_e, zs_e]]
    np.testing.assert_allclose(lp240sq.z_line.m, z_line_expected)
    ys_e = 8.796459430051418e-07j
    ym_e = -1.8849555921538752e-07j
    y_shunt_expected = [[ys_e, ym_e, ym_e], [ym_e, ys_e, ym_e], [ym_e, ym_e, ys_e]]
    np.testing.assert_allclose(lp240sq.y_shunt.m, y_shunt_expected)
    assert lp240sq.line_type is None
    assert lp240sq.max_current is None

    # DSS command: `New LineCode.16sq NPhases=1 R1=0.350, X1=0.025, R0=0.366, X0=0.025, C1=1.036, C0=0.488 Units=kft NormAmps=400 LineType=OH`
    lp16sq = LineParameters.from_open_dss(
        id="linecode-16sq",
        nphases=1,
        r1=Q_(0.350, "ohm/kft"),
        x1=Q_(0.025, "ohm/kft"),
        r0=Q_(0.366, "ohm/kft"),
        x0=Q_(0.025, "ohm/kft"),
        c1=Q_(1.036, "nF/kft"),
        c0=Q_(0.488, "nF/kft"),
        linetype="OH",
        normamps=Q_(400, "A"),
    )
    assert lp16sq.id == "linecode-16sq"
    zs_e = 1.1657917760279966 + 0.08202099737532809j
    z_line_expected = [[zs_e]]
    np.testing.assert_allclose(lp16sq.z_line.m, z_line_expected)
    ys_e = 8.795360010050165e-07j
    y_shunt_expected = [[ys_e]]
    np.testing.assert_allclose(lp16sq.y_shunt.m, y_shunt_expected)
    assert lp16sq.line_type == LineType.OVERHEAD
    assert lp16sq.max_current.m == 400
