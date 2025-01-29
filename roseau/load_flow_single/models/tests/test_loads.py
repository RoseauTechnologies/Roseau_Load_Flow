import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow import Q_, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow_single.models import Bus, CurrentLoad, FlexibleParameter, ImpedanceLoad, PowerLoad, Projection


def test_flexible_load():
    bus = Bus(id="bus")
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

    # Bad loads
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl1", bus=bus, power=300 + 50j, flexible_param=fp_pq_prod)
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl2", bus=bus, power=10 + 250j, flexible_param=fp_pq_prod)
    assert "The reactive power is greater than the parameter q_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl3", bus=bus, power=10 - 250j, flexible_param=fp_pq_prod)
    assert "The reactive power is lower than the parameter q_min for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl4", bus=bus, power=100 + 50j, flexible_param=fp_pq_prod)
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad(id="fl5", bus=bus, power=-100 + 50j, flexible_param=fp_p_cons)
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Same mistakes with the powers setter
    load = PowerLoad(id="fl6", bus=bus, power=-200 + 50j, flexible_param=fp_pq_prod)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.power = 300 + 50j
    assert "The power is greater than the parameter s_max for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    load = PowerLoad(id="fl7", bus=bus, power=-100 + 50j, flexible_param=fp_pq_prod)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.power = 100 + 50j
    assert "There is a production control but a positive power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    load = PowerLoad(id="fl8", bus=bus, power=100 + 50j, flexible_param=fp_pq_cons)
    with pytest.raises(RoseauLoadFlowException) as e:
        load.power = -100 + 50j
    assert "There is a consumption control but a negative power for flexible load" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Good load
    load = PowerLoad(id="fl9", bus=bus, power=100 + 50j, flexible_param=fp_pq_cons)
    assert load.flexible_param == fp_pq_cons
    assert load._res_current is None  # load flow not run yet
    load._res_current = 0.25 / np.sqrt(3)
    load._res_voltage = 400
    assert np.isclose(load.res_power.m_as("VA"), 100)


def test_loads_to_dict():
    bus = Bus(id="bus")
    value = 1 + 2j

    # Power load
    assert_json_close(
        PowerLoad(id="load_s1", bus=bus, power=value).to_dict(include_results=False),
        {"id": "load_s1", "bus": "bus", "type": "power", "power": [1.0, 2.0]},
    )

    # Current load
    assert_json_close(
        CurrentLoad(id="load_i1", bus=bus, current=value).to_dict(include_results=False),
        {"id": "load_i1", "bus": "bus", "type": "current", "current": [1.0, 2.0]},
    )

    # Impedance load
    assert_json_close(
        ImpedanceLoad(id="load_z1", bus=bus, impedance=value).to_dict(include_results=False),
        {"id": "load_z1", "bus": "bus", "type": "impedance", "impedance": [1.0, 2.0]},
    )

    # Flexible load
    expected_dict = {
        "id": "load_f1",
        "bus": "bus",
        "type": "power",
        "power": [1.0, 2.0],
        "flexible_param": {
            "control_p": {"type": "constant"},
            "control_q": {"type": "constant"},
            "projection": {
                "type": "euclidean",
                "alpha": Projection._DEFAULT_ALPHA,
                "epsilon": Projection._DEFAULT_EPSILON,
            },
            "s_max": 1.0,
        },
    }
    fp = FlexibleParameter.constant()
    flex_load = PowerLoad(id="load_f1", bus=bus, power=value, flexible_param=fp)
    assert flex_load.flexible_param is not None
    assert_json_close(flex_load.to_dict(include_results=False), expected_dict)
    parsed_flex_load = PowerLoad.from_dict(expected_dict | {"bus": Bus(id="bus")})
    assert isinstance(parsed_flex_load, PowerLoad)
    assert parsed_flex_load.id == flex_load.id
    assert parsed_flex_load.bus.id == flex_load.bus.id
    assert np.allclose(parsed_flex_load.power.m, flex_load.power.m)
    assert parsed_flex_load.flexible_param is not None
    assert parsed_flex_load.flexible_param.to_dict(include_results=False) == flex_load.flexible_param.to_dict(
        include_results=False
    )


def test_loads_units():
    bus = Bus(id="bus")

    # Good unit constructor
    load = PowerLoad(id="pl1", bus=bus, power=Q_(1, "kVA"))
    assert np.allclose(load._power, 1000)

    # Good unit setter
    load = PowerLoad(id="pl2", bus=bus, power=100)
    assert np.allclose(load._power, 100)
    load.power = Q_(1, "kVA")
    assert np.allclose(load._power, 1000)

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'VA'"):
        PowerLoad(id="pl3", bus=bus, power=Q_(100, "A"))

    # Bad unit setter
    load = PowerLoad(id="pl4", bus=bus, power=100)
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'VA'"):
        load.power = Q_(100, "A")
