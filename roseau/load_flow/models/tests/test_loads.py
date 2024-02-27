import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow import Projection
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, CurrentLoad, FlexibleParameter, ImpedanceLoad, PowerLoad
from roseau.load_flow.units import Q_


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

    fp = [FlexibleParameter.constant()] * 3
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", powers=[100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    fp = [FlexibleParameter.constant()] * 3
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    fp = [FlexibleParameter.constant()] * 2
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", powers=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    fp = [FlexibleParameter.constant()] * 4
    with pytest.raises(RoseauLoadFlowException) as e:
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

    # Short-circuit
    bus = Bus(id="bus", phases="abcn")
    bus.add_short_circuit("a", "b")
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="load", bus=bus, powers=[10, 10, 10])
    assert "that already has a short-circuit. It makes the short-circuit calculation impossible." in e.value.msg
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_SHORT_CIRCUIT


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
        q_min=-200,
        q_max=200,
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
        q_min=-200,
        q_max=200,
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
        PowerLoad("flexible load", bus, powers=[10 + 250j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The reactive power is greater than the parameter q_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[10 - 250j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The reactive power is lesser than the parameter q_min for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_p_cons, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, powers=[-100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Same mistakes with the powers setter
    fp = [fp_pq_prod, fp_const, fp_const]
    load = PowerLoad("flexible load", bus, powers=[-200 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [300 + 50j, 0, 0j]
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    load = PowerLoad("flexible load", bus, powers=[-100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [100 + 50j, 0, 0j]
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_p_cons, fp_const, fp_const]
    load = PowerLoad("flexible load", bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [-100 + 50j, 0, 0j]
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Good load
    fp = [fp_pq_cons, fp_const, fp_const]
    load = PowerLoad("flexible load", bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert load.flexible_params == [fp_pq_cons, fp_const, fp_const]
    assert load._res_flexible_powers is None  # load flow not run yet
    load._res_flexible_powers = np.array([100, 100, 100], dtype=complex)
    assert np.allclose(load.res_flexible_powers.m_as("VA"), [100, 100, 100])


def test_loads_to_dict():
    bus = Bus("bus", phases="abcn")
    values = [1 + 2j, 3 + 4j, 5 + 6j]

    # Power load
    assert PowerLoad("load_s1", bus, phases="abcn", powers=values).to_dict(include_results=False) == {
        "id": "load_s1",
        "bus": "bus",
        "phases": "abcn",
        "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }
    assert PowerLoad("load_s2", bus, phases="abc", powers=values).to_dict(include_results=False) == {
        "id": "load_s2",
        "bus": "bus",
        "phases": "abc",
        "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }

    # Current load
    assert CurrentLoad("load_i1", bus, phases="abcn", currents=values).to_dict(include_results=False) == {
        "id": "load_i1",
        "bus": "bus",
        "phases": "abcn",
        "currents": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }
    assert CurrentLoad("load_i2", bus, phases="abc", currents=values).to_dict(include_results=False) == {
        "id": "load_i2",
        "bus": "bus",
        "phases": "abc",
        "currents": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }

    # Impedance load
    assert ImpedanceLoad("load_z1", bus, phases="abcn", impedances=values).to_dict(include_results=False) == {
        "id": "load_z1",
        "bus": "bus",
        "phases": "abcn",
        "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
    }
    assert ImpedanceLoad("load_z2", bus, phases="abc", impedances=values).to_dict(include_results=False) == {
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
                "projection": {
                    "type": "euclidean",
                    "alpha": Projection._DEFAULT_ALPHA,
                    "epsilon": Projection._DEFAULT_EPSILON,
                },
                "s_max": 1.0,
            },
        ]
        * 3,
    }
    fp = [FlexibleParameter.constant()] * 3
    flex_load = PowerLoad("load_f1", bus, phases="abcn", powers=values, flexible_params=fp)
    assert flex_load.to_dict(include_results=False) == expected_dict
    parsed_flex_load = PowerLoad.from_dict(expected_dict | {"bus": bus})
    assert isinstance(parsed_flex_load, PowerLoad)
    assert parsed_flex_load.id == flex_load.id
    assert parsed_flex_load.bus.id == flex_load.bus.id
    assert parsed_flex_load.phases == flex_load.phases
    assert np.allclose(parsed_flex_load.powers, flex_load.powers)
    assert [p.to_dict(include_results=False) for p in parsed_flex_load.flexible_params] == [
        p.to_dict(include_results=False) for p in flex_load.flexible_params
    ]


def test_loads_units():
    bus = Bus("bus", phases="abcn")

    # Good unit constructor
    load = PowerLoad("load", bus, powers=Q_([1, 1, 1], "kVA"), phases="abcn")
    assert np.allclose(load._powers, [1000, 1000, 1000])

    # Good unit setter
    load = PowerLoad("load", bus, powers=[100, 100, 100], phases="abcn")
    assert np.allclose(load._powers, [100, 100, 100])
    load.powers = Q_([1, 1, 1], "kVA")
    assert np.allclose(load._powers, [1000, 1000, 1000])

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
            [229.56453031 - 1.70412303e-23j, -114.78226516 - 1.98934385e02j, -114.78226516 + 1.98934385e02j],
            [0.43546969 + 0.0j, -0.21773484 - 0.25145831j, -0.21773484 + 0.25145831j],
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
        pytest.param(
            "bcn",
            "cn",
            [100],
            [-115.0 - 199.18584287j, -114.78178053 + 198.80787565j, -0.21821947 + 0.37796722j],
            [-0.21821947 + 0.37796722j, 0.21821947 - 0.37796722j],
            id="bcn,cn",
        ),
    ),
)
def test_power_load_res_powers(bus_ph, load_ph, s, res_pot, res_cur):
    bus = Bus("bus", phases=bus_ph)
    load = PowerLoad("load", bus, powers=s, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=complex)
    load._res_currents = np.array(res_cur, dtype=complex)
    assert np.allclose(sum(load.res_powers), sum(load.powers))


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
    bus._res_potentials = np.array(res_pot, dtype=complex)
    load._res_currents = np.array(res_cur, dtype=complex)
    load_powers = load.res_voltages * load.currents.conj()  # S = V * I*
    assert np.allclose(sum(load.res_powers), sum(load_powers))


@pytest.mark.parametrize(
    ("bus_ph", "load_ph", "z", "res_pot", "res_cur"),
    (
        pytest.param(
            "abcn",
            "abcn",
            [1000, 500j, 1000],
            [
                229.76994582 + 4.26340012e-04j,
                -114.60031752 - 1.99414475e02j,
                -114.88539883 + 1.98987282e02j,
                -0.28422948 + 4.26766352e-01j,
            ],
            [
                0.23005418 - 4.26340012e-04j,
                -0.39968248 + 2.28632176e-01j,
                -0.11460117 + 1.98560516e-01j,
                0.28422948 - 4.26766352e-01j,
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
            [1000, 500j, 1000],
            [
                229.31206381 - 2.70509524e-20j,
                -113.86089233 - 1.98983679e02j,
                -115.45117148 + 1.98983679e02j,
                0.0 + 0.0j,
            ],
            [0.68793619 + 0.0j, -1.13910767 - 0.20216424j, 0.45117148 + 0.20216424j],
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
            [229.31206381 - 2.70509524e-20j, -113.86089233 - 1.98983679e02j, -115.45117148 + 1.98983679e02j],
            [0.68793619 + 0.0j, -1.13910767 - 0.20216424j, 0.45117148 + 0.20216424j],
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
    bus._res_potentials = np.array(res_pot, dtype=complex)
    load._res_currents = np.array(res_cur, dtype=complex)
    load_powers = np.abs(load.res_voltages) ** 2 / load.impedances.conj()  # S = |V|² / Z*
    assert np.allclose(sum(load.res_powers), sum(load_powers))


@pytest.mark.parametrize(
    ("bus_ph", "load_ph", "bus_vph", "load_vph"),
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
def test_load_voltages(bus_ph, load_ph, bus_vph, load_vph):
    bus = Bus("bus", phases=bus_ph)
    powers = [100, 200, 300]
    load = PowerLoad("load", bus, powers=powers[: len(load_vph)], phases=load_ph)

    res_pot = [230 + 0j, 230 * np.exp(1j * 2 * np.pi / 3), 230 * np.exp(1j * 4 * np.pi / 3), 0j]
    bus._res_potentials = np.array(res_pot[: len(bus_ph)], dtype=complex)

    res_cur = [0.1 + 0j, 0.2 + 0j, 0.3 + 0j, 0.6 + 0j]
    load._res_currents = np.array(res_cur[: len(load_ph)], dtype=complex)

    assert bus.voltage_phases == bus_vph
    assert len(bus.res_voltages) == len(bus.voltage_phases)

    assert load.voltage_phases == load_vph
    assert len(load.res_voltages) == len(load.voltage_phases)
