import re

import numpy as np
import pandas as pd
import pytest

from roseau.load_flow import Q_, Insulator, LineType, Material, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow import LineParameters as MultiLineParameters
from roseau.load_flow_single.models import Bus, Line, LineParameters


def test_line_parameters():
    bus1 = Bus(id="junction1")
    bus2 = Bus(id="junction2")

    # Negative real values (Z)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters("test", z_line=-3, y_shunt=2)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_LINE_VALUE
    assert e.value.msg == "The z_line value of line type 'test' has negative real part: (-3+0j)"

    # Negative real values (Y)
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters(id="test", z_line=3, y_shunt=-2)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Y_SHUNT_VALUE
    assert e.value.msg == "The y_shunt value of line type 'test' has negative real part: (-2+0j)"

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
    z_line_expected = 0.18842666666666666 + 0.0734465742082604j
    y_shunt_expected = 5.0821451105135946e-05j
    assert np.isclose(lp.z_line.m, z_line_expected, atol=1e-6)
    assert np.isclose(lp.y_shunt.m, y_shunt_expected, atol=1e-4)

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
    assert np.isclose(lp.z_line.m, z_line_expected, atol=1e-6)
    assert np.isclose(lp.y_shunt.m, y_shunt_expected, atol=1e-4)
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
    # TODO regenerate all expected values with the IEC constants and update this test
    z_line_expected = 0.18842666666666666 + 0.08071828175629972j
    y_shunt_expected = 0.0006515742213003806j
    assert np.isclose(lp.z_line.m, z_line_expected, atol=1e-6)
    assert np.isclose(lp.y_shunt.m, y_shunt_expected, atol=1e-4)
    assert isinstance(lp.line_type, LineType)
    assert lp.line_type == LineType.UNDERGROUND
    assert lp.material == Material.AL
    assert lp.insulator == Insulator.PVC
    assert np.isclose(lp.section.m, 150)


def test_sym():
    z0 = 0.0j
    z1 = 1.0 + 1.0j
    y0 = 0.0j
    y1 = 1e-06j
    lp = LineParameters.from_sym(id="NKBA NOR  25.00 kV", z0=z0, z1=z1, y0=y0, y1=y1)
    assert np.isclose(lp.z_line.m, z1)
    assert np.isclose(lp.y_shunt.m, y1)

    # Test optional zero-sequence parameters
    lp2 = LineParameters.from_sym(id="NKBA NOR  25.00 kV", z1=z1, y1=y1)
    assert np.isclose(lp2.z_line.m, z1)
    assert np.isclose(lp2.y_shunt.m, y1)


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
        if not pd.isna(row.insulator):
            Insulator(row.insulator)  # Check that the insulator is valid
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
    r1 = Q_(0.127, "ohm/km")
    x1 = Q_(0.072, "ohm/km")
    r0 = Q_(0.342, "ohm/km")
    x0 = Q_(0.089, "ohm/km")
    c1 = Q_(3.4, "nF/km")
    c0 = Q_(1.6, "nF/km")
    lp240sq = LineParameters.from_open_dss(id="linecode-240sq", r1=r1, x1=x1, r0=r0, x0=x0, c1=c1, c0=c0)
    assert lp240sq.id == "linecode-240sq"
    z_expected = complex(r1.m_as("ohm/km"), x1.m_as("ohm/km"))
    assert np.isclose(lp240sq.z_line.m, z_expected)
    y_expected = complex(0, c1.m_as("F/km") * 2 * np.pi * 50)
    assert np.isclose(lp240sq.y_shunt.m, y_expected)
    assert lp240sq.line_type is None
    assert lp240sq.ampacity is None

    # DSS command: `New LineCode.16sq NPhases=1 R1=0.350, X1=0.025, R0=0.366, X0=0.025, C1=1.036, C0=0.488 Units=kft NormAmps=400 LineType=OH`
    r1 = Q_(0.350, "ohm/kft")
    x1 = Q_(0.025, "ohm/kft")
    r0 = Q_(0.366, "ohm/kft")
    x0 = Q_(0.025, "ohm/kft")
    c1 = Q_(1.036, "nF/kft")
    c0 = Q_(0.488, "nF/kft")
    lp16sq = LineParameters.from_open_dss(
        id="linecode-16sq", r1=r1, x1=x1, r0=r0, x0=x0, c1=c1, c0=c0, linetype="OH", normamps=Q_(400, "A")
    )
    assert lp16sq.id == "linecode-16sq"
    z_expected = complex(r1.m_as("ohm/km"), x1.m_as("ohm/km"))
    assert np.isclose(lp16sq.z_line.m, z_expected)
    y_expected = complex(0, c1.m_as("F/km") * 2 * np.pi * 50)
    assert np.isclose(lp16sq.y_shunt.m, y_expected)
    assert lp16sq.line_type == LineType.OVERHEAD
    assert np.isclose(lp16sq.ampacity.m, 400)

    # Test optional zero-sequence parameters
    lp16sq2 = LineParameters.from_open_dss(id="linecode-16sq-2", r1=r1, x1=x1, c1=c1)
    assert np.isclose(lp16sq2.z_line.m, z_expected)
    assert np.isclose(lp16sq2.y_shunt.m, y_expected)


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
    z_expected = complex(pwf_params["r1"], pwf_params["x1"])
    assert np.isclose(na2ysy1x95rm.z_line.m, z_expected)
    y_expected = complex(0, pwf_params["b1"] * 1e-6)
    assert np.isclose(na2ysy1x95rm.y_shunt.m, y_expected)
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

    # Test optional zero-sequence parameters
    lp2 = LineParameters.from_power_factory(
        id="NA2YSY 1x95rm 12/20kV it", r1=pwf_params["r1"], x1=pwf_params["x1"], b1=pwf_params["b1"]
    )
    assert np.isclose(lp2.z_line.m, z_expected)
    assert np.isclose(lp2.y_shunt.m, y_expected)


def test_from_roseau_load_flow():
    z1 = 1.0 + 2.0j
    y1 = 1e-02j
    lp_m = MultiLineParameters.from_sym(id="LP", z0=1.0, z1=z1, y0=0.2j, y1=y1, zn=1.0, xpn=0.0, bn=0.0, bpn=0.0)
    lp_s = LineParameters.from_roseau_load_flow(lp_m)
    assert np.isclose(lp_s.z_line.m, z1)
    assert np.isclose(lp_s.y_shunt.m, y1)

    lp_m_bad = MultiLineParameters(id="Bad LP", z_line=np.eye(2), y_shunt=np.eye(2))
    with pytest.raises(RoseauLoadFlowException) as e:
        LineParameters.from_roseau_load_flow(lp_m_bad)
    assert e.value.code == RoseauLoadFlowExceptionCode.INVALID_FOR_SINGLE_PHASE
    assert e.value.msg == (
        "Multi-phase line parameters with id 'Bad LP' and 2 phases cannot be converted to "
        "`rlfs.LineParameters`. It must be three-phase."
    )


def test_results_to_dict():
    # No results to export
    lp = LineParameters.from_catalogue(name="U_AL_150")
    with pytest.raises(RoseauLoadFlowException) as e:
        lp.results_to_dict()
    assert e.value.msg == "The LineParameters has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS
