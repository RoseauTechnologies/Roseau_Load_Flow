import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, CurrentLoad, FlexibleParameter, ImpedanceLoad, PowerLoad, Projection
from roseau.load_flow.sym import PositiveSequence
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow.units import Q_


def test_loads():
    bus = Bus(id="bus", phases="abcn")
    # Bad number of phases
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="pl1", bus=bus, phases="abcn", powers=[100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="pl2", bus=bus, phases="abcn", powers=[100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="pl3", bus=bus, phases="abc", powers=[100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="pl4", bus=bus, phases="abc", powers=[100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id="cl1", bus=bus, phases="abcn", currents=[100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id="cl2", bus=bus, phases="abcn", currents=[100, 100, 100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id="cl3", bus=bus, phases="abc", currents=[100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad(id="cl4", bus=bus, phases="abc", currents=[100, 100, 100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad(id="il1", bus=bus, phases="abcn", impedances=[100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad(id="il2", bus=bus, phases="abcn", impedances=[100, 100, 100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad(id="il3", bus=bus, phases="abc", impedances=[100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad(id="il4", bus=bus, phases="abc", impedances=[100, 100, 100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    fp = [FlexibleParameter.constant()] * 3
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl1", bus=bus, phases="abcn", powers=[100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    fp = [FlexibleParameter.constant()] * 3
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl2", bus=bus, phases="abcn", powers=[100, 100, 100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    fp = [FlexibleParameter.constant()] * 2
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl3", bus=bus, phases="abcn", powers=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    fp = [FlexibleParameter.constant()] * 4
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl4", bus=bus, phases="abcn", powers=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE

    # Bad impedance
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad(id="il5", bus=bus, phases="abcn", impedances=[100, 100, 0.0])
    assert "An impedance of the load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad(id="il6", bus=bus, phases="abc", impedances=[100, 100, 0.0])
    assert "An impedance of the load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    # Update
    loads = [
        PowerLoad(id="pl5", bus=bus, phases="abcn", powers=[100, 100, 100]),
        PowerLoad(id="pl6", bus=bus, phases="abc", powers=[100, 100, 100]),
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
        CurrentLoad(id="cl5", bus=bus, phases="abcn", currents=[100, 100, 100]),
        CurrentLoad(id="cl6", bus=bus, phases="abc", currents=[100, 100, 100]),
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
        ImpedanceLoad(id="il7", bus=bus, phases="abcn", impedances=[100, 100, 100]),
        ImpedanceLoad(id="il8", bus=bus, phases="abc", impedances=[100, 100, 100]),
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
    bus = Bus(id="bus", phases="abcn")
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
        PowerLoad(id="fl1", bus=bus, powers=[300 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl2", bus=bus, powers=[10 + 250j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The reactive power is greater than the parameter q_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl3", bus=bus, powers=[10 - 250j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The reactive power is lower than the parameter q_min for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl4", bus=bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_p_cons, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl5", bus=bus, powers=[-100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Same mistakes with the powers setter
    fp = [fp_pq_prod, fp_const, fp_const]
    load = PowerLoad(id="fl6", bus=bus, powers=[-200 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [300 + 50j, 0, 0j]
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    load = PowerLoad(id="fl7", bus=bus, powers=[-100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [100 + 50j, 0, 0j]
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_p_cons, fp_const, fp_const]
    load = PowerLoad(id="fl8", bus=bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [-100 + 50j, 0, 0j]
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Good load
    fp = [fp_pq_cons, fp_const, fp_const]
    load = PowerLoad(id="fl9", bus=bus, powers=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert load.flexible_params == [fp_pq_cons, fp_const, fp_const]
    assert load._res_flexible_powers is None  # load flow not run yet
    load._res_flexible_powers = np.array([100, 100, 100], dtype=complex)
    assert np.allclose(load.res_flexible_powers.m_as("VA"), [100, 100, 100])


def test_loads_to_dict():
    bus = Bus(id="bus", phases="abcn")
    values = [1 + 2j, 3 + 4j, 5 + 6j]

    # Power load
    assert_json_close(
        PowerLoad(id="load_s1", bus=bus, phases="abcn", powers=values).to_dict(include_results=False),
        {
            "id": "load_s1",
            "bus": "bus",
            "phases": "abcn",
            "type": "power",
            "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )
    assert_json_close(
        PowerLoad(id="load_s2", bus=bus, phases="abc", powers=values).to_dict(include_results=False),
        {
            "id": "load_s2",
            "bus": "bus",
            "phases": "abc",
            "type": "power",
            "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )

    # Current load
    assert_json_close(
        CurrentLoad(id="load_i1", bus=bus, phases="abcn", currents=values).to_dict(include_results=False),
        {
            "id": "load_i1",
            "bus": "bus",
            "phases": "abcn",
            "type": "current",
            "currents": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )
    assert_json_close(
        CurrentLoad(id="load_i2", bus=bus, phases="abc", currents=values).to_dict(include_results=False),
        {
            "id": "load_i2",
            "bus": "bus",
            "phases": "abc",
            "type": "current",
            "currents": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )

    # Impedance load
    assert_json_close(
        ImpedanceLoad(id="load_z1", bus=bus, phases="abcn", impedances=values).to_dict(include_results=False),
        {
            "id": "load_z1",
            "bus": "bus",
            "phases": "abcn",
            "type": "impedance",
            "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )
    assert_json_close(
        ImpedanceLoad(id="load_z2", bus=bus, phases="abc", impedances=values).to_dict(include_results=False),
        {
            "id": "load_z2",
            "bus": "bus",
            "phases": "abc",
            "type": "impedance",
            "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )
    assert_json_close(
        ImpedanceLoad(id="load_z3", bus=bus, phases="abc", impedances=values, connect_neutral=False).to_dict(
            include_results=False
        ),
        {
            "id": "load_z3",
            "bus": "bus",
            "phases": "abc",
            "type": "impedance",
            "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": False,
        },
    )
    assert_json_close(
        ImpedanceLoad(id="load_z4", bus=bus, phases="abcn", impedances=values, connect_neutral=True).to_dict(
            include_results=False
        ),
        {
            "id": "load_z4",
            "bus": "bus",
            "phases": "abcn",
            "type": "impedance",
            "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": True,
        },
    )
    with pytest.warns(UserWarning, match=r"Neutral connection requested for load 'load_z5' with no neutral phase"):
        vs = ImpedanceLoad(id="load_z5", bus=bus, phases="abc", impedances=values, connect_neutral=True)
    assert_json_close(
        vs.to_dict(include_results=False),
        {
            "id": "load_z5",
            "bus": "bus",
            "phases": "abc",
            "type": "impedance",
            "impedances": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            "connect_neutral": None,
        },
    )

    # Flexible load
    expected_dict = {
        "id": "load_f1",
        "bus": "bus",
        "phases": "abcn",
        "type": "power",
        "powers": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
        "connect_neutral": None,
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
    flex_load = PowerLoad(id="load_f1", bus=bus, phases="abcn", powers=values, flexible_params=fp)
    assert flex_load.flexible_params is not None
    assert_json_close(flex_load.to_dict(include_results=False), expected_dict)
    parsed_flex_load = PowerLoad.from_dict(expected_dict | {"bus": Bus(id="bus", phases="abcn")})
    assert isinstance(parsed_flex_load, PowerLoad)
    assert parsed_flex_load.id == flex_load.id
    assert parsed_flex_load.bus.id == flex_load.bus.id
    assert parsed_flex_load.phases == flex_load.phases
    assert np.allclose(parsed_flex_load.powers.m, flex_load.powers.m)
    assert parsed_flex_load.flexible_params is not None
    assert [p.to_dict(include_results=False) for p in parsed_flex_load.flexible_params] == [
        p.to_dict(include_results=False) for p in flex_load.flexible_params
    ]


def test_loads_units():
    bus = Bus(id="bus", phases="abcn")

    # Good unit constructor
    load = PowerLoad(id="pl1", bus=bus, powers=Q_([1, 1, 1], "kVA"), phases="abcn")
    assert np.allclose(load._powers, [1000, 1000, 1000])

    # Good unit setter
    load = PowerLoad(id="pl2", bus=bus, powers=[100, 100, 100], phases="abcn")
    assert np.allclose(load._powers, [100, 100, 100])
    load.powers = Q_([1, 1, 1], "kVA")
    assert np.allclose(load._powers, [1000, 1000, 1000])

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'VA'"):
        PowerLoad(id="pl3", bus=bus, powers=Q_([100, 100, 100], "A"), phases="abcn")

    # Bad unit setter
    load = PowerLoad(id="pl4", bus=bus, powers=[100, 100, 100], phases="abcn")
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
    bus = Bus(id="bus", phases=bus_ph)
    load = PowerLoad(id="load", bus=bus, powers=s, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=complex)
    load._res_currents = np.array(res_cur, dtype=complex)
    load._res_potentials = np.array([bus._res_potentials[bus.phases.index(p)] for p in load_ph], dtype=complex)
    assert np.allclose(sum(load.res_powers.m), sum(load.powers.m))


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
    bus = Bus(id="bus", phases=bus_ph)
    load = CurrentLoad(id="load", bus=bus, currents=i, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=complex)
    load._res_currents = np.array(res_cur, dtype=complex)
    load._res_potentials = np.array([bus._res_potentials[bus.phases.index(p)] for p in load_ph], dtype=complex)
    load_powers = load.res_voltages.m * load.currents.m.conj()  # S = V * I*
    assert np.allclose(sum(load.res_powers.m), sum(load_powers))


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
    bus = Bus(id="bus", phases=bus_ph)
    load = ImpedanceLoad(id="load", bus=bus, impedances=z, phases=load_ph)
    bus._res_potentials = np.array(res_pot, dtype=complex)
    load._res_currents = np.array(res_cur, dtype=complex)
    load._res_potentials = np.array([bus._res_potentials[bus.phases.index(p)] for p in load_ph], dtype=complex)
    load_powers = np.abs(load.res_voltages.m) ** 2 / load.impedances.m.conj()  # S = |V|² / Z*
    assert np.allclose(sum(load.res_powers.m), sum(load_powers))


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
    load._res_potentials = np.array([bus._res_potentials[bus.phases.index(p)] for p in load_ph], dtype=complex)

    assert bus.voltage_phases == bus_vph
    assert len(bus.res_voltages.m) == len(bus.voltage_phases)

    assert load.voltage_phases == load_vph
    assert len(load.res_voltages.m) == len(load.voltage_phases)


def test_non_flexible_load_res_flexible_powers():
    bus = Bus(id="bus", phases="an")
    load = PowerLoad(id="load", bus=bus, powers=[2300], phases="an")
    bus._res_potentials = np.array([230, 0], dtype=complex)
    load._res_currents = np.array([10, -10], dtype=complex)
    load._res_potentials = np.array([bus._res_potentials[bus.phases.index(p)] for p in load.phases], dtype=complex)
    with pytest.raises(RoseauLoadFlowException) as e:
        _ = load.res_flexible_powers
    assert e.value.msg == "The load 'load' is not flexible and does not have flexible powers"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE


def test_loads_scalar_values():
    bus = Bus(id="bus", phases="abcn")

    # Power load
    load = PowerLoad(id="load1", bus=bus, powers=100 + 50j, phases="abcn")
    np.testing.assert_allclose(load.powers.m, [100 + 50j, 100 + 50j, 100 + 50j], strict=True)
    load.powers = 200 + 100j
    np.testing.assert_allclose(load.powers.m, [200 + 100j, 200 + 100j, 200 + 100j], strict=True)
    load = PowerLoad(id="load2", bus=bus, powers=100 + 50j, phases="abc")
    np.testing.assert_allclose(load.powers.m, [100 + 50j, 100 + 50j, 100 + 50j], strict=True)
    load = PowerLoad(id="load3", bus=bus, powers=100 + 50j, phases="bcn")
    np.testing.assert_allclose(load.powers.m, [100 + 50j, 100 + 50j], strict=True)
    load = PowerLoad(id="load4", bus=bus, powers=100 + 50j, phases="ca")
    np.testing.assert_allclose(load.powers.m, [100 + 50j], strict=True)
    load = PowerLoad(id="load5", bus=bus, powers=100 + 50j, phases="an")
    np.testing.assert_allclose(load.powers.m, [100 + 50j], strict=True)

    # Current load
    load = CurrentLoad(id="load6", bus=bus, currents=2 + 1j, phases="abcn")
    np.testing.assert_allclose(load.currents.m, [2 + 1j, 2 + 1j, 2 + 1j], strict=True)
    load.currents = 4 + 2j
    np.testing.assert_allclose(load.currents.m, [4 + 2j, 4 + 2j, 4 + 2j], strict=True)
    load = CurrentLoad(id="load7", bus=bus, currents=2 + 1j, phases="abc")
    np.testing.assert_allclose(load.currents.m, [2 + 1j, 2 + 1j, 2 + 1j], strict=True)
    load = CurrentLoad(id="load8", bus=bus, currents=2 + 1j, phases="bcn")
    np.testing.assert_allclose(load.currents.m, [2 + 1j, 2 + 1j], strict=True)
    load = CurrentLoad(id="load9", bus=bus, currents=2 + 1j, phases="ca")
    np.testing.assert_allclose(load.currents.m, [2 + 1j], strict=True)
    load = CurrentLoad(id="load10", bus=bus, currents=2 + 1j, phases="an")
    np.testing.assert_allclose(load.currents.m, [2 + 1j], strict=True)

    # Impedance load
    load = ImpedanceLoad(id="load11", bus=bus, impedances=1000 + 500j, phases="abcn")
    np.testing.assert_allclose(load.impedances.m, [1000 + 500j, 1000 + 500j, 1000 + 500j], strict=True)
    load.impedances = 2000 + 1000j
    np.testing.assert_allclose(load.impedances.m, [2000 + 1000j, 2000 + 1000j, 2000 + 1000j], strict=True)


def test_res_unbalance():
    bus = Bus(id="b1", phases="abcn")
    load = PowerLoad(id="l1", bus=bus, powers=[100 + 50j, 0, 0j], phases="abc")

    va, vb, vc = 230 * PositiveSequence
    ia, ib, ic = 1 * PositiveSequence

    # Balanced load
    load._res_potentials = np.array([va, vb, vc])
    load._res_currents = np.array([ia, ib, ic])
    assert np.isclose(load.res_current_unbalance().m, 0)

    # Unbalanced load
    load._res_potentials = np.array([va, vb, vc])
    load._res_currents = np.array([ia, ib, (ic + ib) / 2])
    assert np.isclose(load.res_current_unbalance().m, 37.7964473)

    # With neutral
    load = PowerLoad(id="l2", bus=bus, powers=[100 + 50j, 0, 0j], phases="abcn")
    load._res_potentials = np.array([va, vb, vc, 0])
    load._res_currents = np.array([ia, ib, ic, 0])
    assert np.isclose(load.res_current_unbalance().m, 0)
    load._res_potentials = np.array([va, vb, vc, 0])
    load._res_currents = np.array([ia, ib, ib, ia + ib + ib])
    assert np.isclose(load.res_current_unbalance().m, 100)

    # Non 3-phase bus
    load = PowerLoad(id="l3", bus=bus, powers=[100 + 50j], phases="ab")
    load._res_potentials = np.array([va, vb])
    load._res_currents = np.array([ia, ib])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.res_current_unbalance()
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PHASE
    assert e.value.msg == "Current unbalance is only available for three-phase elements, load 'l3' has phases 'ab'."
