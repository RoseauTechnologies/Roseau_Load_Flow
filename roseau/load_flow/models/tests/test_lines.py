import numpy as np
import pytest
from pint import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, Ground, Line, LineParameters
from roseau.load_flow.sym import PositiveSequence as PosSeq
from roseau.load_flow.units import Q_


def test_lines_length():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    lp = LineParameters(id="lp", z_line=np.eye(4, dtype=complex))

    # Negative value for length in the constructor
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=-5)
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(-5, "m"))
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # Test on the length setter
    line = Line(id="line3", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "m"))
    with pytest.raises(RoseauLoadFlowException) as e:
        line.length = -6.5
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE

    # The same with a unit
    with pytest.raises(RoseauLoadFlowException) as e:
        line.length = Q_(-6.5, "cm")
    assert "A line length must be greater than 0." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_LENGTH_VALUE


def test_lines_units():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")
    lp = LineParameters(id="lp", z_line=np.eye(4, dtype=complex))

    # Good unit constructor
    line = Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "km"))
    assert np.isclose(line._length, 5)

    # Good unit setter
    line = Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    assert np.allclose(line._length, 5)
    line.length = Q_(6.5, "m")
    assert np.isclose(line._length, 6.5e-3)

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        Line(id="line3", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(5, "A"))

    # Bad unit setter
    line = Line(id="line4", bus1=bus1, bus2=bus2, parameters=lp, length=5)
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'km'"):
        line.length = Q_(6.5, "A")


def test_line_parameters_shortcut():
    bus1 = Bus(id="bus1", phases="abcn")
    bus2 = Bus(id="bus2", phases="abcn")

    #
    # Without shunt
    #
    lp = LineParameters(id="lp", z_line=np.eye(4, dtype=complex))

    # Z
    line = Line(id="line1", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))
    assert np.allclose(line.z_line.m_as("ohm"), 0.05 * np.eye(4, dtype=complex))

    # Y
    assert not line.with_shunt
    assert np.allclose(line.y_shunt.m_as("S"), np.zeros(shape=(4, 4), dtype=complex))

    #
    # With shunt
    #
    z_line = 0.01 * np.eye(4, dtype=complex)
    y_shunt = 1e-5 * np.eye(4, dtype=complex)
    lp = LineParameters(id="lp", z_line=z_line, y_shunt=y_shunt)

    # Z
    ground = Ground("ground")
    line = Line(id="line2", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"), ground=ground)
    assert np.allclose(line.z_line.m_as("ohm"), 0.05 * z_line)

    # Y
    assert line.with_shunt
    assert np.allclose(line.y_shunt.m_as("S"), 0.05 * y_shunt)


def test_line_ground(recwarn):
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abc")
    z_line = 0.01 * np.eye(3, dtype=complex)
    y_shunt = 1e-5 * np.eye(3, dtype=complex)
    lp_with_shunt = LineParameters(id="lp_with_shunt", z_line=z_line, y_shunt=y_shunt)
    lp_without_shunt = LineParameters(id="lp_without_shunt", z_line=z_line)
    ground = Ground(id="ground")

    # Create a line with a useless ground
    recwarn.clear()
    line_without_shunt = Line(
        id="line", bus1=bus1, bus2=bus2, parameters=lp_without_shunt, length=Q_(50, "m"), ground=ground
    )
    assert len(recwarn) == 1
    assert recwarn[0].category is UserWarning
    assert (
        recwarn[0].message.args[0]
        == "The ground element must not be provided for line 'line' as it does not have a shunt admittance."
    )
    assert line_without_shunt.ground is None

    # assign a line parameter with shunt to a line without ground
    line_without_shunt._initialized = False  # To reach the last option of the parameters setter
    with pytest.raises(RoseauLoadFlowException) as e:
        line_without_shunt.parameters = lp_with_shunt
    assert e.value.msg == "The ground element must be provided for line 'line' with shunt admittance."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_TYPE


def test_max_loading():
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abc")
    lp = LineParameters(id="lp", z_line=np.eye(3, dtype=complex))
    line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))

    # Value must be positive
    with pytest.raises(RoseauLoadFlowException) as e:
        line.max_loading = -1
    assert e.value.msg == "Maximum loading must be positive: -1 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        line.max_loading = 0
    assert e.value.msg == "Maximum loading must be positive: 0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_MAX_LOADING_VALUE


def test_res_violated():
    bus1 = Bus(id="bus1", phases="abc")
    bus2 = Bus(id="bus2", phases="abc")
    lp = LineParameters(id="lp", z_line=np.eye(3, dtype=complex))
    line = Line(id="line", bus1=bus1, bus2=bus2, parameters=lp, length=Q_(50, "m"))

    bus1._res_potentials = 230 * PosSeq
    bus2._res_potentials = 225 * PosSeq
    line._res_currents = 10 * PosSeq, -10 * PosSeq

    # No limits
    assert line.max_loading == Q_(1, "")
    assert line.res_violated is None

    # No constraint violated
    lp.ampacities = 11
    assert (line.res_violated == [False, False, False]).all()
    np.testing.assert_allclose(line.res_loading.m, 10 / 11)

    # Reduced max_loading
    line.max_loading = Q_(50, "%")
    assert line.max_loading.m == 0.5
    assert (line.res_violated == [True, True, True]).all()
    np.testing.assert_allclose(line.res_loading.m, 10 / 11)

    # Two sides violations
    lp.ampacities = 9
    line.max_loading = 1
    assert (line.res_violated == [True, True, True]).all()
    np.testing.assert_allclose(line.res_loading.m, 10 / 9)

    # Side 1 violation
    lp.ampacities = 11
    line._res_currents = 12 * PosSeq, -10 * PosSeq
    assert (line.res_violated == [True, True, True]).all()
    np.testing.assert_allclose(line.res_loading.m, 12 / 11)

    # Side 2 violation
    lp.ampacities = 11
    line._res_currents = 10 * PosSeq, -12 * PosSeq
    assert (line.res_violated == [True, True, True]).all()
    np.testing.assert_allclose(line.res_loading.m, 12 / 11)

    # A single phase violation
    lp.ampacities = 11
    line._res_currents = 10 * PosSeq, -10 * PosSeq
    line._res_currents[0][0] = 12
    line._res_currents[1][0] = -12
    assert (line.res_violated == [True, False, False]).all()
    np.testing.assert_allclose(line.res_loading.m, [12 / 11, 10 / 11, 10 / 11])

    #
    # The same with arrays
    #
    line._res_currents = 10 * PosSeq, -10 * PosSeq

    # No constraint violated
    lp.ampacities = [11, 12, 13]
    line.max_loading = 1
    assert (line.res_violated == [False, False, False]).all()
    np.testing.assert_allclose(line.res_loading.m, [10 / 11, 10 / 12, 10 / 13])

    # Two sides violations
    lp.ampacities = [9, 9, 12]
    assert (line.res_violated == [True, True, False]).all()
    np.testing.assert_allclose(line.res_loading.m, [10 / 9, 10 / 9, 10 / 12])

    # Side 1 violation
    lp.ampacities = [11, 13, 11]
    line._res_currents = 12 * PosSeq, -10 * PosSeq
    assert (line.res_violated == [True, False, True]).all()
    np.testing.assert_allclose(line.res_loading.m, [12 / 11, 12 / 13, 12 / 11])

    # Side 2 violation
    lp.ampacities = [11, 11, 13]
    line._res_currents = 10 * PosSeq, -12 * PosSeq
    assert (line.res_violated == [True, True, False]).all()
    np.testing.assert_allclose(line.res_loading.m, [12 / 11, 12 / 11, 12 / 13])


@pytest.mark.parametrize(
    ("phases", "z_line", "y_shunt", "len_line", "bus_pot", "line_cur", "ground_pot", "expected_pow"),
    (
        pytest.param(
            {"bus1": "abcn", "bus2": "abcn", "line": "abcn"},
            (0.1 + 0.1j) / 2 * np.eye(4, dtype=complex),
            None,
            10,
            (
                [20000.0 + 0.0j, -10000.0 - 17320.50807569j, -10000.0 + 17320.50807569j, 0.0 + 0.0j],
                [
                    1.99621674e04 - 62.38453592j,
                    -1.00176882e04 - 17288.64531401j,
                    -9.92685604e03 + 17319.05036774j,
                    -1.76232064e01 + 31.97948219j,
                ],
            ),
            (
                [
                    100.21710731 + 24.55196453j,
                    -14.1745826 - 49.55094075j,
                    -71.68624893 + 74.60166483j,
                    -14.35627577 - 49.60268862j,
                ],
                [
                    -100.21710731 - 24.55196453j,
                    14.1745826 + 49.55094075j,
                    71.68624893 - 74.60166483j,
                    14.35627577 + 49.60268862j,
                ],
            ),
            None,
            (
                [
                    2004342.14612294 - 491039.29068267j,
                    999993.29542839 - 249998.43500887j,
                    2009001.22751577 - 495625.6052414j,
                    -0.0 + 0.0j,
                ],
                [
                    -1.99901901e06 + 496362.42446232j,
                    -9.98665188e05 + 251326.54226938j,
                    -2.00364906e06 + 500977.76858232j,
                    1.33326469e03 + 1333.26468605j,
                ],
                [
                    5323.13594471 + 5323.13594471j,
                    1328.10800112 + 1328.10800112j,
                    5352.16379695 + 5352.16379695j,
                    1333.26468496 + 1333.26468496j,
                ],
            ),
            id="abcn-abcn,abcn",
        ),
        pytest.param(
            {"bus1": "abcn", "bus2": "abc", "line": "abc"},
            (0.1 + 0.1j) / 2 * np.eye(3, dtype=complex),
            None,
            10,
            (
                [20000.0 + 0.0j, -10000.0 - 17320.50807569j, -10000.0 + 17320.50807569j, 0.0 + 0.0j],
                [
                    19962.27794964 - 62.50004648j,
                    -10017.22332639 - 17267.46636437j,
                    -9945.05462325 + 17329.96641085j,
                ],
            ),
            (
                [100.22209684 + 24.77799611j, -35.81838493 - 70.26503771j, -64.40371192 + 45.48704159j],
                [-100.22209684 - 24.77799611j, 35.81838493 + 70.26503771j, 64.40371192 - 45.48704159j],
            ),
            None,
            (
                [
                    2004441.93685032 - 495559.92229999j,
                    1575210.00228621 - 82257.75171098j,
                    1431895.79039895 - 660634.59645348j,
                ],
                [
                    -1999112.72795683 + 500889.13119348j,
                    -1572099.93617494 + 85367.81782226j,
                    -1428787.33586821 + 663743.05098422j,
                ],
                [5329.20889349 + 5329.20889349j, 3110.06611127 + 3110.06611127j, 3108.45453074 + 3108.45453074j],
            ),
            id="abcn-abc,abc",
        ),
        pytest.param(
            {"bus1": "an", "bus2": "an", "line": "an"},
            np.eye(2, dtype=complex),
            None,
            1,
            ([230.0 + 0.0j, 0.0 + 0.0j], [225.47405027 + 0.0j, 4.52594973 + 0.0j]),
            ([4.52594973 + 0.0j, -4.52594973 + 0.0j], [-4.52594973 - 0.0j, 4.52594973 - 0.0j]),
            None,
            (
                [1040.9684375398983 + 0j, 0.0 - 0.0j],
                [-1020.4842166 + 0.0j, 20.48422094 + 0.0j],
                [20.484220944314885 + 0j, 20.484220944314885 + 0j],
            ),
            id="an-an,an,1",
        ),
        pytest.param(  # Verified manually and with pandapower
            {"bus1": "an", "bus2": "an", "line": "an"},
            (0.1 + 0.1j) / 2 * np.eye(2, dtype=complex),
            None,
            10,
            ([20000.0 + 0.0j, 0.0 + 0.0j], [19961.964706645947 - 62.5j, 38.035293354052556 + 62.5j]),
            (
                [100.53529335405256 + 24.464706645947444j, -100.53529335405256 - 24.464706645947444j],
                [-100.53529335405256 - 24.464706645947444j, 100.53529335405256 + 24.464706645947444j],
            ),
            None,
            (
                [2010705.86708105 - 489294.13291895j, -0.0 + 0.0j],
                [-2005352.93354052 + 494647.06645948j, 5352.93354053 + 5352.93354053j],
                [5352.933540528835 + 5352.933540528836j, 5352.933540528835 + 5352.933540528836j],
            ),
            id="an-an,an,10",
        ),
        pytest.param(
            {"bus1": "abcn", "bus2": "abc", "line": "abc"},
            [
                [0.12918333333333334 + 0.10995533333333332j, 0.05497783333333334j, 0.05497783333333334j],
                [0.05497783333333334j, 0.12918333333333334 + 0.10995533333333332j, 0.05497783333333334j],
                [0.05497783333333334j, 0.05497783333333334j, 0.12918333333333334 + 0.10995533333333332j],
            ],
            [
                [4.930205666666666e-05j, 6.073716666666661e-07j, 6.073716666666661e-07j],
                [6.073716666666661e-07j, 4.930205666666666e-05j, 6.073716666666661e-07j],
                [6.073716666666661e-07j, 6.073716666666661e-07j, 4.930205666666666e-05j],
            ],
            10,
            (
                [
                    11547.005383792517 + 0j,
                    -5773.502691896257 - 10000.000000000002j,
                    -5773.502691896257 + 10000.000000000002j,
                    0j,
                ],
                [
                    11455.159113672085 + 1.0958017067068913j,
                    -5723.334202012903 - 9947.26661034906j,
                    -5731.824911659177 + 9946.17080864235j,
                ],
            ),
            (
                [
                    59.88964164257595 - 23.524538885127185j,
                    -45.15366676852227 - 21.973732003466466j,
                    -14.735974874052772 + 45.49827088859456j,
                ],
                [
                    -59.88990844117143 + 29.124954657737362j,
                    50.01029608953468 + 19.17455774824157j,
                    9.879612351638343 - 48.29951240597802j,
                ],
            ),
            0j,
            (
                [
                    691546.014480241 + 271637.9771577995j,
                    480432.1366716957 + 324671.26681220764j,
                    540060.8994889962 + 115324.64071139487j,
                ],
                [
                    -686016.5153219448 - 333696.6172467909j,
                    -476960.0761193553 - 387723.34629617876j,
                    -537023.4085587 - 178580.03645703004j,
                ],
                [
                    5529.49915838859 + 2353.2295702256074j,
                    3472.060552425377 + 1477.630311089882j,
                    3037.4909303430604 + 1292.687325167883j,
                ],
            ),
            id="abcn-abc,abc,shunt",
        ),
    ),
)
def test_lines_results(phases, z_line, y_shunt, len_line, bus_pot, line_cur, ground_pot, expected_pow):
    bus1 = Bus(id="bus1", phases=phases["bus1"])
    bus2 = Bus(id="bus2", phases=phases["bus2"])
    y_shunt = np.array(y_shunt, dtype=np.complex128) if y_shunt is not None else None
    ground = Ground("gnd")
    lp = LineParameters(id="lp", z_line=np.array(z_line, dtype=complex), y_shunt=y_shunt)
    line = Line(
        id="line",
        bus1=bus1,
        bus2=bus2,
        phases=phases["line"],
        length=len_line,
        parameters=lp,
        ground=ground if lp.with_shunt else None,
    )
    bus1._res_potentials = np.array(bus_pot[0], dtype=complex)
    bus2._res_potentials = np.array(bus_pot[1], dtype=complex)
    line._res_currents = np.array(line_cur[0], dtype=complex), np.array(line_cur[1], dtype=complex)
    line._res_potentials = (
        bus1._res_potentials[[bus1.phases.index(p) for p in line.phases1]],
        bus2._res_potentials[[bus2.phases.index(p) for p in line.phases2]],
    )
    ground._res_potential = ground_pot
    if lp.with_shunt:
        line._res_ground_potential = ground._res_potential
    res_powers1, res_powers2 = (x.m for x in line.res_powers)
    series_losses = line.res_series_power_losses.m
    shunt_losses = line.res_shunt_power_losses.m
    line_losses = line.res_power_losses.m
    exp_p1, exp_p2, exp_pl_series = expected_pow
    np.testing.assert_allclose(res_powers1, exp_p1)
    np.testing.assert_allclose(res_powers2, exp_p2)
    np.testing.assert_allclose(series_losses, exp_pl_series)
    if y_shunt is None:
        assert np.allclose(shunt_losses, 0)
    else:
        assert not np.allclose(shunt_losses, 0)
    np.testing.assert_allclose(line_losses, series_losses + shunt_losses)
    if line.with_shunt:
        np.testing.assert_allclose(line.res_ground_potential, ground.res_potential)
    else:
        with pytest.raises(RoseauLoadFlowException) as e:
            _ = line.res_ground_potential
        assert e.value.msg == (
            "Ground potential is only available for lines with shunt components. Line 'line' does "
            "not have shunt components."
        )
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LINE_TYPE

    # Sanity check: the total power lost is equal to the sum of the powers flowing through
    np.testing.assert_allclose(res_powers1 + res_powers2, line_losses, rtol=1e-6)

    # Check currents (Kirchhoff's law at each end of the line)
    i1_line, i2_line = (x.m for x in line.res_currents)
    i_series = line.res_series_currents.m
    i1_shunt, i2_shunt = (x.m for x in line.res_shunt_currents)
    np.testing.assert_allclose(i1_line, i_series + i1_shunt, rtol=1e-6)
    np.testing.assert_allclose(i2_line + i_series, i2_shunt, atol=1e-4)
