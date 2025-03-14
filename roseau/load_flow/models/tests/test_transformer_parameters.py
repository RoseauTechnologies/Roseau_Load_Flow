import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from pint import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import TransformerParameters
from roseau.load_flow.units import Q_


def test_transformer_parameters():
    # Example in the "transformers" document of Victor.
    # Yzn11 - 50kVA
    data = {
        "id": "Yzn11 - 50kVA",
        "psc": 1350.0,  # W
        "p0": 145.0,  # W
        "i0": 1.8 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 50 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "yzn11",
    }
    tp = TransformerParameters.from_dict(data)

    r_iron = 20e3**2 / 145  # Ohm
    lm_omega = 20e3**2 / (np.sqrt((1.8 / 100 * 50e3) ** 2 - 145**2))  # H *rad/s
    z2_norm = 4 / 100 * 400**2 / 50e3
    r2 = 1350 * 400**2 / 50e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = 400 / (np.sqrt(3.0) * 20e3)
    orientation_expected = 1.0

    assert np.isclose(tp.z2.m, z2_expected)
    assert np.isclose(tp.ym.m, ym_expected)
    assert np.isclose(tp.k.m, k_expected)
    assert np.isclose(tp.orientation, orientation_expected)

    # Dyn11 - 100kVA
    data = {
        "id": "Dyn11 - 100kVA",
        "psc": 2150.0,  # W
        "p0": 210.0,  # W
        "i0": 3.5 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 100 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "dyn11",
    }
    tp = TransformerParameters.from_dict(data)
    r_iron = 3 * 20e3**2 / 210  # Ohm
    lm_omega = 3 * 20e3**2 / (np.sqrt((3.5 / 100 * 100e3) ** 2 - 210**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 100e3
    r2 = 2150 * 400**2 / 100e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = (400 / np.sqrt(3)) / 20e3
    orientation_expected = 1.0

    assert np.isclose(tp.z2.m, z2_expected)
    assert np.isclose(tp.ym.m, ym_expected)
    assert np.isclose(tp.k.m, k_expected)
    assert np.isclose(tp.orientation, orientation_expected)

    # Dyn5 - 160kVA
    data = {
        "id": "Dyn5 - 160kVA",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "dyn5",
    }
    tp = TransformerParameters.from_dict(data)
    r_iron = 3 * 20e3**2 / 460  # Ohm
    lm_omega = 3 * 20e3**2 / (np.sqrt((5.6 / 100 * 160e3) ** 2 - 460**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 160e3
    r2 = 2350 * 400**2 / 160e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = 400 / np.sqrt(3) / 20e3
    orientation_expected = -1.0

    assert np.isclose(tp.z2.m, z2_expected)
    assert np.isclose(tp.ym.m, ym_expected)
    assert np.isclose(tp.k.m, k_expected)
    assert np.isclose(tp.orientation, orientation_expected)

    # Check that there is an error if the winding is not good
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "dtotoyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert e.value.msg.startswith("Invalid vector group: 'dtotoyn11'. Expected one of ['Dd0'")
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS

    # UHV == ULV...
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 400,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "dyn11",
    }
    TransformerParameters.from_dict(data)

    # UHV < ULV...
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400.0045,  # V
        "uhv": np.int64(350),  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert e.value.msg == (
        "Transformer parameters 'test' has the low voltage higher than the high voltage: uhv=350 V and ulv=400.0045 V."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES

    # Bad i0
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "vg": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "Invalid open-circuit test current i0=" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS

    # Bad vsc
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 20000,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4,  # %
        "vg": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "Invalid short-circuit test voltage vsc=" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS

    # Bad l2_omega
    data = {
        "id": "test",
        "vg": "Dyn11",
        "sn": 50000.0,
        "uhv": 20000.0,
        "ulv": 400.0,
        "i0": 0.027,
        "p0": 210.0,
        "psc": 2150.0,
        "vsc": 0.04,
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "The following inequality must be respected: psc/sn <= vsc" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS


def test_transformers_parameters_units():
    # Example in the "transformers" document of Victor.
    # Yzn11 - 50kVA. Good units
    data = {
        "id": "Yzn11 - 50kVA",
        "z2": Q_(8.64 + 9.444j, "centiohm"),  # Ohm
        "ym": Q_(0.3625 - 2.2206j, "uS"),  # S
        "ulv": Q_(400, "V"),  # V
        "uhv": Q_(20, "kV"),  # V
        "sn": Q_(50, "kVA"),  # VA
        "vg": "yzn11",
    }
    tp = TransformerParameters(**data)
    assert np.isclose(tp._z2, (0.0864 + 0.0944406692j))
    assert np.isclose(tp._ym, (3.625e-07 - 2.2206e-06j))
    assert np.isclose(tp._ulv, 400)
    assert np.isclose(tp._uhv, 20000)
    assert np.isclose(tp._sn, 50e3)

    # Bad unit for each of them
    for param, fake_quantity in (
        ("z2", Q_(1350.0, "A")),
        ("ym", Q_(145.0, "A")),
        ("ulv", Q_(400, "A")),
        ("uhv", Q_(20, "A")),
        ("sn", Q_(50, "A")),
    ):
        copy_data = data.copy()
        copy_data[param] = fake_quantity
        with pytest.raises(
            DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to '\w+?' \(.+?\)"
        ):
            TransformerParameters(**copy_data)


def test_transformers_parameters_units_from_tests():
    # Example in the "transformers" document of Victor.
    # Yzn11 - 50kVA. Good units
    data = {
        "id": "Yzn11 - 50kVA",
        "psc": Q_(1350.0, "W"),  # W
        "p0": Q_(145.0, "W"),  # W
        "i0": Q_(1.8, "percent"),  # %
        "ulv": Q_(400, "V"),  # V
        "uhv": Q_(20, "kV"),  # V
        "sn": Q_(50, "kVA"),  # VA
        "vsc": Q_(4, "percent"),  # %
        "vg": "yzn11",
    }
    tp = TransformerParameters.from_open_and_short_circuit_tests(**data)
    assert np.isclose(tp._psc, 1350.0)
    assert np.isclose(tp._p0, 145.0)
    assert np.isclose(tp._i0, 1.8e-2)
    assert np.isclose(tp._ulv, 400)
    assert np.isclose(tp._uhv, 20000)
    assert np.isclose(tp._sn, 50e3)
    assert np.isclose(tp._vsc, 4e-2)

    # Bad unit for each of them
    for param, fake_quantity in (
        ("psc", Q_(1350.0, "A")),
        ("p0", Q_(145.0, "A")),
        ("i0", Q_(1.8 / 100, "A")),
        ("ulv", Q_(400, "A")),
        ("uhv", Q_(20, "A")),
        ("sn", Q_(50, "A")),
        ("vsc", Q_(4 / 100, "A")),
    ):
        copy_data = data.copy()
        copy_data[param] = fake_quantity
        with pytest.raises(
            DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to '\w+?' \(.+?\)"
        ):
            TransformerParameters.from_open_and_short_circuit_tests(**copy_data)


def test_transformer_type():
    valid_windings1 = ("y", "yn", "d", "i")
    valid_windings2 = ("y", "yn", "z", "zn", "d", "i", "ii")
    valid_clock_numbers = (0, 5, 6, 11)
    valid_types = {
        "dd",
        "yy",
        "yny",
        "yyn",
        "ynyn",
        "dz",
        "dzn",
        "dy",
        "dyn",
        "yd",
        "ynd",
        "yz",
        "ynz",
        "yzn",
        "ynzn",
        "ii",
        "iii",
    }
    valid_full_types = {
        "dd0",
        "dd6",
        "yy0",
        "yy6",
        "yny0",
        "yny6",
        "yyn0",
        "yyn6",
        "ynyn0",
        "ynyn6",
        "dz0",
        "dz6",
        "dzn0",
        "dzn6",
        "dy5",
        "dy11",
        "dyn5",
        "dyn11",
        "yd5",
        "yd11",
        "ynd5",
        "ynd11",
        "yz5",
        "yz11",
        "ynz5",
        "ynz11",
        "yzn5",
        "yzn11",
        "ynzn5",
        "ynzn11",
        "ii0",
        "ii6",
        "iii0",
        "iii6",
    }

    for winding_hv in valid_windings1:
        for winding_lv in valid_windings2:
            vg = f"{winding_hv}{winding_lv}"
            if vg in valid_types:
                with pytest.raises(RoseauLoadFlowException) as e:
                    TransformerParameters.extract_windings(vg)
                assert e.value.msg.startswith(f"Invalid vector group: '{vg}'. Expected one of ['Dd0'")
                assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS
                for clock_number in valid_clock_numbers:
                    vg = f"{winding_hv}{winding_lv}{clock_number}"
                    if vg in valid_full_types:
                        whv, wlv, clock = TransformerParameters.extract_windings(vg)
                        assert whv == winding_hv.upper()
                        assert wlv == winding_lv
                        assert clock == clock_number
                    else:
                        with pytest.raises(RoseauLoadFlowException) as e:
                            TransformerParameters.extract_windings(vg)
                        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS
            else:
                with pytest.raises(RoseauLoadFlowException) as e:
                    TransformerParameters.extract_windings(vg)
                assert e.value.msg.startswith(f"Invalid vector group: '{vg}'. Expected one of ['Dd0'")
                assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS


def test_catalogue_data():
    # The catalogue data path exists
    catalogue_path = TransformerParameters.catalogue_path()
    assert catalogue_path.exists()

    # Read it and copy it
    catalogue_data = TransformerParameters.catalogue_data()

    # Iterate over the folder and ensure that the elements are in the catalogue data
    error_message = (
        "Something changed in the transformers parameters catalogue. Please regenerate the json files for the "
        "transformers catalogue by using the python file `scripts/generate_transformer_parameters_catalogue.py`. "
        "Don't forget to delete files that are useless too."
    )

    # Check that the name is unique
    assert catalogue_data["name"].is_unique, error_message

    catalogue_data.set_index(keys=["name"], inplace=True)
    for idx in catalogue_data.index:
        tp = TransformerParameters.from_catalogue(name=idx)

        # The entry of the catalogue has been found
        assert tp.id in catalogue_data.index, error_message

        # Check the values are the same
        assert tp.vg == catalogue_data.at[tp.id, "vg"]
        npt.assert_allclose(tp.uhv.m, catalogue_data.at[tp.id, "uhv"])
        npt.assert_allclose(tp.ulv.m, catalogue_data.at[tp.id, "ulv"])
        npt.assert_allclose(tp.sn.m, catalogue_data.at[tp.id, "sn"])
        npt.assert_allclose(tp.p0.m, catalogue_data.at[tp.id, "p0"])
        if pd.isna(tp.i0.m):
            assert pd.isna(catalogue_data.at[tp.id, "i0"])
        else:
            npt.assert_allclose(tp.i0.m, catalogue_data.at[tp.id, "i0"])
        npt.assert_allclose(tp.psc.m, catalogue_data.at[tp.id, "psc"])
        npt.assert_allclose(tp.vsc.m, catalogue_data.at[tp.id, "vsc"])
        assert tp.manufacturer == catalogue_data.at[tp.id, "manufacturer"]
        assert tp.range == catalogue_data.at[tp.id, "range"]
        assert tp.efficiency == catalogue_data.at[tp.id, "efficiency"]

        # Check that the parameters are valid
        assert isinstance(tp.z2.m, complex)
        assert isinstance(tp.ym.m, complex)
        assert isinstance(tp.k.m, float)
        assert tp.orientation in (-1.0, 1.0)


def test_from_catalogue():
    # Unknown strings
    for field_name, display_name in (
        ("name", "name"),
        ("manufacturer", "manufacturer"),
        ("range", "range"),
        ("efficiency", "efficiency"),
        ("vg", "vector group"),
    ):
        # String
        with pytest.raises(RoseauLoadFlowException) as e:
            TransformerParameters.from_catalogue(**{field_name: "unknown"})
        assert e.value.msg.startswith(f"No {display_name} matching 'unknown' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

        # Regexp
        with pytest.raises(RoseauLoadFlowException) as e:
            TransformerParameters.from_catalogue(**{field_name: r"unknown[a-z]+"})
        assert e.value.msg.startswith(f"No {display_name} matching 'unknown[a-z]+' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Unknown floats
    for field_name, display_name, display_unit in (
        ("sn", "nominal power", "kVA"),
        ("uhv", "high voltage", "kV"),
        ("ulv", "low voltage", "kV"),
    ):
        # Without unit
        with pytest.raises(RoseauLoadFlowException) as e:
            TransformerParameters.from_catalogue(**{field_name: 3141.5})
        assert e.value.msg.startswith(f"No {display_name} matching 3.1 {display_unit} has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

        # With unit
        with pytest.raises(RoseauLoadFlowException) as e:
            TransformerParameters.from_catalogue(**{field_name: Q_(3141.5, display_unit.removeprefix("k"))})
        assert e.value.msg.startswith(f"No {display_name} matching 3.1 {display_unit} has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Several transformers
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_catalogue(vg=r"yzn.*", efficiency="A0Ak", sn=50e3)
    assert e.value.msg == (
        "Several transformers matching the query (efficiency='A0Ak', vg='yzn.*', sn=50.0 kVA) have been found: "
        "'SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11', 'SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11'."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND

    # Success
    tp = TransformerParameters.from_catalogue(name="SE Minera AA0Ak 160kVA 20kV 410V Dyn11")
    assert tp.id == "SE Minera AA0Ak 160kVA 20kV 410V Dyn11"
    tp = TransformerParameters.from_catalogue(name="SE Minera AA0Ak 160kVA 20kV 410V Dyn11", id="tp-test1")
    assert tp.id == "tp-test1"


def test_get_catalogue():
    # Get the entire catalogue
    catalogue = TransformerParameters.get_catalogue()
    assert isinstance(catalogue, pd.DataFrame)
    assert catalogue.shape == (327, 9)

    # Filter on a single attribute
    for field_name, value, expected_size in [
        ("name", "SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11", 1),
        ("manufacturer", "SE", 259),
        ("range", r"min.*", 123),
        ("efficiency", r"c0.*", 58),
        ("vg", r"dy.*", 304),
        ("sn", Q_(160, "kVA"), 19),
        ("uhv", Q_(20, "kV"), 175),
        ("ulv", 400, 57),
    ]:
        filtered_catalogue = TransformerParameters.get_catalogue(**{field_name: value})
        assert filtered_catalogue.shape == (expected_size, 9), f"{field_name}={value!r}"

    # Filter on two attributes
    for field_name, value, expected_size in [
        ("name", "SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11", 1),
        ("range", "minera", 123),
        ("efficiency", r"c0.*", 58),
        ("vg", r"^d.*11$", 247),
        ("sn", Q_(160, "kVA"), 17),
        ("uhv", Q_(20, "kV"), 158),
        ("ulv", 400, 1),
    ]:
        filtered_catalogue = TransformerParameters.get_catalogue(**{field_name: value}, manufacturer="se")
        assert filtered_catalogue.shape == (expected_size, 9), f"{field_name}={value!r}"

    # Filter on three attributes
    for field_name, value, expected_size in [
        ("name", "se VEGETA C0BK 3150kva 15/20Kv(20) 410v dyn11", 1),
        ("efficiency", r"c0[abc]k", 30),
        ("vg", r"dyn\d+", 71),
        ("sn", Q_(160, "kVA"), 5),
        ("uhv", Q_(20, "kV"), 41),
        ("ulv", 400, 0),
    ]:
        filtered_catalogue = TransformerParameters.get_catalogue(
            **{field_name: value}, manufacturer="se", range=r"^vegeta$"
        )
        assert filtered_catalogue.shape == (expected_size, 9), f"{field_name}={value!r}"

    # No results
    empty_catalogue = TransformerParameters.get_catalogue(ulv=250)
    assert empty_catalogue.shape == (0, 9)


def test_from_open_dss():
    """https://sourceforge.net/p/electricdss/discussion/beginners/thread/742e6c9665/

    Main input data for transformer:

    - Type: two windings transformer
    - Phases numbers: 3
    - Apparent rated power: 1800 kVA
    - Frequency = 50 Hz
    - Rated line voltage in = 33 kV
    - Rated line voltage out = 0.405 kV
    - Short circuit voltage: 6%
    - Short circuit losses: 0.902%
    - No load current: 0.3%
    - No load losses: 0.136%
    - Connections: DYn
    - Group No: 11
    - Neutral: distributed at side out (low voltage level)
    - Impedance to earth in = 1 MΩ (insulated)
    - Impedance to earth out = 0 Ω
    - Impedance to earth common = 5 Ω "

    OpenDss Model::

        New Transformer.Isacco phases=3 windings=2 XHL=6
        ~ wdg=1 bus=MVbusname kV=33 kVA=1800 conn=delta
        ~ Wdg=2 bus=LVBusname.1.2.3.4 kV=0.405 kVA=1800 conn=wye
        ~ %Loadloss=0.902 %imag=0.3 %noload=.136  LeadLag=Euro
    """
    sn = Q_(1800, "kVA")
    tp_rlf = TransformerParameters.from_open_and_short_circuit_tests(
        id="tp-test",
        # Electrical parameters
        vg="Dyn11",
        uhv=Q_(33, "kV"),
        ulv=Q_(0.405, "kV"),
        sn=sn,
        p0=Q_(0.136, "percent") * sn,
        i0=Q_(0.3, "percent"),
        psc=Q_(0.902, "percent") * sn,
        vsc=Q_(6, "percent"),
        # Optional parameters
        manufacturer="Roseau",
        range="Tech+",
        efficiency="Wonderful",
    )

    tp_dss = TransformerParameters.from_open_dss(
        id="tp-test",
        # Electrical parameters
        conns=("delta", "wye"),
        kvs=(33, 0.405),
        kvas=1800,
        leadlag="euro",
        xhl=6,
        loadloss=0.902,
        noloadloss=0.136,
        imag=0.3,
        # Optional parameters
        manufacturer="Roseau",
        range="Tech+",
        efficiency="Wonderful",
    )

    # Electrical parameters
    assert tp_rlf.vg == tp_dss.vg
    assert tp_rlf.uhv == tp_dss.uhv
    assert tp_rlf.ulv == tp_dss.ulv
    assert tp_rlf.sn == tp_dss.sn
    assert tp_rlf.k == tp_dss.k
    assert tp_rlf.orientation == tp_dss.orientation
    np.testing.assert_allclose(tp_rlf.z2.m, tp_dss.z2.m)
    np.testing.assert_allclose(tp_rlf.ym.m, tp_dss.ym.m)

    # Optional parameters
    assert tp_rlf.manufacturer == tp_dss.manufacturer
    assert tp_rlf.range == tp_dss.range
    assert tp_rlf.efficiency == tp_dss.efficiency


def test_from_power_factory():
    # Parameters from tests/data/dgs/MV_LV_Transformer.json
    tp_pwf = TransformerParameters.from_power_factory(
        id="Transformer 100 kVA Dyn11",
        # Electrical parameters
        tech=3,  # Three Phase Transformer
        sn=0.1,  # MVA
        uhv=20,  # kV
        ulv=0.4,  # kV
        vg_hv="D",
        vg_lv="yn",
        phase_shift=11,
        uk=4,  # Vsc (%)
        pc=2.15,  # Psc (kW)
        curmg=2.5,  # i0 (%)
        pfe=0.21,  # P0 (kW)
        # Optional parameters
        manufacturer="Roseau",
        range="Tech+",
        efficiency="Wonderful",
    )
    tp_rlf = TransformerParameters.from_open_and_short_circuit_tests(
        id="Transformer 100 kVA Dyn11",
        # Electrical parameters
        vg="Dyn11",
        uhv=Q_(20, "kV"),
        ulv=Q_(0.4, "kV"),
        sn=Q_(0.1, "MVA"),
        p0=Q_(0.21, "kW"),
        i0=Q_(2.5, "percent"),
        psc=Q_(2.15, "kW"),
        vsc=Q_(4, "percent"),
        # Optional parameters
        manufacturer="Roseau",
        range="Tech+",
        efficiency="Wonderful",
    )

    # Electrical parameters
    assert tp_pwf.uhv == tp_rlf.uhv
    assert tp_pwf.ulv == tp_rlf.ulv
    assert tp_pwf.sn == tp_rlf.sn
    assert tp_pwf.k == tp_rlf.k
    assert tp_pwf.orientation == tp_rlf.orientation
    np.testing.assert_allclose(tp_pwf.z2.m, tp_rlf.z2.m)
    np.testing.assert_allclose(tp_pwf.ym.m, tp_rlf.ym.m)

    # Optional parameters
    assert tp_pwf.manufacturer == tp_rlf.manufacturer
    assert tp_pwf.range == tp_rlf.range
    assert tp_pwf.efficiency == tp_rlf.efficiency

    # Test single phase (only the technology has been changed)
    tp_pwf = TransformerParameters.from_power_factory(
        id="Transformer 100 kVA Dyn11",
        # Electrical parameters
        tech="single-phase",  # Single Phase Transformer
        sn=0.1,  # MVA
        uhv=20,  # kV
        ulv=0.4,  # kV
        vg_hv="D",
        vg_lv="yn",
        phase_shift=11,
        uk=4,  # Vsc (%)
        pc=2.15,  # Psc (kW)
        curmg=2.5,  # i0 (%)
        pfe=0.21,  # P0 (kW)
        # Optional parameters
        manufacturer="Roseau",
        range="Tech+",
        efficiency="Wonderful",
    )
    assert tp_pwf.type == "single-phase"
    assert tp_pwf.vg == "Ii0"

    # Bad technology
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_power_factory(
            id="Transformer 100 kVA Dyn11",
            # Electrical parameters
            tech="unknown value",  # <-------------Error
            sn=0.1,  # MVA
            uhv=20,  # kV
            ulv=0.4,  # kV
            vg_hv="D",
            vg_lv="yn",
            phase_shift=11,
            uk=4,  # Vsc (%)
            pc=2.15,  # Psc (kW)
            curmg=2.5,  # i0 (%)
            pfe=0.21,  # P0 (kW)
            # Optional parameters
            manufacturer="Roseau",
            range="Tech+",
            efficiency="Wonderful",
        )
    assert (
        e.value.msg == "Expected tech='single-phase' or 'three-phase', got 'unknown value' for transformer parameters "
        "'Transformer 100 kVA Dyn11'."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE


def test_to_dict():
    # No results to export
    tp = TransformerParameters.from_catalogue(name="SE Minera A0Ak 100kVA 15/20kV(20) 410V Dyn11")
    with pytest.raises(RoseauLoadFlowException) as e:
        tp.results_to_dict()
    assert e.value.msg == "The TransformerParameters has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS

    # All the options for to_dict: no short-circuit data but Optional data
    tp2 = TransformerParameters(
        id=tp.id,
        vg=tp.vg,
        uhv=tp.uhv,
        ulv=tp.ulv,
        sn=tp.sn,
        z2=tp.z2,
        ym=tp.ym,
        manufacturer=tp.manufacturer,
        range=tp.range,
        efficiency=tp.efficiency,
    )
    d = tp2.to_dict()
    assert d.pop("id") == tp2.id
    assert d.pop("sn") == tp2.sn.m
    assert d.pop("uhv") == tp2.uhv.m
    assert d.pop("ulv") == tp2.ulv.m
    assert d.pop("vg") == tp2.vg
    assert d.pop("z2") == [tp2.z2.m.real, tp2.z2.m.imag]
    assert d.pop("ym") == [tp2.ym.m.real, tp2.ym.m.imag]
    assert d.pop("manufacturer") == tp2.manufacturer
    assert d.pop("range") == tp2.range
    assert d.pop("efficiency") == tp2.efficiency
    assert not d

    # Test the from_dict without "p0", ... (only z2 and ym)
    tp3 = TransformerParameters.from_dict(tp2.to_dict())
    assert tp3 == tp2


def test_equality():
    data = {
        "id": "Yzn11 - 50kVA",
        "z2": Q_(8.64 + 9.444j, "centiohm"),  # Ohm
        "ym": Q_(0.3625 - 2.2206j, "uS"),  # S
        "ulv": Q_(400, "V"),  # V
        "uhv": Q_(20, "kV"),  # V
        "sn": Q_(50, "kVA"),  # VA
        "vg": "yzn11",
        "manufacturer": "Roseau",
        "range": "Tech+",
        "efficiency": "Extraordinary",
    }

    tp = TransformerParameters(**data)
    tp2 = TransformerParameters(**data)
    assert tp2 == tp

    # Fails
    other_data = {
        "id": "Dyn11 - 49kVA",
        "z2": Q_(8.63 + 9.444j, "centiohm"),  # Ohm
        "ym": Q_(0.48 - 2.2206j, "uS"),  # S
        "ulv": Q_(399, "V"),  # V
        "uhv": Q_(19, "kV"),  # V
        "sn": Q_(49, "kVA"),  # VA
        "vg": "dyn11",
        "manufacturer": "Roso",
        "range": "Tech-",
        "efficiency": "Less extraordinary",
    }
    for k, v in other_data.items():
        other_tp = TransformerParameters(**(data | {k: v}))
        assert other_tp != tp, k

    # Test the case which returns NotImplemented in the equality operator
    assert tp != object()


def test_ideal_transformer():
    # Ideal transformer not yet supported
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters(id="test", vg="Dyn11", sn=50e3, uhv=20e3, ulv=400, z2=0.0, ym=0.0)
    assert e.value.msg == (
        "Transformer parameters 'test' has a null series impedance z2. Ideal transformers are not supported yet."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_IMPEDANCE
    # OK
    TransformerParameters(id="test", vg="Dyn11", sn=50e3, uhv=20e3, ulv=400, z2=0.0000001, ym=0.0)


def test_from_tests_no_leakage_reactance():
    # https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/349
    # Data from LV isolation transformer "DYN11 K13 CU IP21 8" of "ORTEA NEXT"
    # https://www.orteanext.com/product/dyn11-k13-r-ip21/
    tp = TransformerParameters.from_open_and_short_circuit_tests(
        id="DYN11 K13 CU IP21 8",
        vg="Dyn11",
        uhv=Q_(400, "V"),
        ulv=Q_(400, "V"),
        sn=Q_(8, "kVA"),
        p0=Q_(150, "W"),
        i0=Q_(10, "percent"),
        psc=Q_(280, "W"),
        vsc=Q_(3.5, "percent"),
    )
    npt.assert_allclose(tp.z2.m.real, tp.vsc.m * tp.ulv.m**2 / tp.sn.m)  # r2 = |z2|
    npt.assert_allclose(tp.z2.m.imag, 0.0)  # x2 = 0
