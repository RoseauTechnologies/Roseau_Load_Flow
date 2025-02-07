import re

import numpy as np
import pytest

from roseau.load_flow import Q_, SQRT3, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_single.models import Control, FlexibleParameter, Projection


def test_control():
    # Generate each possible kind of control
    c0 = Control.constant()
    c1 = Control.p_max_u_consumption(u_min=Q_(210, "V"), u_down=Q_(215, "V"))
    c2 = Control.p_max_u_production(u_up=Q_(245, "V"), u_max=Q_(250, "V"))
    c3 = Control.q_u(u_min=Q_(215, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(245, "V"))
    for c in (c0, c1, c2, c3):
        c_tmp = Control.from_dict(c.to_dict())
        assert c_tmp == c

        assert c.alpha == Control._DEFAULT_ALPHA
        assert c.epsilon == Control._DEFAULT_EPSILON

    # Equality with something which is not a control
    assert c0 != object()

    # Bad control type
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="unknown", u_min=210, u_down=220, u_up=230, u_max=240)  # type: ignore
    assert e.value.msg == "Unsupported control type 'unknown'"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE

    # Bad alpha
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=c3.u_min, u_down=c3.u_down, u_up=c3.u_up, u_max=c3.u_max, alpha=0)
    assert e.value.msg == "'alpha' must be greater than 1 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    # No results to export
    with pytest.raises(RoseauLoadFlowException) as e:
        c0.results_to_dict()
    assert e.value.msg == "The Control has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS

    # From dict with an error (bad control type)
    c_dict = c3.to_dict()
    c_dict["type"] = "unknown"
    with pytest.raises(RoseauLoadFlowException) as e:
        Control.from_dict(c_dict)
    assert e.value.msg == "Unsupported control type 'unknown'"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE

    # To dict with an error
    c3._type = "unknown"  # type: ignore
    with pytest.raises(RoseauLoadFlowException) as e:
        c3.to_dict()
    assert e.value.msg == "Unsupported control type 'unknown'"
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_TYPE
    c3._type = "q_u"


def test_bad_p_max_u_production_control():
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=-1, u_max=240)
    assert e.value.msg == "'u_up' must be greater than zero but -1.0 V <= 0.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=0, u_max=240)
    assert e.value.msg == "'u_up' must be greater than zero but 0.0 V <= 0.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=240, u_max=240)
    assert e.value.msg == "'u_max' must be greater than 'u_up' but 240.0 V <= 240.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=241, u_max=240)
    assert e.value.msg == "'u_max' must be greater than 'u_up' but 240.0 V <= 241.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_production", u_min=0, u_down=0, u_up=240, u_max=Q_(0.250, "kV"), alpha=0)
    assert e.value.msg == "'alpha' must be greater than 1 but 0.0 was provided."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    # Warning if values provided to useless parameters
    with pytest.warns(
        UserWarning,
        match=re.escape(
            "The following voltage parameters are not used by the 'p_max_u_production' control and "
            "should be set to 0 V: 'u_min' (2.0 V), 'u_down' (1.0 V)"
        ),
    ):
        Control(type="p_max_u_production", u_min=2, u_down=1, u_up=240, u_max=250)


def test_bad_p_max_u_consumption_control():
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=-1, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_min' must be greater than zero but -1.0 V <= 0.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=0, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_min' must be greater than zero but 0.0 V <= 0.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=210, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_down' must be greater than 'u_min' but 210.0 V <= 210.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="p_max_u_consumption", u_min=211, u_down=210, u_up=0, u_max=0)
    assert e.value.msg == "'u_down' must be greater than 'u_min' but 210.0 V <= 211.0 V."
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

    # Warning if values provided to useless parameters
    with pytest.warns(
        UserWarning,
        match=re.escape(
            "The following voltage parameters are not used by the 'p_max_u_consumption' control and "
            "should be set to 0 V: 'u_max' (-1.0 V), 'u_up' (2.3 V)"
        ),
    ):
        Control(type="p_max_u_consumption", u_min=210, u_down=220, u_up=2.3, u_max=-1)


def test_bad_q_u_control():
    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=-1, u_down=210, u_up=220, u_max=225)
    assert e.value.msg == "'u_min' must be greater than zero but -1.0 V <= 0.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=0, u_down=210, u_up=220, u_max=225)
    assert e.value.msg == "'u_min' must be greater than zero but 0.0 V <= 0.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=210, u_up=220, u_max=225)
    assert e.value.msg == "'u_down' must be greater than 'u_min' but 210.0 V <= 210.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=211, u_down=210.3, u_up=220, u_max=225)
    assert e.value.msg == "'u_down' must be greater than 'u_min' but 210.3 V <= 211.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=220, u_up=220, u_max=225)
    assert e.value.msg == "'u_up' must be greater than 'u_down' but 220.0 V <= 220.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=221, u_up=220, u_max=225)
    assert e.value.msg == "'u_up' must be greater than 'u_down' but 220.0 V <= 221.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=220, u_up=225, u_max=225)
    assert e.value.msg == "'u_max' must be greater than 'u_up' but 225.0 V <= 225.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Control(type="q_u", u_min=210, u_down=220, u_up=226, u_max=225)
    assert e.value.msg == "'u_max' must be greater than 'u_up' but 225.0 V <= 226.0 V."
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_CONTROL_VALUE


def test_projection():
    p0 = Projection(type="euclidean")
    p1 = Projection(type="keep_p")
    p2 = Projection(type="keep_q")
    for p in (p0, p1, p2):
        p_tmp = Projection.from_dict(p.to_dict())
        assert p_tmp == p

        assert p.alpha == Projection._DEFAULT_ALPHA
        assert p.epsilon == Projection._DEFAULT_EPSILON

    # Equality with something which is not a projection
    assert p0 != object()

    # Bad projection type
    with pytest.raises(RoseauLoadFlowException) as e:
        Projection(type="unknown", alpha=150, epsilon=1e-3)  # type: ignore
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

    # No results to export
    with pytest.raises(RoseauLoadFlowException) as e:
        p0.results_to_dict()
    assert e.value.msg == "The Projection has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS


def test_flexible_parameter():
    # Generate each possible kind of flexible parameters
    fp0 = FlexibleParameter.constant()
    fp1 = FlexibleParameter.p_max_u_consumption(u_min=Q_(210, "V"), u_down=Q_(215, "V"), s_max=Q_(150, "VA"))
    fp2 = FlexibleParameter.pq_u_consumption(
        up_min=Q_(210, "V"),
        up_down=Q_(215, "V"),
        uq_min=Q_(215, "V"),
        uq_down=Q_(220, "V"),
        uq_up=Q_(245, "V"),
        uq_max=Q_(250, "V"),
        s_max=Q_(150, "VA"),
    )
    fp3 = FlexibleParameter.p_max_u_production(u_up=Q_(245, "V"), u_max=Q_(250, "V"), s_max=Q_(150, "VA"))
    fp4 = FlexibleParameter.pq_u_production(
        up_up=Q_(245, "V"),
        up_max=Q_(250, "V"),
        uq_min=Q_(215, "V"),
        uq_down=Q_(220, "V"),
        uq_up=Q_(240, "V"),
        uq_max=Q_(245, "V"),
        s_max=Q_(150, "VA"),
    )
    fp5 = FlexibleParameter.q_u(
        u_min=Q_(215, "V"), u_down=Q_(220, "V"), u_up=Q_(240, "V"), u_max=Q_(245, "V"), s_max=Q_(150, "VA")
    )
    for fp in (fp0, fp1, fp2, fp3, fp4, fp5):
        fp_tmp = FlexibleParameter.from_dict(fp.to_dict())
        assert fp_tmp == fp

    # Equality with something which is not a flexible parameters
    assert fp0 != object()

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

    # No results to export
    with pytest.raises(RoseauLoadFlowException) as e:
        fp.results_to_dict()
    assert e.value.msg == "The FlexibleParameter has no results to export."
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_NO_RESULTS


@pytest.mark.no_patch_engine
def test_flexible_parameters_compute_powers():
    # Control P
    fp = FlexibleParameter(
        control_p=Control.p_max_u_production(u_up=Q_(240, "V"), u_max=Q_(250, "V")),
        control_q=Control.constant(),
        projection=Projection(type="keep_p"),
        s_max=Q_(15, "kVA"),
    )
    voltages = np.arange(205, 256, dtype=float)
    power = Q_(-7.5 + 3j, "kVA")
    res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)

    expected_res_flexible_powers = np.array(
        [
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.50000000e03 + 1000.0j,
            -2.49999999e03 + 1000.0j,
            -2.49999923e03 + 1000.0j,
            -2.49995807e03 + 1000.0j,
            -2.49773126e03 + 1000.0j,
            -2.41335660e03 + 1000.0j,
            -1.99773127e03 + 1000.0j,
            -1.49995884e03 + 1000.0j,
            -1.00004116e03 + 1000.0j,
            -5.02268727e02 + 1000.0j,
            -8.66433973e01 + 1000.0j,
            -2.26874099e00 + 1000.0j,
            -4.19257965e-02 + 1000.0j,
            -7.68024183e-04 + 1000.0j,
            -1.40668965e-05 + 1000.0j,
            -2.57644184e-07 + 1000.0j,
        ]
    )
    np.testing.assert_allclose(res_flexible_powers.m, expected_res_flexible_powers)

    # Check that the plot does not fail
    ax, res_flexible_powers = fp.plot_control_p(voltages=voltages, power=power)
    np.testing.assert_allclose(res_flexible_powers.m, expected_res_flexible_powers)

    # Control Q(U)
    fp = FlexibleParameter(
        control_p=Control.constant(),
        control_q=Control.q_u(
            u_min=Q_(210 * SQRT3, "V"),
            u_down=Q_(220 * SQRT3, "V"),
            u_up=Q_(240 * SQRT3, "V"),
            u_max=Q_(250 * SQRT3, "V"),
        ),
        projection=Projection(type="keep_q"),
        s_max=Q_(15, "kVA"),
    )
    voltages = np.arange(205, 256, dtype=float) * SQRT3
    power = Q_(-7.5, "kVA")
    res_flexible_powers = fp.compute_powers(voltages=voltages, power=power)
    expected_res_flexible_powers = [
        -5.00013230e-01 - 5.00000000e03j,
        -5.32061670e-01 - 4.99999999e03j,
        -2.77132482e00 - 4.99999923e03j,
        -2.04757468e01 - 4.99995807e03j,
        -1.50606317e02 - 4.99773126e03j,
        -9.26783091e02 - 4.91335660e03j,
        -2.18417487e03 - 4.49773126e03j,
        -2.50000004e03 - 3.99995807e03j,
        -2.50000000e03 - 3.49999923e03j,
        -2.50000000e03 - 2.99999999e03j,
        -2.50000000e03 - 2.50000000e03j,
        -2.50000000e03 - 2.00000001e03j,
        -2.50000000e03 - 1.50000077e03j,
        -2.50000000e03 - 1.00004193e03j,
        -2.50000000e03 - 5.02268741e02j,
        -2.50000000e03 - 8.66433976e01j,
        -2.50000000e03 - 2.26874099e00j,
        -2.50000000e03 - 4.19257966e-02j,
        -2.50000000e03 - 7.68024186e-04j,
        -2.50000000e03 - 1.40668960e-05j,
        -2.50000000e03 - 2.57643906e-07j,
        -2.50000000e03 - 4.71900297e-09j,
        -2.50000000e03 - 8.71525074e-11j,
        -2.50000000e03 - 2.77555756e-12j,
        -2.50000000e03 + 1.11022302e-12j,
        -2.50000000e03 + 0.00000000e00j,
        -2.50000000e03 - 1.08246745e-12j,
        -2.50000000e03 + 2.69229083e-12j,
        -2.50000000e03 + 8.75410855e-11j,
        -2.50000000e03 + 4.71891970e-09j,
        -2.50000000e03 + 2.57643101e-07j,
        -2.50000000e03 + 1.40668972e-05j,
        -2.50000000e03 + 7.68024186e-04j,
        -2.50000000e03 + 4.19257966e-02j,
        -2.50000000e03 + 2.26874099e00j,
        -2.50000000e03 + 8.66433976e01j,
        -2.50000000e03 + 5.02268741e02j,
        -2.50000000e03 + 1.00004193e03j,
        -2.50000000e03 + 1.50000077e03j,
        -2.50000000e03 + 2.00000001e03j,
        -2.50000000e03 + 2.50000000e03j,
        -2.50000000e03 + 2.99999999e03j,
        -2.50000000e03 + 3.49999923e03j,
        -2.50000004e03 + 3.99995807e03j,
        -2.18417487e03 + 4.49773126e03j,
        -9.26783091e02 + 4.91335660e03j,
        -1.50606317e02 + 4.99773126e03j,
        -2.04757468e01 + 4.99995807e03j,
        -2.77132482e00 + 4.99999923e03j,
        -5.32061663e-01 + 4.99999999e03j,
        -5.00013230e-01 + 5.00000000e03j,
    ]
    np.testing.assert_allclose(res_flexible_powers.m, expected_res_flexible_powers)

    # Check that the plot does not fail
    ax, res_flexible_powers = fp.plot_control_q(voltages=voltages, power=power)
    np.testing.assert_allclose(res_flexible_powers.m, expected_res_flexible_powers)

    # Plot PQ
    ax, res_flexible_powers = fp.plot_pq(
        voltages=voltages, power=power, voltages_labels_mask=np.isin(voltages, [240 * SQRT3, 250 * SQRT3])
    )
    np.testing.assert_allclose(res_flexible_powers.m, expected_res_flexible_powers)
