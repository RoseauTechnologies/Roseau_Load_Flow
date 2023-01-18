import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, CurrentLoad, FlexibleParameter, ImpedanceLoad, PowerLoad
from roseau.load_flow.utils import Q_


def test_loads():
    bus = Bus("bus", phases="abcn")
    # Bad number of phases
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", powers=[100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abc", powers=[100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abc", powers=[100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abcn", currents=[100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abcn", currents=[100, 100, 100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abc", currents=[100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abc", currents=[100, 100, 100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abcn", impedances=[100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abcn", impedances=[100, 100, 100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abc", impedances=[100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abc", impedances=[100, 100, 100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 3
        PowerLoad("load", bus, phases="abcn", powers=[100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 3
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 2
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 4
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE

    # Bad impedance
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abcn", impedances=[100, 100, 0.0])
    assert "An impedance of the load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abc", impedances=[100, 100, 0.0])
    assert "An impedance of the load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    # Update
    loads = [
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100]),
        PowerLoad("load", bus, phases="abc", powers=[100, 100, 100]),
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.powers = [100, 100]
        assert "Incorrect number of powers" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.powers = [100, 100, 100, 100]
        assert "Incorrect number of powers" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    loads = [
        CurrentLoad("load", bus, phases="abcn", currents=[100, 100, 100]),
        CurrentLoad("load", bus, phases="abc", currents=[100, 100, 100]),
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.currents = [100, 100]
        assert "Incorrect number of currents" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.currents = [100, 100, 100, 100]
        assert "Incorrect number of currents" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    loads = [
        ImpedanceLoad("load", bus, phases="abcn", impedances=[100, 100, 100]),
        ImpedanceLoad("load", bus, phases="abc", impedances=[100, 100, 100]),
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.impedances = [100, 100]
        assert "Incorrect number of impedances" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.impedances = [100, 100, 100, 100]
        assert "Incorrect number of impedances" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.impedances = [100, 100, 0.0]
        assert "An impedance of the load" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE


def test_flexible_load():
    bus = Bus("bus", phases="abcn")
    fp_pq_prod = FlexibleParameter.pq_u_production(
        up_up=250,
        up_max=260,
        uq_min=210,
        uq_down=220,
        uq_up=240,
        uq_max=250,
        s_max=300,
        alpha_control=100.0,
        alpha_proj=100.0,
        epsilon_proj=0.01,
    )
    fp_pq_cons = FlexibleParameter.pq_u_consumption(
        up_min=200,
        up_down=210,
        uq_min=210,
        uq_down=220,
        uq_up=240,
        uq_max=250,
        s_max=300,
        alpha_control=100.0,
        alpha_proj=100.0,
        epsilon_proj=0.01,
    )
    fp_p_cons = FlexibleParameter.p_max_u_consumption(
        u_min=210, u_down=220, s_max=300, alpha_control=100.0, alpha_proj=100.0, epsilon_proj=0.01
    )
    fp_const = FlexibleParameter.constant()

    # Bad loads
    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[300 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[0, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a P control but a null active power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_p_cons, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[-100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Good load
    fp = [fp_pq_cons, fp_const, fp_const]
    load = PowerLoad("flexible load", bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert load.flexible_params == [fp_pq_cons, fp_const, fp_const]
    assert load._res_flexible_powers is None  # load flow not run yet
    load._res_flexible_powers = np.array([100, 100, 100], dtype=complex)
    assert np.allclose(load.res_flexible_powers, [100, 100, 100])


def test_loads_to_dict():
    bus = Bus("bus", phases="abcn")
    values = [1 + 2j, 3 + 4j, 5 + 6j]

    # Power load
    assert PowerLoad("load_s1", bus, phases="abcn", powers=values).to_dict() == {
        "id": "load_s1",
        "bus": "bus",
        "phases": "abcn",
        "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }
    assert PowerLoad("load_s2", bus, phases="abc", powers=values).to_dict() == {
        "id": "load_s2",
        "bus": "bus",
        "phases": "abc",
        "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }

    # Current load
    assert CurrentLoad("load_i1", bus, phases="abcn", currents=values).to_dict() == {
        "id": "load_i1",
        "bus": "bus",
        "phases": "abcn",
        "currents": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }
    assert CurrentLoad("load_i2", bus, phases="abc", currents=values).to_dict() == {
        "id": "load_i2",
        "bus": "bus",
        "phases": "abc",
        "currents": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }

    # Impedance load
    assert ImpedanceLoad("load_z1", bus, phases="abcn", impedances=values).to_dict() == {
        "id": "load_z1",
        "bus": "bus",
        "phases": "abcn",
        "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }
    assert ImpedanceLoad("load_z2", bus, phases="abc", impedances=values).to_dict() == {
        "id": "load_z2",
        "bus": "bus",
        "phases": "abc",
        "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }

    # Flexible load
    expected_dict = {
        "id": "load_f1",
        "bus": "bus",
        "phases": "abcn",
        "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
        "flexible_params": [
            {
                "control_p": {"type": "constant"},
                "control_q": {"type": "constant"},
                "projection": {"type": "euclidean", "alpha": 100.0, "epsilon": 0.01},
                "s_max": 1.0,
            },
        ]
        * 3,
    }
    fp = [FlexibleParameter.constant()] * 3
    flex_load = PowerLoad("load_f1", bus, phases="abcn", powers=values, flexible_params=fp)
    assert flex_load.to_dict() == expected_dict
    parsed_flex_load = PowerLoad.from_dict(expected_dict | {"bus": bus})
    assert isinstance(parsed_flex_load, PowerLoad)
    assert parsed_flex_load.id == flex_load.id
    assert parsed_flex_load.bus.id == flex_load.bus.id
    assert parsed_flex_load.phases == flex_load.phases
    assert np.allclose(parsed_flex_load.powers, flex_load.powers)
    assert [p.to_dict() for p in parsed_flex_load.flexible_params] == [p.to_dict() for p in flex_load.flexible_params]


def test_loads_units():
    bus = Bus("bus", phases="abcn")

    # Good unit constructor
    load = PowerLoad("load", bus, powers=Q_([1, 1, 1], "kVA"), phases="abcn")
    assert np.allclose(load.powers, [1000, 1000, 1000])

    # Good unit setter
    load = PowerLoad("load", bus, powers=[100, 100, 100], phases="abcn")
    assert np.allclose(load.powers, [100, 100, 100])
    load.powers = Q_([1, 1, 1], "kVA")
    assert np.allclose(load.powers, [1000, 1000, 1000])

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'VA'"):
        PowerLoad("load", bus, powers=Q_([100, 100, 100], "A"), phases="abcn")

    # Bad unit setter
    load = PowerLoad("load", bus, powers=[100, 100, 100], phases="abcn")
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'VA'"):
        load.powers = Q_([100, 100, 100], "A")


@pytest.mark.parametrize(
    ("bus_ph", "load_ph", "s", "res_pot", "res_cur"),
    (
        pytest.param(
            "abcn",
            "abcn",
            [100, 50, 100],
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
            [100],
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
            [100, 50],
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
            [100, 50, 100],
            [
                229.78226585 - 1.25629783e-01j,
                -114.78233441 - 1.98934583e02j,
                -114.99993144 + 1.99060213e02j,
                0.0 + 0.0000j,
            ],
            [-1.52803999e228 + 0.12562986j, -2.17665984e-001 - 0.2512596j, 1.52803999e228 + 0.12562975j],
            id="abcn,abc",
        ),
        pytest.param(
            "abcn",
            "ab",
            [100],
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
            [100, 50, 100],
            [229.78226585 - 1.25629783e-01j, -114.78233441 - 1.98934583e02j, -114.99993144 + 1.99060213e02j],
            [2.17734670e-01 + 0.12562986j, -2.17665984e-01 - 0.2512596j, -6.86859745e-05 + 0.12562975j],
            id="abc,abc",
        ),
        pytest.param(
            "abc",
            "ab",
            [100],
            [229.78233438 - 1.25669301e-01j, -114.78233438 - 1.99060174e02j, -115.0 + 1.99185843e02j],
            [0.21766596 + 0.1256695j, -0.21766596 - 0.1256695j],
            id="abc,ab",
        ),
        # pytest.param(  # TODO: this causes Segmentation fault, re-visit when fixed
        #     "bcn",
        #     "cn",
        #     [100],
        #     [
        #         ...
        #     ],
        #     [
        #         ...
        #     ],
        #     id="bcn,cn",
        # ),
    ),
)
def test_power_load_res_powers(bus_ph, load_ph, s, res_pot, res_cur):
    bus = Bus("bus", phases=bus_ph)
    load = PowerLoad("load", bus, powers=s, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=np.complex_)
    load._res_currents = np.array(res_cur, dtype=np.complex_)
    assert np.allclose(load.res_powers, load.powers)


@pytest.mark.parametrize(
    ("bus_ph", "load_ph", "i", "res_pot", "res_cur"),
    (
        pytest.param(
            "abcn",
            "abcn",
            [1, 0.5, 1],
            [229.0 + 0.0j, -115.5 - 199.18584287j, -116.0 + 199.18584287j, 2.5 + 0.0j],
            [1.0 + 0.0j, 0.5 + 0.0j, 1.0 + 0.0j, -2.5 + 0.0j],
            id="abcn,abcn",
        ),
        pytest.param(
            "abcn",
            "bn",
            [1],
            [230.0 + 0.0j, -116.0 - 199.18584287j, -115.0 + 199.18584287j, 1.0 + 0.0j],
            [1.0 + 0.0j, -1.0 + 0.0j],
            id="abcn,bn",
        ),
        pytest.param(
            "abcn",
            "abn",
            [1, 0.5],
            [229.0 + 0.0j, -115.5 - 199.18584287j, -115.0 + 199.18584287j, 1.5 + 0.0j],
            [1.0 + 0.0j, 0.5 + 0.0j, -1.5 + 0.0j],
            id="abcn,abn",
        ),
        pytest.param(
            "abcn",
            "abc",
            [1, 0.5, 1],
            [230.0 + 0.0j, -114.5 - 199.18584287j, -115.5 + 199.18584287j, 0.0 + 0.0j],
            [0.0 + 0.0j, -0.5 + 0.0j, 0.5 + 0.0j],
            id="abcn,abc",
        ),
        pytest.param(
            "abcn",
            "ab",
            [1],
            [229.0 + 0.0j, -114.0 - 199.18584287j, -115.0 + 199.18584287j, 0.0 + 0.0j],
            [1.0 + 0.0j, -1.0 + 0.0j],
            id="abcn,ab",
        ),
        pytest.param(
            "abc",
            "abc",
            [1, 0.5, 1],
            [230.0 + 0.0j, -114.5 - 199.18584287j, -115.5 + 199.18584287j],
            [0.0 + 0.0j, -0.5 + 0.0j, 0.5 + 0.0j],
            id="abc,abc",
        ),
        pytest.param(
            "abc",
            "ab",
            [1],
            [229.0 + 0.0j, -114.0 - 199.18584287j, -115.0 + 199.18584287j],
            [1.0 + 0.0j, -1.0 + 0.0j],
            id="abc,ab",
        ),
    ),
)
def test_current_load_res_powers(bus_ph, load_ph, i, res_pot, res_cur):
    bus = Bus("bus", phases=bus_ph)
    load = CurrentLoad("load", bus, currents=i, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=np.complex_)
    load._res_currents = np.array(res_cur, dtype=np.complex_)
    currents = (load.res_powers / load.res_voltages).conj()  # I = (S / V)*
    assert np.allclose(currents, load.currents)


@pytest.mark.parametrize(
    ("bus_ph", "load_ph", "z", "res_pot", "res_cur"),
    (
        pytest.param(
            "abcn",
            "abcn",
            [1000, 500, 1000],
            [
                2.29770116e02 - 1.97602061e-04j,
                -1.14770687e02 - 1.98788661e02j,
                -1.14885229e02 + 1.98986658e02j,
                -1.14199689e-01 - 1.97799663e-01j,
            ],
            [
                0.22988432 + 1.97602061e-04j,
                -0.22931297 - 3.97181723e-01j,
                -0.11477103 + 1.99184458e-01j,
                0.11419969 + 1.97799663e-01j,
            ],
            id="abcn,abcn",
        ),
        pytest.param(
            "abcn",
            "bn",
            [1000],
            [
                2.30000000e02 + 0.00000000e00j,
                -1.14885230e02 - 1.98987055e02j,
                -1.15000000e02 + 1.99185843e02j,
                -1.14770459e-01 - 1.98788266e-01j,
            ],
            [-0.11477046 - 0.19878827j, 0.11477046 + 0.19878827j],
            id="abcn,bn",
        ),
        pytest.param(
            "abcn",
            "abn",
            [1000, 500],
            [
                2.29770230e02 - 3.95993350e-04j,
                -1.14770459e02 - 1.98789058e02j,
                -1.15000000e02 + 1.99185843e02j,
                2.28626867e-04 - 3.96389343e-01j,
            ],
            [2.29770001e-01 + 3.95993350e-04j, -2.29541375e-01 - 3.96785336e-01j, -2.28626867e-04 + 3.96389343e-01j],
            id="abcn,abn",
        ),
        pytest.param(
            "abcn",
            "abc",
            [1000, 500, 1000],
            [
                229.65568794 + 1.97996675e-01j,
                -114.99931412 - 1.98392668e02j,
                -114.65637382 + 1.98194672e02j,
                0.0 + 0.00000000e00j,
            ],
            [0.34431206 - 0.19799667j, -0.00068588 - 0.79317468j, -0.34362618 + 0.99117135j],
            id="abcn,abc",
        ),
        pytest.param(
            "abcn",
            "ab",
            [1000],
            [
                229.65568862 - 1.98788266e-01j,
                -114.65568862 - 1.98987055e02j,
                -115.0 + 1.99185843e02j,
                0.0 + 0.00000000e00j,
            ],
            [0.34431138 + 0.19878827j, -0.34431138 - 0.19878827j],
            id="abcn,ab",
        ),
        pytest.param(
            "abc",
            "abc",
            [1000, 500j, 1000],
            [229.65489388 + 1.98785776e-01j, -114.20366418 - 1.99183348e02j, -115.4512297 + 1.98984562e02j],
            [0.34510612 - 0.19878578j, -0.79633582 - 0.00249513j, 0.4512297 + 0.20128091j],
            id="abc,abc",
        ),
        pytest.param(
            "abc",
            "ab",
            [1000],
            [229.65568862 - 1.98788266e-01j, -114.65568862 - 1.98987055e02j, -115.0 + 1.99185843e02j],
            [0.34431138 + 0.19878827j, -0.34431138 - 0.19878827j],
            id="abc,ab",
        ),
    ),
)
def test_impedance_load_res_powers(bus_ph, load_ph, z, res_pot, res_cur):
    bus = Bus("bus", phases=bus_ph)
    load = ImpedanceLoad("load", bus, impedances=z, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=np.complex_)
    load._res_currents = np.array(res_cur, dtype=np.complex_)
    impedances = np.abs(load.res_voltages) ** 2 / load.res_powers.conj()  # Z = |V|² / S*
    # TODO: test comparison to load.res_currents using Delta-Wye transform
    # https://en.wikipedia.org/wiki/Y-%CE%94_transform
    assert np.allclose(impedances, load.impedances)
