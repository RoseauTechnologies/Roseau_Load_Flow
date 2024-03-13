import numbers

import numpy as np
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
        "type": "yzn11",
    }
    tp = TransformerParameters.from_dict(data)

    z2, ym, k, orientation = tp.to_zyk()
    r_iron = 3 * 20e3**2 / 145  # Ohm
    lm_omega = 3 * 20e3**2 / (np.sqrt((1.8 / 100 * 50e3) ** 2 - 145**2))  # H *rad/s
    z2_norm = 4 / 100 * 400**2 / 50e3
    r2 = 1350 * 400**2 / 50e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = 400 / (np.sqrt(3.0) * 20e3)
    orientation_expected = 1.0

    assert np.isclose(z2.m, z2_expected)
    assert np.isclose(ym.m, ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

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
        "type": "dyn11",
    }
    tp = TransformerParameters.from_dict(data)
    z2, ym, k, orientation = tp.to_zyk()
    r_iron = 3 * 20e3**2 / 210  # Ohm
    lm_omega = 3 * 20e3**2 / (np.sqrt((3.5 / 100 * 100e3) ** 2 - 210**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 100e3
    r2 = 2150 * 400**2 / 100e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = (400 / np.sqrt(3)) / 20e3
    orientation_expected = 1.0

    assert np.isclose(z2.m, z2_expected)
    assert np.isclose(ym.m, ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

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
        "type": "dyn5",
    }
    tp = TransformerParameters.from_dict(data)
    z2, ym, k, orientation = tp.to_zyk()
    r_iron = 3 * 20e3**2 / 460  # Ohm
    lm_omega = 3 * 20e3**2 / (np.sqrt((5.6 / 100 * 160e3) ** 2 - 460**2))  # H*rad/s
    z2_norm = 4 / 100 * 400**2 / 160e3
    r2 = 2350 * 400**2 / 160e3**2  # Ohm
    l2_omega = np.sqrt(z2_norm**2 - r2**2)  # H*rad/s

    ym_expected = 1 / r_iron + 1 / (1j * lm_omega)
    z2_expected = r2 + 1j * l2_omega
    k_expected = 400 / np.sqrt(3) / 20e3
    orientation_expected = -1.0

    assert np.isclose(z2.m, z2_expected)
    assert np.isclose(ym.m, ym_expected)
    assert np.isclose(k, k_expected)
    assert np.isclose(orientation, orientation_expected)

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
        "type": "dtotoyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "Transformer windings cannot be extracted from the string" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS

    # UHV == ULV...
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 401,  # V
        "uhv": 400,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the low voltages higher than the high voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES

    # UHV < ULV...
    data = {
        "id": "test",
        "psc": 2350.0,  # W
        "p0": 460.0,  # W
        "i0": 5.6 / 100,  # %
        "ulv": 400,  # V
        "uhv": 350,  # V
        "sn": 160 * 1e3,  # VA
        "vsc": 4 / 100,  # %
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the low voltages higher than the high voltages" in e.value.msg
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
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the 'current during off-load test' i0" in e.value.msg
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
        "type": "dyn11",
    }
    with pytest.raises(RoseauLoadFlowException) as e:
        TransformerParameters.from_dict(data)
    assert "has the 'voltages on LV side during short-circuit test' vsc" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS

    # Bad l2_omega
    data = {
        "id": "test",
        "type": "Dyn11",
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
    assert "The following inequality should be respected: psc/sn <= vsc" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS


def test_transformers_parameters_units():
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
        "type": "yzn11",
    }
    tp = TransformerParameters.from_dict(data)
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
            TransformerParameters.from_dict(copy_data)


def test_transformer_type():
    valid_windings = ("y", "yn", "z", "zn", "d")
    valid_phase_displacements = (0, 5, 6, 11)
    valid_types = {"dd", "yy", "yny", "yyn", "ynyn", "dz", "dzn", "dy", "dyn", "yd", "ynd", "yz", "ynz", "yzn", "ynzn"}
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
    }

    for winding1 in valid_windings:
        for winding2 in valid_windings:
            t = f"{winding1}{winding2}"
            if t in valid_types:
                with pytest.raises(RoseauLoadFlowException) as e:
                    TransformerParameters.extract_windings(t)
                assert "Transformer windings cannot be extracted from the string" in e.value.msg
                assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS
                for phase_displacement in valid_phase_displacements:
                    t = f"{winding1}{winding2}{phase_displacement}"
                    if t in valid_full_types:
                        w1, w2, p = TransformerParameters.extract_windings(t)
                        assert w1 == winding1.upper()
                        assert w2 == winding2
                        assert p == phase_displacement
                    else:
                        with pytest.raises(RoseauLoadFlowException) as e:
                            TransformerParameters.extract_windings(t)
                        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS
            else:
                with pytest.raises(RoseauLoadFlowException) as e:
                    TransformerParameters.extract_windings(t)
                assert "Transformer windings cannot be extracted from the string" in e.value.msg
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

    # Check that the id is unique
    assert catalogue_data["id"].is_unique, error_message

    catalogue_data.set_index("id", inplace=True)
    for idx in catalogue_data.index:
        tp = TransformerParameters.from_catalogue(id=idx)

        # The entry of the catalogue has been found
        assert tp.id in catalogue_data.index, error_message

        # Check the values are the same
        assert tp.type == catalogue_data.at[tp.id, "type"]
        assert np.isclose(tp.uhv.m, catalogue_data.at[tp.id, "uhv"])
        assert np.isclose(tp.ulv.m, catalogue_data.at[tp.id, "ulv"])
        assert np.isclose(tp.sn.m, catalogue_data.at[tp.id, "sn"])
        assert np.isclose(tp.p0.m, catalogue_data.at[tp.id, "p0"])
        assert np.isclose(tp.i0.m, catalogue_data.at[tp.id, "i0"])
        assert np.isclose(tp.psc.m, catalogue_data.at[tp.id, "psc"])
        assert np.isclose(tp.vsc.m, catalogue_data.at[tp.id, "vsc"])

        # Check that the parameters are valid
        z, y, k, orientation = tp.to_zyk()
        assert isinstance(z.m, numbers.Complex)
        assert isinstance(y.m, numbers.Complex)
        assert isinstance(k.m, numbers.Real)
        assert orientation in (-1.0, 1.0)


def test_from_catalogue():
    # Unknown strings
    for field_name in ("id", "manufacturer", "range", "efficiency", "type"):
        # String
        with pytest.raises(RoseauLoadFlowException) as e:
            TransformerParameters.from_catalogue(**{field_name: "unknown"})
        assert e.value.msg.startswith(f"No {field_name} matching 'unknown' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

        # Regexp
        with pytest.raises(RoseauLoadFlowException) as e:
            TransformerParameters.from_catalogue(**{field_name: r"unknown[a-z]+"})
        assert e.value.msg.startswith(f"No {field_name} matching 'unknown[a-z]+' has been found. Available ")
        assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_NOT_FOUND

    # Unknown floats
    for field_name, display_name, display_unit in (
        ("sn", "nominal power", "kVA"),
        ("uhv", "primary side voltage", "kV"),
        ("ulv", "secondary side voltage", "kV"),
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
        TransformerParameters.from_catalogue(type="yzn", sn=50e3)
    assert e.value.msg == (
        "Several transformers matching the query (type='yzn', nominal power=50.0 kVA) have been "
        "found: 'SE_Minera_A0Ak_50kVA', 'SE_Minera_B0Bk_50kVA', 'SE_Minera_C0Bk_50kVA', "
        "'SE_Minera_Standard_50kVA'."
    )
    assert e.value.code == RoseauLoadFlowExceptionCode.CATALOGUE_SEVERAL_FOUND


def test_get_catalogue():
    # Get the entire catalogue
    catalogue = TransformerParameters.get_catalogue()
    assert isinstance(catalogue, pd.DataFrame)
    assert catalogue.shape == (162, 7)

    # Filter on a single attribute
    for field_name, value, expected_size in (
        ("id", "SE_Minera_A0Ak_50kVA", 1),
        ("manufacturer", "SE", 148),
        ("range", r"min.*", 67),
        ("efficiency", "c0", 29),
        ("type", "dy", 158),
        ("sn", Q_(160, "kVA"), 12),
        ("uhv", Q_(20, "kV"), 162),
        ("ulv", 400, 162),
    ):
        filtered_catalogue = TransformerParameters.get_catalogue(**{field_name: value})
        assert filtered_catalogue.shape == (expected_size, 7), f"{field_name}={value!r}"

    # Filter on two attributes
    for field_name, value, expected_size in (
        ("id", "SE_Minera_A0Ak_50kVA", 1),
        ("range", "minera", 67),
        ("efficiency", "c0", 29),
        ("type", r"^d.*11$", 144),
        ("sn", Q_(160, "kVA"), 11),
        ("uhv", Q_(20, "kV"), 148),
        ("ulv", 400, 148),
    ):
        filtered_catalogue = TransformerParameters.get_catalogue(**{field_name: value}, manufacturer="se")
        assert filtered_catalogue.shape == (expected_size, 7), f"{field_name}={value!r}"

    # Filter on three attributes
    for field_name, value, expected_size in (
        ("id", "se_VEGETA_C0BK_3150kva", 1),
        ("efficiency", r"c0[abc]k", 15),
        ("type", "dyn", 41),
        ("sn", Q_(160, "kVA"), 3),
        ("uhv", Q_(20, "kV"), 41),
        ("ulv", 400, 41),
    ):
        filtered_catalogue = TransformerParameters.get_catalogue(
            **{field_name: value}, manufacturer="se", range=r"^vegeta$"
        )
        assert filtered_catalogue.shape == (expected_size, 7), f"{field_name}={value!r}"

    # No results
    empty_catalogue = TransformerParameters.get_catalogue(ulv=250)
    assert empty_catalogue.shape == (0, 7)


def test_max_power():
    kwds = {
        "type": "yzn11",
        "psc": 1350.0,
        "p0": 145.0,
        "i0": 1.8 / 100,
        "ulv": 400,
        "uhv": 20000,
        "sn": 50 * 1e3,
        "vsc": 4 / 100,
    }
    tp = TransformerParameters("test", **kwds)
    assert tp.max_power is None

    tp = TransformerParameters("test", **kwds, max_power=60_000)
    assert tp.max_power == Q_(60_000, "VA")

    tp.max_power = 55_000
    assert tp.max_power == Q_(55_000, "VA")

    tp.max_power = None
    assert tp.max_power is None

    tp.max_power = Q_(65, "kVA")
    assert tp.max_power == Q_(65_000, "VA")
