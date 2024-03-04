import warnings

import pytest

from roseau.load_flow import (
    Q_,
    Control,
    FlexibleParameter,
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
    assert e.value.msg == "'alpha' must be greater than 1 but 0.0 was provided."
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
    assert e.value.msg == "'alpha' must be greater than 1 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=Q_(210, "V"), u_down=Q_(0.220, "kV"), u_up=0, u_max=0, epsilon=0)
    assert e.value.msg == "'epsilon' must be greater than 0 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=Q_(210, "V"), u_down=Q_(0.220, "kV"), u_up=0, u_max=0, epsilon=1.2)
    assert e.value.msg == "'epsilon' must be lower than 1 but 1.200 was provided."
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
    assert e.value.msg == "'alpha' must be greater than 1 but 0.0 was provided."
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
    # s_max > 0
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(-1e3, "kVA"),
        )
    assert e.value.msg == "'s_max' must be greater than 0 but -1.0 MVA was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    # q_min >= -s_max
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(1e3, "kVA"),
            q_min=Q_(-2e3, "kVAr"),
        )
    assert e.value.msg == "q_min must be greater than -s_max (-1.0 MVA) but -2.0 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    # q_min <= s_max
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(1e3, "kVA"),
            q_min=Q_(2e3, "kVAr"),
        )
    assert e.value.msg == "q_min must be lower than s_max (1.0 MVA) but 2.0 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    # q_max <= s_max
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(1e3, "kVA"),
            q_max=Q_(2e3, "kVAr"),
        )
    assert e.value.msg == "q_max must be lower than s_max (1.0 MVA) but 2.0 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    # q_max >= -s_max
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleParameter(
            control_p=Control.constant(),
            control_q=Control.constant(),
            projection=Projection(type="euclidean"),
            s_max=Q_(1e3, "kVA"),
            q_max=Q_(-2e3, "kVAr"),
        )
    assert e.value.msg == "q_max must be greater than -s_max (-1.0 MVA) but -2.0 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    fp = FlexibleParameter(
        control_p=Control.constant(),
        control_q=Control.constant(),
        projection=Projection(type="euclidean"),
        s_max=Q_(3e3, "kVA"),
        q_max=Q_(2e3, "kVAr"),
        q_min=Q_(-2e3, "kVAr"),
    )
    fp.s_max = Q_(1e3, "kVA")  # reduce q_min and q_max
    assert fp.q_max.magnitude == 1e6
    assert fp.q_min.magnitude == -1e6

    # q_min < q_max
    fp = FlexibleParameter(
        control_p=Control.constant(),
        control_q=Control.constant(),
        projection=Projection(type="euclidean"),
        s_max=Q_(3e3, "kVA"),
        q_max=Q_(2e3, "kVAr"),
        q_min=Q_(-2e3, "kVAr"),
    )

    with pytest.raises(RoseauLoadFlowException) as e:
        fp.q_max = Q_(-2.5e3, "kVAr")
    assert e.value.msg == "q_max must be greater than q_min (-2.0 MVAr) but -2.5 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        fp.q_min = Q_(2.5e3, "kVAr")
    assert e.value.msg == "q_min must be lower than q_max (2.0 MVAr) but 2.5 MVAr was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_FLEXIBLE_PARAMETER_VALUE
