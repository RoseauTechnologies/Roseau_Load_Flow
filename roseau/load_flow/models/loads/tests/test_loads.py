import pytest
from pint.errors import DimensionalityError

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import Bus, FlexibleParameter, Load
from roseau.load_flow.utils import Q_


def test_load_normal():
    bus = Bus("bus", 4)
    load = Load("load", 4, bus, s=Q_([1, 1, 1], "kVA"))

    # Store value in SI unit and strip the unit
    assert not isinstance(load.s, Q_)
    assert list(load.s) == [1000, 1000, 1000]

    # The load id is in the load string representation
    assert "id='load'" in str(load)

    # Update the power
    load = Load("load", 4, bus, s=[100, 100, 100])
    assert load.s == [100, 100, 100]
    load.update_powers([50j, 50j, 50j])
    assert load.s == [50j, 50j, 50j]

    # TODO re-enable these tests when constant current is implemented
    # Update the current
    # load = Load("load", 4, bus, i=[100, 100, 100])
    # assert load.i == [100, 100, 100]
    # load.update_currents([50j, 50j, 50j])
    # assert load.i == [50j, 50j, 50j]

    # Update the impedance
    load = Load("load", 4, bus, z=[100, 100, 100])
    assert load.z == [100, 100, 100]
    load.update_impedances([50j, 50j, 50j])
    assert load.z == [50j, 50j, 50j]

    # The result currents
    load = Load("load", 4, bus, s=[100, 100, 100])
    load.currents = Q_([0.5j, 0.5j, 0.5j], "kA")
    assert (load.currents.m_as("A") == [500j, 500j, 500j]).all()


def test_load_errors():
    bus = Bus("bus", 4)
    # Bad number of phases
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, s=[100, 100])
    assert "Incorrect number of power" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, s=[100, 100, 100, 100])
    assert "Incorrect number of power" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 3, bus, s=[100, 100])  # delta
    assert "Incorrect number of power" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 3, bus, s=[100, 100, 100, 100])  # delta
    assert "Incorrect number of power" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    # TODO re-enable these tests when constant current is implemented
    # with pytest.raises(RoseauLoadFlowException) as e:
    #     Load("load", 4, bus, i=[100, 100])
    # assert "Incorrect number of current" in e.value.args[0]
    # assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    # with pytest.raises(RoseauLoadFlowException) as e:
    #     Load("load", 4, bus, i=[100, 100, 100, 100])
    # assert "Incorrect number of current" in e.value.args[0]
    # assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    # with pytest.raises(RoseauLoadFlowException) as e:
    #     Load("load", 3, bus, i=[100, 100])  # delta
    # assert "Incorrect number of current" in e.value.args[0]
    # assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    # with pytest.raises(RoseauLoadFlowException) as e:
    #     Load("load", 3, bus, i=[100, 100, 100, 100])  # delta
    # assert "Incorrect number of current" in e.value.args[0]
    # assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, z=[100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, z=[100, 100, 100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 3, bus, z=[100, 100])  # delta
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 3, bus, z=[100, 100, 100, 100])  # delta
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, s=[100, 100, 100], flexible_parameters=[FlexibleParameter.constant()] * 2)
    assert "Incorrect number of parameters" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, s=[100, 100, 100], flexible_parameters=[FlexibleParameter.constant()] * 4)
    assert "Incorrect number of parameters" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE

    # Bad impedance
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, bus, z=[100, 100, 0.0])
    assert "An impedance for load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 3, bus, z=[100, 100, 0.0])  # delta
    assert "An impedance for load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    # Bad unit
    with pytest.raises(
        DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'volt_ampere'"
    ) as e:
        Load("load", 4, bus, s=Q_([100, 100, 100], "A"))

    # Update
    loads = [
        Load("load", 4, bus, s=[100, 100, 100]),  # star
        Load("load", 3, bus, s=[100, 100, 100]),  # delta
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_powers([100, 100])
        assert "Incorrect number of power" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_powers([100, 100, 100, 100])
        assert "Incorrect number of power" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    # TODO re-enable these tests when constant current is implemented
    # loads = [
    #     Load("load", 4, bus, i=[100, 100, 100]),  # star
    #     Load("load", 3, bus, i=[100, 100, 100]),  # delta
    # ]
    # for load in loads:
    #     with pytest.raises(RoseauLoadFlowException) as e:
    #         load.update_currents([100, 100])
    #     assert "Incorrect number of current" in e.value.args[0]
    #     assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_I_SIZE
    #     with pytest.raises(RoseauLoadFlowException) as e:
    #         load.update_currents([100, 100, 100, 100])
    #     assert "Incorrect number of current" in e.value.args[0]
    #     assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_I_SIZE

    loads = [
        Load("load", 4, bus, z=[100, 100, 100]),  # star
        Load("load", 3, bus, z=[100, 100, 100]),  # delta
    ]
    for load in loads:
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_impedances([100, 100])
        assert "Incorrect number of impedance" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_impedances([100, 100, 100, 100])
        assert "Incorrect number of impedance" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
        with pytest.raises(RoseauLoadFlowException) as e:
            load.update_impedances([100, 100, 0.0])
        assert "An impedance for load" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_VALUE


def test_flexible_load():
    bus = Bus("bus", 4)
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

    # Bad control parameters
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("flexible load", 4, bus, s=[300 + 50j, 0, 0j], flexible_parameters=[fp_pq_prod, fp_const, fp_const])
    assert "The power is greater than the parameter s_max for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("flexible load", 4, bus, s=[100 + 50j, 0, 0j], flexible_parameters=[fp_pq_prod, fp_const, fp_const])
    assert "There is a production control but a positive power for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("flexible load", 4, bus, s=[0, 0, 0j], flexible_parameters=[fp_pq_prod, fp_const, fp_const])
    assert "There is a P control but a null active power for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("flexible load", 4, bus, s=[-100 + 50j, 0, 0j], flexible_parameters=[fp_p_cons, fp_const, fp_const])
    assert "There is a consumption control but a negative power for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Only power loads with neutral can have control (this is the legacy behavior with FlexibleLoad)
    # (TODO: what needs to be done to enable it on other loads?)
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("flexible load", 4, bus, z=[100, 100, 100], flexible_parameters=[fp_pq_prod, fp_const, fp_const])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "Flexible parameters are currently only available for power loads with neutral connection" in e.value.args[0]
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("flexible load", 3, bus, s=[100, 100, 100], flexible_parameters=[fp_pq_prod, fp_const, fp_const])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "Flexible parameters are currently only available for power loads with neutral connection" in e.value.args[0]

    # Getting/Setting the power on a non flexible load
    load = Load("normal load", 4, bus, s=[100 + 50j, 0, 0j])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "Cannot get the power of a non flexible load" in e.value.args[0]
    with pytest.raises(RoseauLoadFlowException) as e:
        load.powers = [100, 100, 100]
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "Cannot set the power of a non flexible load" in e.value.args[0]

    # Good load
    load = Load("flexible load", 4, bus, s=[100 + 50j, 0, 0j], flexible_parameters=[fp_pq_cons, fp_const, fp_const])
    assert load.flexible_parameters == [fp_pq_cons, fp_const, fp_const]
    assert load.is_flexible()
    assert load._powers is None  # cannot use load.powers because it is passing None to pint
    load.powers = [100, 100, 100]
    assert (load.powers.m_as("VA") == [100, 100, 100]).all()


def test_temporarily_unavailable_load_error():
    # Constant current load not implemented
    # -------------------------------------
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, Bus("bus", 4), i=[100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "i (constant current) is not implemented" in e.value.args[0]

    load = Load("load", 4, Bus("bus", 4), s=[100, 100, 100])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_currents([100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "i (constant current) is not implemented" in e.value.args[0]

    # Only s or z can be used
    # -----------------------
    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, Bus("bus", 4), s=[100, 100, 100], z=[100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "only s (constant power) or z (constant impedance), not both" in e.value.args[0]

    with pytest.raises(RoseauLoadFlowException) as e:
        Load("load", 4, Bus("bus", 4), s=None, z=None)
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "either s (constant power) or z (constant impedance), non given" in e.value.args[0]

    load = Load("load", 4, Bus("bus", 4), s=[100, 100, 100])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_impedances([100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "only s (constant power) or z (constant impedance), not both" in e.value.args[0]

    load = Load("load", 4, Bus("bus", 4), z=[100, 100, 100])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_powers([100, 100, 100])
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "only s (constant power) or z (constant impedance), not both" in e.value.args[0]

    # Test NO bypassing the check
    load = Load("load", 4, Bus("bus", 4), s=[100, 100, 100])
    load.z = [100, 100, 100]  # cheating
    with pytest.raises(RoseauLoadFlowException) as e:
        load.to_dict()
    assert e.value.code == RoseauLoadFlowExceptionCode.BAD_LOAD_TYPE
    assert "only s (constant power) or z (constant impedance), not both" in e.value.args[0]
