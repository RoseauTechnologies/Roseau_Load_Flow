import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow.converters import calculate_voltages
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, VoltageSource
from roseau.load_flow.units import Q_


def test_sources():
    bus = Bus(id="bus", phases="abcn")
    # Bad number of phases
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="vs1", bus=bus, phases="abcn", voltages=[230, 230j])
    assert "Incorrect number of voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="vs2", bus=bus, phases="abcn", voltages=[230, 230j, -230, -230j])
    assert "Incorrect number of voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="vs3", bus=bus, phases="abc", voltages=[230, 230j])
    assert "Incorrect number of voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        VoltageSource(id="vs4", bus=bus, phases="abc", voltages=[100, 100, 100, 100])
    assert "Incorrect number of voltages" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE

    # Update
    sources = [
        VoltageSource(id="vs5", bus=bus, phases="abcn", voltages=[100, 100, 100]),
        VoltageSource(id="vs6", bus=bus, phases="abc", voltages=[100, 100, 100]),
    ]
    for source in sources:
        with pytest.raises(RoseauLoadFlowException) as e:
            source.voltages = [100, 100]
        assert "Incorrect number of voltages" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            source.voltages = [100, 100, 100, 100]
        assert "Incorrect number of voltages" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_VOLTAGES_SIZE


def test_sources_to_dict():
    bus = Bus(id="bus", phases="abcn")
    values = [1 + 2j, 3 + 4j, 5 + 6j]

    # Power source
    assert VoltageSource(id="vs1", bus=bus, phases="abcn", voltages=values).to_dict(include_results=False) == {
        "id": "vs1",
        "bus": "bus",
        "phases": "abcn",
        "voltages": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
        "connect_neutral": True,
    }
    assert VoltageSource(id="vs2", bus=bus, phases="abc", voltages=values).to_dict(include_results=False) == {
        "id": "vs2",
        "bus": "bus",
        "phases": "abc",
        "voltages": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
        "connect_neutral": True,
    }


def test_sources_units():
    bus = Bus(id="bus", phases="abcn")

    # Good unit constructor
    source = VoltageSource(id="vs1", bus=bus, voltages=Q_([1, 1, 1], "kV"), phases="abcn")
    assert np.allclose(source._voltages, [1000, 1000, 1000])

    # Good unit setter
    source = VoltageSource(id="vs2", bus=bus, voltages=[100, 100, 100], phases="abcn")
    assert np.allclose(source._voltages, [100, 100, 100])
    source.voltages = Q_([1, 1, 1], "kV")
    assert np.allclose(source._voltages, [1000, 1000, 1000])

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'V'"):
        VoltageSource(id="vs3", bus=bus, voltages=Q_([100, 100, 100], "A"), phases="abcn")

    # Bad unit setter
    source = VoltageSource(id="vs4", bus=bus, voltages=[100, 100, 100], phases="abcn")
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'V'"):
        source.voltages = Q_([100, 100, 100], "A")


@pytest.mark.parametrize(
    ("bus_ph", "source_ph", "res_pot", "res_cur"),
    (
        pytest.param(
            "abcn",
            "abcn",
            [
                2.29564186e02 + 3.57582604e-04j,
                -1.14891305e02 - 1.98997577e02j,
                -1.14781783e02 + 1.98808595e02j,
                1.08902102e-01 + 1.88623974e-01j,
            ],
            [
                0.43581447 - 3.57582604e-04j,
                -0.10869546 - 1.88266054e-01j,
                -0.21821691 + 3.77247611e-01j,
                -0.1089021 - 1.88623974e-01j,
            ],
            id="abcn,abcn",
        ),
        pytest.param(
            "abcn",
            "bn",
            [
                2.30000000e02 + 0.0j,
                -1.14781781e02 - 198.80787565j,
                -1.15000000e02 + 199.18584287j,
                -2.18219474e-01 - 0.37796722j,
            ],
            [-0.21821947 - 0.37796722j, 0.21821947 + 0.37796722j],
            id="abcn,bn",
        ),
        pytest.param(
            "abcn",
            "abn",
            [
                229.56376987 - 3.56904091e-04j,
                -114.89089301 - 1.98997578e02j,
                -115.0 + 1.99185843e02j,
                0.32712315 - 1.87908131e-01j,
            ],
            [0.43623013 + 0.0003569j, -0.10910699 - 0.18826504j, -0.32712315 + 0.18790813j],
            id="abcn,abn",
        ),
        pytest.param(
            "abcn",
            "abc",
            [
                229.56453031 - 8.54648227e-24j,
                -114.78226516 - 1.98934385e02j,
                -114.78226516 + 1.98934385e02j,
                0.0 + 0.00000000e00j,
            ],
            [0.43546969 + 0.0j, -0.21773484 - 0.25145831j, -0.21773484 + 0.25145831j],
            id="abcn,abc",
        ),
        pytest.param(
            "abcn",
            "ab",
            [
                229.78233438 - 1.25669301e-01j,
                -114.78233438 - 1.99060174e02j,
                -115.0 + 1.99185843e02j,
                0.0 + 0.00000000e00j,
            ],
            [0.21766596 + 0.1256695j, -0.21766596 - 0.1256695j],
            id="abcn,ab",
        ),
        pytest.param(
            "abc",
            "abc",
            [229.56453031 - 1.70412303e-23j, -114.78226516 - 1.98934385e02j, -114.78226516 + 1.98934385e02j],
            [0.43546969 + 0.0j, -0.21773484 - 0.25145831j, -0.21773484 + 0.25145831j],
            id="abc,abc",
        ),
        pytest.param(
            "abc",
            "ab",
            [229.78233438 - 1.25669301e-01j, -114.78233438 - 1.99060174e02j, -115.0 + 1.99185843e02j],
            [0.21766596 + 0.1256695j, -0.21766596 - 0.1256695j],
            id="abc,ab",
        ),
        pytest.param(
            "bcn",
            "cn",
            [-115.0 - 199.18584287j, -114.78178053 + 198.80787565j, -0.21821947 + 0.37796722j],
            [-0.21821947 + 0.37796722j, 0.21821947 - 0.37796722j],
            id="bcn,cn",
        ),
    ),
)
def test_source_res_voltages(bus_ph, source_ph, res_pot, res_cur):
    bus = Bus(id="bus", phases=bus_ph)
    bus._res_potentials = np.array(res_pot, dtype=complex)
    voltages = calculate_voltages(bus._get_potentials_of(source_ph, warning=False), source_ph)
    source = VoltageSource(id="source", bus=bus, voltages=voltages, phases=source_ph)
    source._res_currents = np.array(res_cur, dtype=complex)
    source._res_potentials = bus._get_potentials_of(source.phases, warning=False)
    assert np.allclose(source.res_voltages, source.voltages)


@pytest.mark.parametrize(
    ("bus_ph", "source_ph", "bus_vph", "source_vph"),
    (
        pytest.param("abcn", "abcn", ["an", "bn", "cn"], ["an", "bn", "cn"], id="abcn,abcn"),
        pytest.param("abcn", "abc", ["an", "bn", "cn"], ["ab", "bc", "ca"], id="abcn,abc"),
        pytest.param("abcn", "can", ["an", "bn", "cn"], ["cn", "an"], id="abcn,can"),
        pytest.param("abcn", "bn", ["an", "bn", "cn"], ["bn"], id="abcn,bn"),
        pytest.param("bcn", "bn", ["bn", "cn"], ["bn"], id="bcn,bn"),
        pytest.param("bcn", "bc", ["bn", "cn"], ["bc"], id="bcn,bc"),
        pytest.param("bn", "bn", ["bn"], ["bn"], id="bn,bn"),
        pytest.param("abc", "abc", ["ab", "bc", "ca"], ["ab", "bc", "ca"], id="abc,abc"),
        pytest.param("abc", "bc", ["ab", "bc", "ca"], ["bc"], id="abc,bc"),
        pytest.param("bc", "bc", ["bc"], ["bc"], id="bc,bc"),
    ),
)
def test_source_voltages(bus_ph, source_ph, bus_vph, source_vph):
    bus = Bus("bus", phases=bus_ph)
    voltages = [100, 200, 300]
    source = VoltageSource("source", bus, voltages=voltages[: len(source_vph)], phases=source_ph)

    res_pot = [230 + 0j, 230 * np.exp(1j * 2 * np.pi / 3), 230 * np.exp(1j * 4 * np.pi / 3), 0j]
    bus._res_potentials = np.array(res_pot[: len(bus_ph)], dtype=complex)

    res_cur = [0.1 + 0j, 0.2 + 0j, 0.3 + 0j, 0.6 + 0j]
    source._res_currents = np.array(res_cur[: len(source_ph)], dtype=complex)
    source._res_potentials = bus._get_potentials_of(phases=source.phases, warning=False)

    assert bus.voltage_phases == bus_vph
    assert len(bus.res_voltages) == len(bus.voltage_phases)

    assert source.voltage_phases == source_vph
    assert len(source.res_voltages) == len(source.voltage_phases)
