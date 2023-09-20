import warnings
from contextlib import contextmanager

import numpy as np
import numpy.testing as npt
import pytest
from matplotlib import pyplot as plt

from roseau.load_flow import (
    Q_,
    Control,
    ElectricalNetwork,
    FlexibleParameter,
    PowerLoad,
    Projection,
    RoseauLoadFlowException,
    RoseauLoadFlowExceptionCode,
)


def test_control():
    # Bad control type
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="unknown", u_min=210, u_down=220, u_up=230, u_max=240)
    assert e.value.msg == "Unsupported control type 'unknown'"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE

    # Bad control value for p_max_u_production
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=-1, u_max=240)
    assert e.value.msg == "'u_up' must be greater than zero as it is a voltage norm: -1 V was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=0, u_max=240)
    assert e.value.msg == "'u_up' must be greater than zero as it is a voltage norm: 0 V was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=240, u_max=240)
    assert e.value.msg == "'u_max' must be greater than the value 'u_up', but 240 V <= 240 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=241, u_max=240)
    assert e.value.msg == "'u_max' must be greater than the value 'u_up', but 240 V <= 241 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=240, u_max=Q_(0.250, "kV"), alpha=0)
    assert e.value.msg == "'alpha' must be greater than 0 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    # Warning if values provided to useless values
    with warnings.catch_warnings(record=True) as records:
        Control(type="p_max_u_production", u_min=2, u_down=1, u_up=240, u_max=250)
    assert len(records) == 1
    assert (
        records[0].message.args[0] == "Some voltage norm value(s) will not be used by the 'p_max_u_production' "
        "control. Nevertheless, values different from 0 were given: 'u_min' (2.0 V), 'u_down' (1.0 V)"
    )
    assert records[0].category == UserWarning

    # Bad control value for p_max_u_consumption
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=-1, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_min' must be greater than zero as it is a voltage norm: -1 V was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=0, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_min' must be greater than zero as it is a voltage norm: 0 V was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=210, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_down' must be greater than the value 'u_min', but 210 V <= 210 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=211, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_down' must be greater than the value 'u_min', but 210 V <= 211 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=Q_(210, "V"), u_down=Q_(0.220, "kV"), u_up=0, u_max=0, alpha=0)
    assert e.value.msg == "'alpha' must be greater than 0 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    # Warning if values provided to useless values
    with warnings.catch_warnings(record=True) as records:
        Control(type="p_max_u_consumption", u_min=210, u_down=220, u_up=2.3, u_max=-1)
    assert len(records) == 1
    assert (
        records[0].message.args[0] == "Some voltage norm value(s) will not be used by the 'p_max_u_consumption' "
        "control. Nevertheless, values different from 0 were given: 'u_max' (-1.0 "
        "V), 'u_up' (2.3 V)"
    )
    assert records[0].category == UserWarning

    # Bad control value for q_u
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=-1, u_down=210, u_up=220, u_max=225)
    assert e.value.msg == "'u_min' must be greater than zero as it is a voltage norm: -1 V was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=0, u_down=210, u_up=220, u_max=225)
    assert e.value.msg == "'u_min' must be greater than zero as it is a voltage norm: 0 V was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=210, u_up=220, u_max=225)
    assert e.value.msg == "'u_down' must be greater than the value 'u_min', but 210 V <= 210 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=211, u_down=210.3, u_up=220, u_max=225)
    assert e.value.msg == "'u_down' must be greater than the value 'u_min', but 210.3 V <= 211 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=220, u_up=220, u_max=225)
    assert e.value.msg == "'u_up' must be greater than the value 'u_down', but 220 V <= 220 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=221, u_up=220, u_max=225)
    assert e.value.msg == "'u_up' must be greater than the value 'u_down', but 220 V <= 221 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=220, u_up=225, u_max=225)
    assert e.value.msg == "'u_max' must be greater than the value 'u_up', but 225 V <= 225 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=220, u_up=226, u_max=225)
    assert e.value.msg == "'u_max' must be greater than the value 'u_up', but 225 V <= 226 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(
            type="q_u",
            u_min=Q_(210, "V"),
            u_down=Q_(0.220, "kV"),
            u_up=Q_(0.230, "kV"),
            u_max=Q_(2400.5, "dV"),
            alpha=0,
        )
    assert e.value.msg == "'alpha' must be greater than 0 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE


def test_projection():
    # Bad projection type
    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="unknown", alpha=150, epsilon=1e-3)
    assert e.value.msg == "Unsupported projection type 'unknown'"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_TYPE

    # Bad projection value
    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="keep_p", alpha=-1, epsilon=1e-2)
    assert e.value.msg == "'alpha' must be greater than 0 but -1.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="keep_p", alpha=0, epsilon=1e-2)
    assert e.value.msg == "'alpha' must be greater than 0 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="keep_p", alpha=150, epsilon=-1)
    assert e.value.msg == "'epsilon' must be greater than 0 but -1.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="keep_p", alpha=150, epsilon=0)
    assert e.value.msg == "'epsilon' must be greater than 0 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="keep_p", alpha=0.1)
    assert e.value.msg == "'alpha' must be greater than 1 but 0.1 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="keep_p", alpha=150, epsilon=1.2)
    assert e.value.msg == "'epsilon' must be lower than 1 but 1.200 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_PROJECTION_VALUE


def test_flexible_parameter():
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(-1e3, "kVA"),
        )
    assert e.value.msg == "'s_max' must be greater than 0 but -1.0 MVA was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(1e3, "kVA"),
            q_min=Q_(-2e3, "kVAr"),
        )
    assert e.value.msg == "'q_min' must be greater than -s_max (-1.0 MVA) but -2.0 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(1e3, "kVA"),
            q_max=Q_(2e3, "kVAr"),
        )
    assert e.value.msg == "'q_max' must be lesser than s_max (1.0 MVA) but 2.0 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE


@pytest.fixture(params=["constant", "p_max_u_production", "p_max_u_consumption"])
def control_p(request) -> Control:
    if request.param == "constant":
        return Control.constant()
    elif request.param == "p_max_u_production":
        return Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V"))
    elif request.param == "p_max_u_consumption":
        return Control.p_max_u_production(u_up=Q_(210, "V"), u_max=Q_(220, "V"))
    raise NotImplementedError(request.param)


@pytest.fixture(params=["constant", "q_u"])
def control_q(request) -> Control:
    if request.param == "constant":
        return Control.constant()
    elif request.param == "q_u":
        return Control.q_u(u_min=Q_(210, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(250, "V"))
    raise NotImplementedError(request.param)


@pytest.fixture(params=["keep_p", "keep_q", "euclidean"])
def projection(request) -> Projection:
    return Projection(type=request.param)


@pytest.fixture()
def flexible_parameter(control_p, control_q, projection) -> FlexibleParameter:
    return FlexibleParameter(control_p=control_p, control_q=control_q, projection=projection, s_max=Q_(5, "kVA"))


@pytest.fixture()
def monkeypatch_flexible_parameter_compute_powers(monkeypatch, rg):
    @contextmanager
    def inner():
        nonlocal monkeypatch
        with monkeypatch.context() as m:
            m.setattr(target=ElectricalNetwork, name="solve_load_flow", value=lambda *args, **kwargs: 2)
            m.setattr(
                target=PowerLoad,
                name="res_flexible_powers",
                value=property(
                    lambda x: Q_([rg.normal(loc=-2500, scale=1000) + 1j * rg.normal(loc=0, scale=2500)], "VA")
                ),
            )
            yield m

    return inner


def test_plot(flexible_parameter, monkeypatch_flexible_parameter_compute_powers):
    voltages = np.array(range(205, 256, 1), dtype=float)
    power = Q_(-2.5 + 1j, "kVA")
    auth = ("username", "password")

    #
    # Test compute powers
    #
    with monkeypatch_flexible_parameter_compute_powers():
        res_flexible_powers = flexible_parameter.compute_powers(auth=auth, voltages=voltages, power=power)

    #
    # Plot control P
    #
    fig, ax = plt.subplots()
    ax, res_flexible_powers_1 = flexible_parameter.plot_control_p(
        auth=auth, voltages=voltages, power=power, res_flexible_powers=res_flexible_powers, ax=ax
    )
    npt.assert_allclose(res_flexible_powers.m_as("VA"), res_flexible_powers_1.m_as("VA"))
    plt.close(fig)

    # The same but do not provide the res_flexible_powers
    fig, ax = plt.subplots()
    with monkeypatch_flexible_parameter_compute_powers():
        ax, res_flexible_powers_2 = flexible_parameter.plot_control_p(auth=auth, voltages=voltages, power=power, ax=ax)
    assert not np.allclose(res_flexible_powers.m_as("VA"), res_flexible_powers_2.m_as("VA"))
    plt.close(fig)

    # Plot control Q
    ax, res_flexible_powers = flexible_parameter.plot_control_q(
        auth=auth, voltages=voltages, power=power, res_flexible_powers=res_flexible_powers, ax=ax
    )

    # The same but do not provide the res_flexible_powers
    fig, ax = plt.subplots()
    with monkeypatch_flexible_parameter_compute_powers():
        ax, res_flexible_powers_3 = flexible_parameter.plot_control_q(auth=auth, voltages=voltages, power=power, ax=ax)
    assert not np.allclose(res_flexible_powers.m_as("VA"), res_flexible_powers_3.m_as("VA"))
    plt.close(fig)

    # Plot trajectory in the (P, Q) plane
    fig, ax = plt.subplots()
    ax, res_flexible_powers_4 = flexible_parameter.plot_pq(
        auth=auth,
        voltages=voltages,
        power=power,
        res_flexible_powers=res_flexible_powers,
        voltages_labels_mask=np.isin(voltages, [240, 250]),
        ax=ax,
    )
    npt.assert_allclose(res_flexible_powers.m_as("VA"), res_flexible_powers_4.m_as("VA"))
    plt.close(fig)

    # The same but do not provide the res_flexible_powers
    fig, ax = plt.subplots()  # Create a new ax that is not used directly in the following function call
    with monkeypatch_flexible_parameter_compute_powers():
        ax, res_flexible_powers_5 = flexible_parameter.plot_pq(
            auth=auth,
            voltages=voltages,
            power=power,
            voltages_labels_mask=np.isin(voltages, [240, 250]),
        )
    assert not np.allclose(res_flexible_powers.m_as("VA"), res_flexible_powers_5.m_as("VA"))
    plt.close(fig)
