import re

import numpy as np
import numpy.linalg as nplin
import numpy.testing as npt
import pandas as pd
import pytest

from roseau.load_flow import Q_, Insulator, LineType, Material, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single.models import Bus, Line, LineParameters


def test_line_parameters():
    bus1 = Bus(id="junction1")
    bus2 = Bus(id="junction2")

    # Negative real values (Z)
    z_line = -3
    y_shunt = -2
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE
    assert e.value.msg == "The z_line value of line type 'test' has coefficients with negative real part."

    # Negative real values (Y)
    y_shunt = -3
    with pytest.raises(RoseauLoadFlowException):
        LineParameters(id="test", z_line=z_line, y_shunt=y_shunt)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE
    assert e.value.msg == "The z_line value of line type 'test' has coefficients with negative real part."

    # Adding/Removing a shunt to a line is not allowed
    lp1 = LineParameters(id="lp1", z_line=1.0, y_shunt=1.0)
    lp2 = LineParameters(id="lp2", z_line=1.0)
    bus1 = Bus(id="bus1")
    bus2 = Bus(id="bus2")
    line1 = Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp1, length=1.0)
    line2 = Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp2, length=1.0)
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
    lp = LineParameters.from_geometry(
        id="test",
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

    assert np.isclose(lp.z_line.m, nplin.inv(y_line_expected)[0, 0], rtol=0.04, atol=0.02)
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
    npt.assert_allclose(lp.y_shunt.m, y_shunt_expected[0, 0], rtol=0.001)

    assert lp.line_type == LineType.OVERHEAD
    assert lp.material == Material.AL
    assert lp.insulator == Insulator.PEX
    assert np.isclose(lp.section.m, 150)

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
    assert lp.insulator == Insulator.NONE
    assert np.isclose(lp.y_shunt.m.real, 0.0)
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
    assert lp.insulator == Insulator.NONE
    assert np.isclose(lp.y_shunt.m.real, 0.0)

    lp = LineParameters.from_geometry(
        id="test",
        line_type="underground",
        material=Material.CU,
        insulator=Insulator.NONE,
        section=50,
        height=-0.5,
        external_diameter=0.04,
    )
    assert np.isclose(
        lp.y_shunt.m.imag * 4,  # because InsulatorType.IP has 4x epsilon_r
        LineParameters.from_geometry(
            id="test",
            line_type=lp.line_type,
            material=lp.material,
            insulator=Insulator.IP,  # 4x epsilon_r of InsulatorType.NONE
            section=lp.section,
            height=-0.5,
            external_diameter=0.04,
        ).y_shunt.m.imag,
    )

    # The same but precise the neutral types
    lp = LineParameters.from_geometry(
        id="test",
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
    assert np.isclose(lp.z_line.m, nplin.inv(y_line_expected)[0, 0], rtol=0.04, atol=0.02)
    assert np.isclose(lp.y_shunt.m, y_shunt_expected[0, 0], rtol=0.001)
    assert lp.line_type == LineType.OVERHEAD
    assert lp.material == Material.AL
    assert lp.insulator == Insulator.PEX
    assert np.isclose(lp.section.m, 150)
    # line_data = {"dpp": 0, "dpn": 0, "dsh": 0.04}

    # Working example (also with string types)
    lp = LineParameters.from_geometry(
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
    assert np.isclose(lp.z_line.m, nplin.inv(y_line_expected)[0, 0], rtol=0.04, atol=0.02)
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
    assert np.isclose(lp.y_shunt.m, y_shunt_expected[0, 0], rtol=0.3)
    assert isinstance(lp.line_type, LineType)
    assert lp.line_type == LineType.UNDERGROUND
    assert lp.material == Material.AL
    assert lp.insulator == Insulator.PVC
    assert np.isclose(lp.section.m, 150)


def test_sym():
    # With the bad model of PwF
    # line_data = {"id": "NKBA NOR  25.00 kV", "un": 25000.0, "in": 277.0000100135803}

    z0 = 0.0j
    z1 = 1.0 + 1.0j
    y0 = 0.0j
    y1 = 1e-06j
    lp = LineParameters.from_sym(id="NKBA NOR  25.00 kV", z0=z0, z1=z1, y0=y0, y1=y1)
    zs = (z0 + 2 * z1) / 3
    ys = (y0 + 2 * y1) / 3
    assert np.isclose(lp.z_line.m, zs)
    assert np.isclose(lp.y_shunt.m, ys)

    # line_data = {"id": "NKBA 4x150   1.00 kV", "un": 1000.0, "in": 361.0000014305115}
    # Downgraded model because of PwF bad data
    lp = LineParameters.from_sym(
        id="NKBA 4x150   1.00 kV", z0=0.5 + 0.3050000071525574j, z1=0.125 + 0.0860000029206276j, y0=0.0j, y1=0.0j
    )
    assert np.isclose(lp.z_line.m, 0.25 + 0.159j)
    assert np.isclose(lp.y_shunt.m, 0)

    # First line
    # line_data = {"id": "sym_neutral_underground_line_example", "un": 400.0, "in": 150}
    lp = LineParameters.from_sym(
        id="sym_neutral_underground_line_example",
        z0=0.188 + 0.8224j,
        z1=0.188 + 0.0812j,
        y0=0.000010462 + 0.000063134j,
        y1=0.000010462 + 0.00022999j,
    )
    assert np.isclose(lp.z_line.m, 0.188 + 0.32826667j)
    assert np.isclose(lp.y_shunt.m, 1.0462e-05 + 1.74371333e-04j)

    # Second line
    # line_data = {"id": "sym_line_example", "un": 20000.0, "in": 309}

    lp = LineParameters.from_sym(id="sym_line_example", z0=0.2 + 0.1j, z1=0.2 + 0.1j, y0=0.00014106j, y1=0.00014106j)
    assert np.isclose(lp.z_line.m, 0.2 + 0.1j)
    assert np.isclose(lp.y_shunt.m, 0.00014106j)


def test_from_coiffier_model():
    # Invalid names
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters.from_coiffier_model("totoU_Al_150")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TYPE_NAME_SYNTAX
    assert e.value.msg == (
        "The Coiffier line parameter name 'totoU_Al_150' is not valid, expected format is "
        "'LineType_Material_CrossSection' or 'LineType_Material_Insulator_CrossSection': 'totoU' "
        "is not a valid LineType"
    )
    with pytest.warns(UserWarning, match=r"The insulator is currently ignored in the Coiffier model, got 'IP'"):
        LineParameters.from_coiffier_model("U_AL_IP_150")

    # Working example with defaults
    lp = LineParameters.from_coiffier_model("U_AL_150")
    z_line_expected = 0.1767 + 0.1j
    y_shunt_expected = 0.00014106j
    assert lp.id == "U_AL_150"
    assert lp.line_type == LineType.UNDERGROUND
    assert lp.material == Material.AL
    assert np.isclose(lp.section.m, 150)
    assert np.isclose(lp.z_line.m_as("ohm/km"), z_line_expected, rtol=0.01, atol=0.01)
    assert np.isclose(lp.y_shunt.m_as("S/km"), y_shunt_expected, rtol=0.01, atol=0.01)
    assert np.isclose(lp.ampacity.m_as("A"), 368.689292)

    # Working example with custom arguments
    lp2 = LineParameters.from_coiffier_model("O_CU_54", id="lp2")
    assert lp2.id == "lp2"
    assert lp2.line_type == LineType.OVERHEAD
    assert lp2.material == Material.CU
    assert np.isclose(lp2.section.m, 54)
    assert isinstance(lp2.z_line.m, complex)
    assert isinstance(lp2.y_shunt.m, complex)


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
        assert isinstance(row.reactance, float)
        assert isinstance(row.susceptance, float)
        assert isinstance(row.ampacity, int | float)
        LineType(row.type)  # Check that the type is valid
        Material(row.material)  # Check that the material is valid
        pd.isna(row.insulator) or Insulator(row.insulator)  # Check that the insulator is valid
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
    assert isinstance(lp.z_line, Q_)
    assert isinstance(lp.z_line.m, complex)
    assert isinstance(lp.y_shunt, Q_)
    assert isinstance(lp.y_shunt.m, complex)
    assert isinstance(lp.ampacity, Q_)
    assert isinstance(lp.ampacity.m, float)
    assert lp.ampacity.m > 0
    assert lp.line_type == LineType.UNDERGROUND
    assert lp.material == Material.AL
    assert lp.insulator is None
    assert isinstance(lp.section, Q_)
    assert lp.section.m == 150

    # Success, overridden ID
    lp = LineParameters.from_catalogue(name="U_AL_150", id="lp1")
    assert lp.id == "lp1"


def test_get_catalogue():
    # Get the entire catalogue
    catalogue = LineParameters.get_catalogue()
    assert isinstance(catalogue, pd.DataFrame)
    assert catalogue.shape == (355, 8)

    # Filter on a single attribute
    for field_name, value, expected_size in (
        ("name", r"U_AL_150.*", 1),
        ("line_type", "OvErHeAd", 122),
        ("material", "Cu", 121),
        # ("insulator", Insulator.SE, 240),
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


def test_insulator():
    z_line = 1 + 2j
    y_shunt = 0.5j

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, insulator=None)
    assert lp.insulator is None
    lp.insulator = np.nan
    assert lp.insulator is None
    lp.insulator = pd.NA
    assert lp.insulator is None

    # Single values
    lp.insulator = Insulator.EPR
    assert lp.insulator == Insulator.EPR

    lp.insulator = Insulator.EPR.name
    assert lp.insulator == Insulator.EPR

    # Special case for Insulator.NONE
    lp.insulator = Insulator.NONE.name
    assert lp.insulator == Insulator.NONE


def test_material():
    z_line = 1 + 2j
    y_shunt = 0.5j

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, material=None)
    assert lp.material is None
    lp.material = np.nan
    assert lp.material is None
    lp.material = pd.NA
    assert lp.material is None

    # Single values
    lp.material = Material.AAAC
    assert lp.material == Material.AAAC

    lp.material = Material.AAAC.name
    assert lp.material == Material.AAAC

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        lp.material = "invalid"
    assert e.value.msg == "'invalid' is not a valid Material"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MATERIAL


def test_section():
    z_line = 1 + 2j
    y_shunt = 0.5j

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, section=None)
    assert lp.section is None
    lp.section = np.nan
    assert lp.section is None
    lp.section = pd.NA
    assert lp.section is None

    # Single values
    lp.section = 4
    assert np.isclose(lp.section.magnitude, 4)

    lp.section = Q_(4, "cm**2")
    assert np.isclose(lp.section.magnitude, 400)

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        lp.section = -1.0
    assert e.value.msg == "Section must be positive: -1.0 mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        lp.section = 0
    assert e.value.msg == "Section must be positive: 0 mm² was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_SECTIONS_VALUE


def test_ampacity():
    z_line = 1 + 2j
    y_shunt = 0.5j

    # None-like values
    lp = LineParameters("test", z_line=z_line, y_shunt=y_shunt, ampacity=None)
    assert lp.ampacity is None
    lp.ampacity = np.nan
    assert lp.ampacity is None
    lp.ampacity = pd.NA
    assert lp.ampacity is None

    # Single values
    lp.ampacity = 4
    assert np.isclose(lp.ampacity.magnitude, 4)

    lp.ampacity = Q_(4, "kA")
    assert np.isclose(lp.ampacity.magnitude, 4000)

    # Errors
    with pytest.raises(RoseauLoadFlowException) as e:
        lp.ampacity = -2
    assert e.value.msg == "Ampacity must be positive: -2 A was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        lp.ampacity = 0
    assert e.value.msg == "Ampacity must be positive: 0 A was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_AMPACITIES_VALUE


def test_json_serialization(tmp_path):
    lp = LineParameters(id="test", z_line=1, section=np.float64(150), ampacity=np.nan, line_type=LineType.OVERHEAD.name)
    assert lp.line_type == LineType.OVERHEAD
    path = tmp_path / "lp.json"
    lp.to_json(path)
    lp_dict = LineParameters.from_json(path).to_dict()
    assert lp_dict["z_line"] == [1, 0]
    assert lp_dict["line_type"] == LineType.OVERHEAD.name
    assert np.isclose(lp_dict["section"], 150)
    assert "ampacity" not in lp_dict


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
    assert np.isclose(lp240sq.z_line.m, zs_e)
    ys_e = 8.796459430051418e-07j
    assert np.isclose(lp240sq.y_shunt.m, ys_e)
    assert lp240sq.line_type is None
    assert lp240sq.ampacity is None

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
    assert np.isclose(lp16sq.z_line.m, zs_e)
    ys_e = 8.795360010050165e-07j
    assert np.isclose(lp16sq.y_shunt.m, ys_e)
    assert lp16sq.line_type == LineType.OVERHEAD
    assert np.isclose(lp16sq.ampacity.m, 400)


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
        "inom": 0.235,  # kA
        "cohl": 0,  # Cable (underground)
        "conductor": "Al",  # Aluminium
        "insulation": 0,  # PVC
        "section": 95,  # mm²
    }
    na2ysy1x95rm = LineParameters.from_power_factory(**pwf_params)

    assert na2ysy1x95rm.id == "NA2YSY 1x95rm 12/20kV it"
    zs_e = 0.645 + 0.2513266666666667j
    assert np.isclose(na2ysy1x95rm.z_line.m, zs_e)
    ys_e = 7.318863666666666e-05j
    assert np.isclose(na2ysy1x95rm.y_shunt.m, ys_e)
    assert np.isclose(na2ysy1x95rm.ampacity.m, 235)
    assert na2ysy1x95rm.line_type == LineType.UNDERGROUND
    assert na2ysy1x95rm.material == Material.AL
    assert na2ysy1x95rm.insulator == Insulator.PVC
    assert np.isclose(na2ysy1x95rm.section.m, 95)

    # String versions of line/insulator type are also accepted
    new_pwf_params = pwf_params | {"cohl": "OHL", "insulation": "XLPE"}
    lp = LineParameters.from_power_factory(**new_pwf_params)
    assert lp.line_type == LineType.OVERHEAD
    assert lp.insulator == Insulator.XLPE


def test_results_to_dict():
    # No results to export
    lp = LineParameters.from_catalogue(name="U_AL_150")
    with pytest.raises(RoseauLoadFlowException) as e:
        lp.results_to_dict()
    assert e.value.msg == "The LineParameters has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS
