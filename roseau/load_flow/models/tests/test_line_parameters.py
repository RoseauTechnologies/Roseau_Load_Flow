import re

import numpy as np
import numpy.linalg as nplin
import numpy.testing as npt
import pandas as pd
import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineParameters
from roseau.load_flow.units import Q_
from roseau.load_flow.utils import Insulator, LineType, Material


def test_line_parameters():
    # Real element off the diagonal (Z)
    y_shunt = np.eye(4, dtype=complex)
    for p in Line.allowed_phases:
        if len(p) == 1:
            continue
        z_line = np.eye(4, dtype=complex)
        indices = ["abcn".index(x) for x in p]
        z_line[indices[0], indices[1]] = 1
        lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
        with pytest.warns(UserWarning, match=r"z_line .* has off-diagonal elements with a non-zero"):
            lp.z_line(p)

    # Real element off the diagonal (Y)
    z_line = np.eye(4, dtype=complex)

    for p in Line.allowed_phases:
        if len(p) == 1:
            continue
        y_shunt = np.eye(4, dtype=complex)
        indices = ["abcn".index(x) for x in p]
        y_shunt[indices[0], indices[1]] = 1
        lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
        with pytest.warns(UserWarning, match=r"y_shunt .* has off-diagonal elements with a non-zero"):
            lp.y_shunt(p)

    # Negative real values (Z)
    y_shunt = -2 * np.eye(4, dtype=complex)
    for p in Line.allowed_phases:
        z_line = 2 * np.eye(4, dtype=complex)
        indices = ["abcn".index(x) for x in p]
        z_line[indices[0], indices[0]] = -3
        lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
        with pytest.raises(RoseauLoadFlowException) as e:
            lp.z_line(p)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE
        assert e.value.msg == "The z_line matrix of line type 'test' has coefficients with negative real part."

    # Negative real values (Y)
    z_line = 2 * np.eye(4, dtype=complex)

    for p in Line.allowed_phases:
        y_shunt = 2 * np.eye(4, dtype=complex)
        indices = ["abcn".index(x) for x in p]
        y_shunt[indices[0], indices[0]] = -3
        lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt)
        with pytest.raises(RoseauLoadFlowException) as e:
            lp.y_shunt(p)
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_VALUE
        assert e.value.msg == "The y_shunt matrix of line type 'test' has coefficients with negative real part."

    # Bad shape (LV - Z)
    z_line = np.eye(4, dtype=complex)[:, :2]
    y_shunt = np.eye(4, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters(id="test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert (
        e.value.msg
        == "The z_line matrix of line type 'test' has incorrect dimensions (4, 2). A 4x4 matrix was expected."
    )

    # Bad shape (LV - Y)
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(3, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters(id="test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE
    assert (
        e.value.msg
        == "The y_shunt matrix of line type 'test' has incorrect dimensions (3, 3). A 4x4 matrix was expected."
    )

    # Bad shape (MV - Z)
    z_line = np.eye(4, dtype=complex)[:, :2]
    y_shunt = np.eye(3, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert (
        e.value.msg
        == "The z_line matrix of line type 'test' has incorrect dimensions (4, 2). A 4x4 matrix was expected."
    )

    # Bad shape (MV - Y)
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(6, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters(id="test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_SHAPE
    assert (
        e.value.msg
        == "The y_shunt matrix of line type 'test' has incorrect dimensions (6, 6). A 4x4 matrix was expected."
    )

    # LV line with not zero shunt admittance
    z_line = np.eye(3, dtype=complex)
    y_shunt = np.eye(3, dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_SHAPE
    assert (
        e.value.msg
        == "The z_line matrix of line type 'test' has incorrect dimensions (3, 3). A 4x4 matrix was expected."
    )

    # Adding/Removing a shunt to a line is not allowed
    mat = np.eye(4, dtype=complex)
    lp1 = LineParameters(id="lp1", z_line=mat.copy(), y_shunt=mat.copy())
    lp2 = LineParameters(id="lp2", z_line=mat.copy())
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abc")
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


def test_from_geometry():
    # line_data = {"dpp": 0, "dpn": 0, "dsh": 0.04}

    # Working example
    z_line, y_shunt, line_type, materials, insulators, sections = LineParameters._from_geometry(
        "test",
        line_type=LineType.OVERHEAD,
        material=Material.AL,
        material_neutral=None,
        insulator=Insulator.PEX,
        insulator_neutral=None,
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
    assert np.array_equal(materials, np.array([Material.AL] * 4, dtype=np.object_))
    assert np.array_equal(insulators, np.array([Insulator.PEX] * 4, dtype=np.object_))
    npt.assert_allclose(sections, [150, 150, 150, 70])

    # Test None insulator
    lp = LineParameters.from_geometry(
        id="test",
        line_type=LineType.OVERHEAD,
        material="CU",
        insulator=None,
        section=50,
        height=10,
        external_diameter=0.04,
    )
    # The default insulator for overhead lines
    assert np.array_equal(lp._insulators, np.array([Insulator.NONE] * 4, dtype=np.object_))
    np.testing.assert_allclose(lp._y_shunt.real, 0.0)
    lp = LineParameters.from_geometry(
        id="test",
        line_type=LineType.OVERHEAD,
        material="CU",
        insulator=Insulator.NONE,
        insulator_neutral=None,
        section=50,
        height=10,
        external_diameter=0.04,
    )
    assert np.array_equal(lp._insulators, np.array([Insulator.NONE] * 4, dtype=np.object_))
    np.testing.assert_allclose(lp._y_shunt.real, 0.0)

    lp = LineParameters.from_geometry(
        id="test",
        line_type="underground",
        material=Material.CU,
        insulator=Insulator.NONE,
        section=50,
        height=-0.5,
        external_diameter=0.04,
    )
    np.testing.assert_allclose(
        lp._y_shunt.imag * 4,  # because InsulatorType.IP has 4x epsilon_r
        LineParameters.from_geometry(
            id="test",
            line_type=lp.line_type,
            material=lp._materials[0],
            insulator=Insulator.IP,  # 4x epsilon_r of InsulatorType.NONE
            section=lp._sections[0],
            height=-0.5,
            external_diameter=0.04,
        )._y_shunt.imag,
    )

    # The same but precise the neutral types
    z_line, y_shunt, line_type, materials, insulators, sections = LineParameters._from_geometry(
        "test",
        line_type=LineType.OVERHEAD,
        material=Material.AL,
        material_neutral=Material.AL,
        insulator=Insulator.PEX,
        insulator_neutral=Insulator.PEX,
        section=150,
        section_neutral=70,
        height=10,
        external_diameter=0.04,
    )
    npt.assert_allclose(z_line, nplin.inv(y_line_expected), rtol=0.04, atol=0.02)
    npt.assert_allclose(y_shunt, y_shunt_expected, rtol=0.001)
    assert line_type == LineType.OVERHEAD
    assert np.array_equal(materials, np.array([Material.AL] * 4, dtype=np.object_))
    assert np.array_equal(insulators, np.array([Insulator.PEX] * 4, dtype=np.object_))
    npt.assert_allclose(sections, [150, 150, 150, 70])
    # line_data = {"dpp": 0, "dpn": 0, "dsh": 0.04}

    # Working example (also with string types)
    z_line, y_shunt, line_type, materials, insulators, sections = LineParameters._from_geometry(
        id="test",
        line_type="UNDERGROUND",
        material="AL",
        material_neutral="AL",
        insulator="PVC",
        insulator_neutral="PVC",
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

    assert isinstance(line_type, LineType)
    assert line_type == LineType.UNDERGROUND
    assert np.array_equal(materials, np.array([Material.AL] * 4, dtype=np.object_))
    assert np.array_equal(insulators, np.array([Insulator.PVC] * 4, dtype=np.object_))
    npt.assert_allclose(sections, [150, 150, 150, 70])

    # Mix two lines to check that the neutral is different
    z_line_1, y_shunt_1, line_type, materials, insulators, sections = LineParameters._from_geometry(
        "test",
        line_type=LineType.OVERHEAD,
        material=Material.AL,
        material_neutral=Material.AL,
        insulator=Insulator.PEX,
        insulator_neutral=Insulator.PEX,
        section=150,
        section_neutral=70,
        height=10,
        external_diameter=0.04,
    )
    z_line_2, y_shunt_2, line_type, materials, insulators, sections = LineParameters._from_geometry(
        "test",
        line_type=LineType.OVERHEAD,
        material=Material.AM,
        material_neutral=Material.AM,
        insulator=Insulator.XLPE,
        insulator_neutral=Insulator.XLPE,
        section=150,
        section_neutral=70,
        height=10,
        external_diameter=0.04,
    )

    z_line, y_shunt, line_type, materials, insulators, sections = LineParameters._from_geometry(
        "test",
        line_type=LineType.OVERHEAD,
        material=Material.AL,
        material_neutral=Material.AM,
        insulator=Insulator.PEX,
        insulator_neutral=Insulator.XLPE,
        section=150,
        section_neutral=70,
        height=10,
        external_diameter=0.04,
    )
    z_line_expected = z_line_1.copy()
    z_line_expected[3, 3] = z_line_2[3, 3]
    y_shunt_expected = y_shunt_1.copy()
    y_shunt_expected[3, 3] = y_shunt_2[3, 3]

    npt.assert_allclose(z_line, z_line_expected)
    npt.assert_allclose(y_shunt, y_shunt_expected)


def test_sym():
    # With the bad model of PwF
    # line_data = {"id": "NKBA NOR  25.00 kV", "un": 25000.0, "in": 277.0000100135803}

    z0 = 0.0j
    z1 = 1.0 + 1.0j
    y0 = 0.0j
    y1 = 1e-06j
    z_line, y_shunt = LineParameters._sym_to_zy(z0=z0, z1=z1, zn=0.0j, zpn=0.0j, y0=y0, y1=y1, bn=0.0, bpn=0.0)
    zs = (z0 + 2 * z1) / 3
    zm = (z0 - z1) / 3
    ys = (y0 + 2 * y1) / 3
    ym = (y0 - y1) / 3
    z_line_expected = [[zs, zm, zm, 0], [zm, zs, zm, 0], [zm, zm, zs, 0], [0, 0, 0, zs]]
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = [[ys, ym, ym, 0], [ym, ys, ym, 0], [ym, ym, ys, 0], [0, 0, 0, ys]]
    npt.assert_allclose(y_shunt, y_shunt_expected)

    # line_data = {"id": "NKBA 4x150   1.00 kV", "un": 1000.0, "in": 361.0000014305115}
    # Downgraded model because of PwF bad data
    z_line, y_shunt = LineParameters._sym_to_zy(
        z0=0.5 + 0.3050000071525574j,
        z1=0.125 + 0.0860000029206276j,
        zn=0.0j,
        zpn=0.0j,
        y0=0.0j,
        y1=0.0j,
        bn=0.0,
        bpn=0.0,
    )
    z_line_expected = np.array(
        [
            [0.25 + 0.159j, 0.125 + 0.073j, 0.125 + 0.073j, 0.0],
            [0.125 + 0.073j, 0.25 + 0.159j, 0.125 + 0.073j, 0.0],
            [0.125 + 0.073j, 0.125 + 0.073j, 0.25 + 0.159j, 0.0],
            [0.0, 0.0, 0.0, 0.25 + 0.159j],
        ],
        dtype=complex,
    )
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = np.zeros(shape=(4, 4), dtype=complex)
    npt.assert_allclose(y_shunt, y_shunt_expected)

    # First line
    # line_data = {"id": "sym_neutral_underground_line_example", "un": 400.0, "in": 150}
    z_line, y_shunt = LineParameters._sym_to_zy(
        z0=0.188 + 0.8224j,
        z1=0.188 + 0.0812j,
        zn=0.4029 + 0.3522j,
        zpn=0.2471j,
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

    z_line, y_shunt = LineParameters._sym_to_zy(z0=0.2 + 0.1j, z1=0.2 + 0.1j, zn=0.4029, y0=0.00014106j, y1=0.00014106j)
    z_line_expected = (0.2 + 0.1j) * np.eye(4)
    npt.assert_allclose(z_line, z_line_expected)
    y_shunt_expected = 0.00014106j * np.eye(4)
    npt.assert_allclose(y_shunt, y_shunt_expected)


def test_from_coiffier_model():
    # Invalid names
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters.from_coiffier_model("totoU_Al_150")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX
    assert e.value.msg == (
        "The Coiffier line parameter name 'totoU_Al_150' is not valid, expected format is "
        "'LineType_Material_CrossSection'."
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters.from_coiffier_model("U_AL_IP_150")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX
    assert e.value.msg == (
        "The Coiffier line parameter name 'U_AL_IP_150' is not valid, expected format is "
        "'LineType_Material_CrossSection'."
    )

    # Working example with defaults
    lp = LineParameters.from_coiffier_model("U_AL_150")
    z_line_expected = (0.1767 + 0.1j) * np.eye(4)
    y_shunt_expected = 0.00014106j * np.eye(4)
    assert lp.id == "U_AL_150"
    assert lp.line_type == LineType.UNDERGROUND
    assert np.array_equal(lp._materials, np.array([Material.AL] * 4, dtype=np.object_))
    assert np.allclose(lp._sections, 150)
    npt.assert_allclose(lp._z_line, z_line_expected, rtol=0.01, atol=0.01, strict=True)
    npt.assert_allclose(lp._y_shunt, y_shunt_expected, rtol=0.01, atol=0.01, strict=True)
    npt.assert_allclose(lp._ampacities, [368.689292] * 4, strict=True)

    # Working example with custom arguments
    lp2 = LineParameters.from_coiffier_model("O_CU_54", id="lp2")
    assert lp2.id == "lp2"
    assert lp2.line_type == LineType.OVERHEAD
    assert np.array_equal(lp2._materials, np.array([Material.CU] * 4, dtype=np.object_))
    assert np.allclose(lp2._sections, 54)
    assert lp2._z_line.shape == (4, 4)
    assert lp2._y_shunt.shape == (4, 4)


def test_catalogue_data():
    # The catalogue data path exists
    catalogue_path = LineParameters.catalogue_path()
    assert catalogue_path.exists()

    catalogue_data = LineParameters.catalogue_data()

    # Check that the name is unique
    assert catalogue_data["name"].is_unique, "Regenerate catalogue."

    for row in catalogue_data.itertuples():
        assert re.match(r"^[UOT]_[A-Z]+_\d+(?:_\w+)?$", row.name)
        assert isinstance(row.resistance, float)
        assert isinstance(row.resistance_neutral, float)
        assert isinstance(row.reactance, float)
        assert isinstance(row.reactance_neutral, float)
        assert isinstance(row.susceptance, float)
        assert isinstance(row.susceptance_neutral, float)
        assert isinstance(row.ampacity, int | float)
        assert isinstance(row.ampacity_neutral, int | float)
        LineType(row.type)  # Check that the type is valid
        Material(row.material)  # Check that the material is valid
        Material(row.material_neutral)  # Check that the material is valid
        pd.isna(row.insulator) or Insulator(row.insulator)  # Check that the insulator is valid
        pd.isna(row.insulator_neutral) or Insulator(row.insulator_neutral)  # Check that the insulator is valid
        assert isinstance(row.section, int | float)
        assert isinstance(row.section_neutral, int | float)


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
    for field_name in ("line_type", "material", "insulator"):
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
    assert lp._z_line.shape == (4, 4)
    assert lp._y_shunt.shape == (4, 4)
    assert (lp._ampacities > 0).all()
    assert lp.line_type == LineType.UNDERGROUND
    assert np.array_equal(lp._materials, np.array([Material.AL] * 4))
    assert lp._insulators is None
    assert np.allclose(lp._sections, 150)

    # Success, overridden ID
    lp = LineParameters.from_catalogue(name="U_AL_150", id="lp1")
    assert lp.id == "lp1"


def test_get_catalogue():
    # Get the entire catalogue
    catalogue = LineParameters.get_catalogue()
    assert isinstance(catalogue, pd.DataFrame)
    assert catalogue.shape == (355, 15)

    # Filter on a single attribute
    for field_name, value, expected_size in (
        ("name", r"U_AL_150.*", 1),
        ("line_type", "OvErHeAd", 122),
        ("material", "Cu", 121),
        ("material_neutral", "Cu", 121),
        # ("insulator", Insulator.SE, 240),
        ("section", 150, 9),
        ("section_neutral", 150, 9),
        ("section", Q_(1.5, "cm²"), 9),
        ("section_neutral", Q_(1.5, "cm²"), 9),
    ):
        filtered_catalogue = LineParameters.get_catalogue(**{field_name: value})
        assert filtered_catalogue.shape == (expected_size, 15)

    # Filter on two attributes
    for field_name, value, expected_size in (
        ("name", r"U_AL_150.*", 1),
        ("line_type", "OvErHeAd", 122),
        ("section", 150, 9),
        ("section_neutral", 150, 9),
    ):
        filtered_catalogue = LineParameters.get_catalogue(**{field_name: value})
        assert filtered_catalogue.shape == (expected_size, 15)

    # No results
    empty_catalogue = LineParameters.get_catalogue(section=15000)
    assert empty_catalogue.shape == (0, 15)


def test_insulators():
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(4, dtype=complex)

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=None)
    assert lp._insulators is None
    for p in Line.allowed_phases:
        assert lp.insulators(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=np.nan)
    assert lp._insulators is None
    for p in Line.allowed_phases:
        assert lp.insulators(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=pd.NA)
    assert lp._insulators is None
    for p in Line.allowed_phases:
        assert lp.insulators(p) is None

    # Single values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=Insulator.EPR)
    assert len(lp._insulators) == 4
    for p in Line.allowed_phases:
        assert np.array_equal(lp.insulators(p), np.array([Insulator.EPR] * len(p)))

    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=Insulator.EPR.name)
    assert len(lp._insulators) == 4
    for p in Line.allowed_phases:
        assert np.array_equal(lp.insulators(p), np.array([Insulator.EPR] * len(p)))

    # Special case for Insulator.NONE
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=Insulator.NONE.name)
    assert len(lp._insulators) == 4
    for p in Line.allowed_phases:
        assert np.array_equal(lp.insulators(p), np.array([Insulator.NONE] * len(p)))

    # Arrays
    insulators = [Insulator.EPR, Insulator.XLPE, Insulator.LDPE, Insulator.IP]
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=insulators)
    for p in Line.allowed_phases:
        expected_value = np.array([insulators["abcn".index(x)] for x in p])
        assert np.array_equal(lp.insulators(p), expected_value)

    insulators = [Insulator.NONE, Insulator.NONE, Insulator.NONE, Insulator.NONE]
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=insulators)
    for p in Line.allowed_phases:
        assert np.array_equal(lp.insulators(p), np.array([Insulator.NONE] * len(p)))

    # Arrays with all none
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=[pd.NA, np.nan, None, None])
    assert lp._insulators is None
    for p in Line.allowed_phases:
        assert lp.insulators(p) is None

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=[pd.NA, np.nan, Insulator.LDPE, Insulator.IP])
    assert e.value.msg == "Insulators cannot contain null values: [<NA>, nan, ldpe, ip] was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_INSULATORS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters(
            "test", z_line=z_line, y_shunt=y_shunt, insulators=["invalid", Insulator.XLPE, "XLPE", Insulator.IP]
        )
    assert e.value.msg == "'invalid' cannot be converted into a Insulator."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_INSULATOR

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulators=[Insulator.XLPE, Insulator.HDPE])
    assert e.value.msg == "Incorrect number of insulators: 2 instead of 4."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_INSULATORS_SIZE


def test_materials():
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(4, dtype=complex)

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=None)
    assert lp._materials is None
    for p in Line.allowed_phases:
        assert lp.materials(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=np.nan)
    assert lp._materials is None
    for p in Line.allowed_phases:
        assert lp.materials(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=pd.NA)
    assert lp._materials is None
    for p in Line.allowed_phases:
        assert lp.materials(p) is None

    # Single values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=Material.AAAC)
    assert len(lp._materials) == 4
    for p in Line.allowed_phases:
        assert np.array_equal(lp.materials(p), np.array([Material.AAAC] * len(p)))

    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=Material.AAAC.name)
    assert len(lp._materials) == 4
    for p in Line.allowed_phases:
        assert np.array_equal(lp.materials(p), np.array([Material.AAAC] * len(p)))

    # Arrays
    materials = [Material.AAAC, Material.AL, Material.CU, Material.AACSR]
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=materials)
    assert len(lp._materials) == 4
    for p in Line.allowed_phases:
        expected_value = np.array([materials["abcn".index(x)] for x in p])
        assert np.array_equal(lp.materials(p), expected_value)

    # Arrays with all none
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=[np.nan, float("nan"), pd.NA, np.nan])
    assert lp._materials is None
    for p in Line.allowed_phases:
        assert lp.materials(p) is None

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters(
            "test", z_line=z_line, y_shunt=y_shunt, materials=[np.nan, float("nan"), Material.AM, Material.CU]
        )
    assert e.value.msg == "Materials cannot contain null values: [nan, nan, am, cu] was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MATERIALS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=["invalid", Material.AM, "AM", "am"])
    assert e.value.msg == "'invalid' cannot be converted into a Material."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MATERIAL

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, materials=[Material.AM, Material.AL])
    assert e.value.msg == "Incorrect number of materials: 2 instead of 4."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MATERIALS_SIZE


def test_sections():
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(4, dtype=complex)

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=None)
    assert lp._sections is None
    for p in Line.allowed_phases:
        assert lp.sections(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=np.nan)
    assert lp._sections is None
    for p in Line.allowed_phases:
        assert lp.sections(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=pd.NA)
    assert lp._sections is None
    for p in Line.allowed_phases:
        assert lp.sections(p) is None

    # Single values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=4)
    assert len(lp._sections) == 4
    for p in Line.allowed_phases:
        assert np.allclose(lp.sections(p).m, 4)

    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=Q_(4, "cm**2"))
    assert len(lp._sections) == 4
    for p in Line.allowed_phases:
        assert np.allclose(lp.sections(p).m, 400)

    # Arrays
    sections = [4, 5, 6, 7]
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=Q_(sections, "mm**2"))
    assert len(lp._sections) == 4
    for p in Line.allowed_phases:
        expected_value = np.array([sections["abcn".index(x)] for x in p])
        assert np.allclose(lp.sections(p).m, expected_value)

    # Arrays with all none
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=[np.nan, float("nan"), pd.NA, np.nan])
    assert lp._sections is None
    for p in Line.allowed_phases:
        assert lp.sections(p) is None

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=[np.nan, float("nan"), 3, 4])
    assert e.value.msg == "Sections cannot contain null values: [nan, nan, 3, 4] mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=-1)
    assert e.value.msg == "Sections must be positive: -1 mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=0)
    assert e.value.msg == "Sections must be positive: 0 mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=[3, -1, 3.0, 4.0])
    assert e.value.msg == "Sections must be positive: [3.0, -1.0, 3.0, 4.0] mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=[3, 0, 3.0, 4.0])
    assert e.value.msg == "Sections must be positive: [3.0, 0.0, 3.0, 4.0] mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, sections=[3, 3])
    assert e.value.msg == "Incorrect number of sections: 2 instead of 4."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_SIZE


def test_ampacities():
    z_line = np.eye(4, dtype=complex)
    y_shunt = np.eye(4, dtype=complex)

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=None)
    assert lp._ampacities is None
    for p in Line.allowed_phases:
        assert lp.ampacities(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=np.nan)
    assert lp._ampacities is None
    for p in Line.allowed_phases:
        assert lp.ampacities(p) is None
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=pd.NA)
    assert lp._ampacities is None
    for p in Line.allowed_phases:
        assert lp.ampacities(p) is None

    # Single values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=4)
    assert len(lp._ampacities) == 4
    for p in Line.allowed_phases:
        assert np.allclose(lp.ampacities(p).m, 4)

    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=Q_(4, "kA"))
    assert len(lp._ampacities) == 4
    for p in Line.allowed_phases:
        assert np.allclose(lp.ampacities(p).m, 4000)

    # Arrays
    ampacities = [4, 5, 6, 7]
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=Q_(ampacities, "A"))
    assert len(lp._ampacities) == 4
    for p in Line.allowed_phases:
        expected_value = np.array([ampacities["abcn".index(x)] for x in p])
        assert np.allclose(lp.ampacities(p).m, expected_value)

    # Arrays with all none
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=[np.nan, float("nan"), pd.NA, np.nan])
    assert lp._ampacities is None
    for p in Line.allowed_phases:
        assert lp.ampacities(p) is None

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=[1, 2])
    assert e.value.msg == "Incorrect number of ampacities: 2 instead of 4."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=-2)
    assert e.value.msg == "Ampacities must be positive: -2 A was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=0)
    assert e.value.msg == "Ampacities must be positive: 0 A was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=[1, 2, -2, 3])
    assert e.value.msg == "Ampacities must be positive: [1.0, 2.0, -2.0, 3.0] A was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacities=[1, 2, 0, 3])
    assert e.value.msg == "Ampacities must be positive: [1.0, 2.0, 0.0, 3.0] A was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE


def test_json_serialization(tmp_path):
    lp = LineParameters(id="test", z_line=np.eye(4), sections=np.float64(150), ampacities=[1, 2, 3, 4])
    path = tmp_path / "lp.json"
    lp.to_json(path)
    lp_dict = LineParameters.from_json(path).to_dict()
    assert isinstance(lp_dict["z_line"], list)
    npt.assert_allclose(lp_dict["sections"], [150, 150, 150, 150])
    npt.assert_allclose(lp_dict["ampacities"], [1, 2, 3, 4])


def test_from_open_dss():
    # DSS command: `New linecode.240sq nphases=3 R1=0.127 X1=0.072 R0=0.342 X0=0.089 units=km`
    lp240sq = LineParameters.from_open_dss(
        id="linecode-240sq",
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
    z_line_expected = [
        [zs_e, zm_e, zm_e, zm_e],
        [zm_e, zs_e, zm_e, zm_e],
        [zm_e, zm_e, zs_e, zm_e],
        [zm_e, zm_e, zm_e, zs_e],
    ]
    np.testing.assert_allclose(lp240sq._z_line, z_line_expected)
    ys_e = 8.796459430051418e-07j
    ym_e = -1.8849555921538752e-07j
    y_shunt_expected = [
        [ys_e, ym_e, ym_e, ym_e],
        [ym_e, ys_e, ym_e, ym_e],
        [ym_e, ym_e, ys_e, ym_e],
        [ym_e, ym_e, ym_e, ys_e],
    ]
    np.testing.assert_allclose(lp240sq._y_shunt, y_shunt_expected)
    assert lp240sq.line_type is None
    assert lp240sq._ampacities is None

    # DSS command: `New LineCode.16sq NPhases=1 R1=0.350, X1=0.025, R0=0.366, X0=0.025, C1=1.036, C0=0.488 Units=kft NormAmps=400 LineType=OH`
    lp16sq = LineParameters.from_open_dss(
        id="linecode-16sq",
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
    zm_e = 0.017497812773403343 + 0j
    z_line_expected = [
        [zs_e, zm_e, zm_e, zm_e],
        [zm_e, zs_e, zm_e, zm_e],
        [zm_e, zm_e, zs_e, zm_e],
        [zm_e, zm_e, zm_e, zs_e],
    ]
    np.testing.assert_allclose(lp16sq._z_line, z_line_expected)
    ys_e = 8.795360010050165e-07j
    ym_e = -1.8827567521513636e-07j
    y_shunt_expected = [
        [ys_e, ym_e, ym_e, ym_e],
        [ym_e, ys_e, ym_e, ym_e],
        [ym_e, ym_e, ys_e, ym_e],
        [ym_e, ym_e, ym_e, ys_e],
    ]
    np.testing.assert_allclose(lp16sq._y_shunt, y_shunt_expected)
    assert lp16sq.line_type == LineType.OVERHEAD
    assert np.allclose(lp16sq._ampacities, 400)


def test_from_power_factory():
    # Parameters from tests/data/dgs/special/MV_Load.json
    pwf_params = {
        "id": "NA2YSY 1x95rm 12/20kV it",
        "r1": 0.3225,  # Ohm/km
        "x1": 0.125663,  # Ohm/km
        "b1": 72.25663,  # µS/km
        "r0": 1.29,  # Ohm/km
        "x0": 0.502654,  # Ohm/km
        "b0": 75.05265,  # µS/km
        "rn": 0,  # Ohm/km
        "xn": 0,  # Ohm/km
        "bn": 0,  # µS/km
        "rpn": 0,  # Ohm/km
        "xpn": 0,  # Ohm/km
        "bpn": 0,  # µS/km
        "inom": 0.235,  # kA
        "cohl": 0,  # Cable (underground)
        "conductor": "Al",  # Aluminium
        "insulation": 0,  # PVC
        "section": 95,  # mm²
    }
    na2ysy1x95rm = LineParameters.from_power_factory(**pwf_params)

    assert na2ysy1x95rm.id == "NA2YSY 1x95rm 12/20kV it"

    zs_e = 0.645 + 0.2513266666666667j
    zm_e = 0.3225 + 0.1256636666666667j
    z_line_expected = [
        [zs_e, zm_e, zm_e, 0],
        [zm_e, zs_e, zm_e, 0],
        [zm_e, zm_e, zs_e, 0],
        [0, 0, 0, zs_e],
    ]
    np.testing.assert_allclose(na2ysy1x95rm._z_line, z_line_expected)
    ys_e = 7.318863666666666e-05j
    ym_e = 9.320066666666643e-07j
    y_shunt_expected = [
        [ys_e, ym_e, ym_e, 0],
        [ym_e, ys_e, ym_e, 0],
        [ym_e, ym_e, ys_e, 0],
        [0, 0, 0, ys_e],
    ]
    np.testing.assert_allclose(na2ysy1x95rm._y_shunt, y_shunt_expected)

    assert np.allclose(na2ysy1x95rm._ampacities, 235), na2ysy1x95rm._ampacities
    assert na2ysy1x95rm.line_type == LineType.UNDERGROUND
    assert np.array_equal(na2ysy1x95rm._materials, np.array([Material.AL] * 4))
    assert np.array_equal(na2ysy1x95rm._insulators, np.array([Insulator.PVC] * 4))
    assert np.allclose(na2ysy1x95rm._sections, 95)

    # Line has no neutral, OK to not pass neutral impedances
    new_pwf_params = {k: v for k, v in pwf_params.items() if k not in {"rn", "xn", "bn", "rpn", "xpn", "bpn"}}
    LineParameters.from_power_factory(**new_pwf_params)

    # This time with a missing neutral value
    for key in ("rn", "xn", "bn", "rpn", "xpn", "bpn"):
        new_pwf_params = {k: v for k, v in pwf_params.items() if k != key}
        with pytest.raises(RoseauLoadFlowException) as e:
            LineParameters.from_power_factory(**new_pwf_params)
        assert e.value.msg == (
            "rn, xn, bn, rpn, xpn and bpn must be all provided or none of them for line parameters "
            "'NA2YSY 1x95rm 12/20kV it'."
        )
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_MODEL

    # String versions of line/insulator type are also accepted
    new_pwf_params = pwf_params | {"cohl": "OHL", "insulation": "XLPE"}
    lp = LineParameters.from_power_factory(**new_pwf_params)
    assert lp.line_type == LineType.OVERHEAD
    assert np.array_equal(lp._insulators, np.array([Insulator.XLPE] * 4, dtype=np.object_))


def test_results_to_dict():
    # No results to export
    lp = LineParameters.from_catalogue(name="U_AL_150")
    with pytest.raises(RoseauLoadFlowException) as e:
        lp.results_to_dict()
    assert e.value.msg == "The LineParameters has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS


def test_equality():
    lp = LineParameters.from_catalogue(name="U_AL_150")
    data = {
        "id": lp.id,
        "z_line": lp._z_line,
        "y_shunt": lp._y_shunt,
        "ampacities": lp._ampacities,
        "line_type": lp._line_type,
        "materials": lp._materials,
        "insulators": lp._insulators,
        "sections": lp._sections,
    }
    lp2 = LineParameters(**data)
    assert lp2 == lp

    other_data = {
        "id": lp.id + " other",
        "z_line": lp._z_line + 1,
        "y_shunt": lp._y_shunt + 1,
        "ampacities": lp._ampacities + 1,
        "line_type": LineType.OVERHEAD,
        "materials": Material.CU,
        "insulators": Insulator.XLPE,
        "sections": lp._sections + 1,
    }
    for k, v in other_data.items():
        other_lp = LineParameters(**(data | {k: v}))
        assert other_lp != lp, k

    # Test the case which returns NotImplemented in the equality operator
    assert lp != object()
