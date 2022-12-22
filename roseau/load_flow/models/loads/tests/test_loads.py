import pytest
from pint.errors import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, CurrentLoad, FlexibleParameter, ImpedanceLoad, PowerLoad
from roseau.load_flow.utils import Q_


def test_loads():
    bus = Bus("bus", phases="abcn")
    # Bad number of phases
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", s=[100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abcn", s=[100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abc", s=[100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", bus, phases="abc", s=[100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abcn", i=[100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abcn", i=[100, 100, 100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abc", i=[100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        CurrentLoad("load", bus, phases="abc", i=[100, 100, 100, 100])
    assert "Incorrect number of currents" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abcn", z=[100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abcn", z=[100, 100, 100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abc", z=[100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abc", z=[100, 100, 100, 100])
    assert "Incorrect number of impedances" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 3
        PowerLoad("load", bus, phases="abcn", s=[100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 3
        PowerLoad("load", bus, phases="abcn", s=[100, 100, 100, 100], flexible_params=fp)
    assert "Incorrect number of powers" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 2
        PowerLoad("load", bus, phases="abcn", s=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        fp = [FlexibleParameter.constant()] * 4
        PowerLoad("load", bus, phases="abcn", s=[100, 100, 100], flexible_params=fp)
    assert "Incorrect number of parameters" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE

    # Bad impedance
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abcn", z=[100, 100, 0.0])
    assert "An impedance of the load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", bus, phases="abc", z=[100, 100, 0.0])
    assert "An impedance of the load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    # Bad unit
    with pytest.raises(
        DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'volt_ampere'"
    ) as e:
        PowerLoad("load", bus, s=Q_([100, 100, 100], "A"), phases="abcn")

    # Update
    loads = [
        PowerLoad("load", bus, phases="abcn", s=[100, 100, 100]),
        PowerLoad("load", bus, phases="abc", s=[100, 100, 100]),
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_powers([100, 100])
        assert "Incorrect number of powers" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_powers([100, 100, 100, 100])
        assert "Incorrect number of powers" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    loads = [
        CurrentLoad("load", bus, phases="abcn", i=[100, 100, 100]),
        CurrentLoad("load", bus, phases="abc", i=[100, 100, 100]),
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_currents([100, 100])
        assert "Incorrect number of currents" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_currents([100, 100, 100, 100])
        assert "Incorrect number of currents" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    loads = [
        ImpedanceLoad("load", bus, phases="abcn", z=[100, 100, 100]),
        ImpedanceLoad("load", bus, phases="abc", z=[100, 100, 100]),
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_impedances([100, 100])
        assert "Incorrect number of impedances" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_impedances([100, 100, 100, 100])
        assert "Incorrect number of impedances" in e.value.msg
        assert e.value.code == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_impedances([100, 100, 0.0])
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
        PowerLoad("flexible load", bus, s=[300 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, s=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_pq_prod, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, s=[0, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a P control but a null active power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = [fp_p_cons, fp_const, fp_const]
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("flexible load", bus, s=[-100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Good load
    fp = [fp_pq_cons, fp_const, fp_const]
    load = PowerLoad("flexible load", bus, s=[100 + 50j, 0, 0j], phases="abcn", flexible_params=fp)
    assert load.flexible_params == [fp_pq_cons, fp_const, fp_const]
    assert load._flexible_powers is None  # cannot use load.flexible_powers because it is passing None to pint
    load.flexible_powers = [100, 100, 100]
    assert (load.flexible_powers.m_as("VA") == [100, 100, 100]).all()


def test_loads_to_dict():
    bus = Bus("bus", phases="abcn")
    values = [1 + 2j, 3 + 4j, 5 + 6j]

    # Power load
    assert PowerLoad("load_s1", bus, phases="abcn", s=values).to_dict() == {
        "id": "load_s1",
        "phases": "abcn",
        "powers": {"sa": [1.0, 2.0], "sb": [3.0, 4.0], "sc": [5.0, 6.0]},
    }
    assert PowerLoad("load_s2", bus, phases="abc", s=values).to_dict() == {
        "id": "load_s2",
        "phases": "abc",
        "powers": {"sa": [1.0, 2.0], "sb": [3.0, 4.0], "sc": [5.0, 6.0]},
    }

    # Current load
    assert CurrentLoad("load_i1", bus, phases="abcn", i=values).to_dict() == {
        "id": "load_i1",
        "phases": "abcn",
        "currents": {"ia": [1.0, 2.0], "ib": [3.0, 4.0], "ic": [5.0, 6.0]},
    }
    assert CurrentLoad("load_i2", bus, phases="abc", i=values).to_dict() == {
        "id": "load_i2",
        "phases": "abc",
        "currents": {"ia": [1.0, 2.0], "ib": [3.0, 4.0], "ic": [5.0, 6.0]},
    }

    # Impedance load
    assert ImpedanceLoad("load_z1", bus, phases="abcn", z=values).to_dict() == {
        "id": "load_z1",
        "phases": "abcn",
        "impedances": {"za": [1.0, 2.0], "zb": [3.0, 4.0], "zc": [5.0, 6.0]},
    }
    assert ImpedanceLoad("load_z2", bus, phases="abc", z=values).to_dict() == {
        "id": "load_z2",
        "phases": "abc",
        "impedances": {"za": [1.0, 2.0], "zb": [3.0, 4.0], "zc": [5.0, 6.0]},
    }

    # Flexible load
    expected_dict = {
        "id": "load_f1",
        "phases": "abcn",
        "powers": {"sa": [1.0, 2.0], "sb": [3.0, 4.0], "sc": [5.0, 6.0]},
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
    flex_load = PowerLoad("load_f1", bus, phases="abcn", s=values, flexible_params=fp)
    assert flex_load.to_dict() == expected_dict
    parsed_flex_load = PowerLoad.from_dict(expected_dict, bus)
    assert isinstance(parsed_flex_load, PowerLoad)
    assert parsed_flex_load.id == flex_load.id
    assert parsed_flex_load.bus.id == flex_load.bus.id
    assert parsed_flex_load.phases == flex_load.phases
    assert parsed_flex_load.s == flex_load.s
    assert [p.to_dict() for p in parsed_flex_load.flexible_params] == [p.to_dict() for p in flex_load.flexible_params]
