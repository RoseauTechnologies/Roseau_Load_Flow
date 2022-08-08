import pytest

from roseau.load_flow import AdmittanceLoad, Bus, FlexibleLoad, FlexibleParameter, ImpedanceLoad, PowerLoad
from roseau.load_flow.utils import RoseauLoadFlowException, RoseauLoadFlowExceptionCode


def test_loads():
    bus = Bus("bus", 4)
    # Bad number of phases
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", 4, bus, [100, 100])
    assert "Incorrect number of powers" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        PowerLoad("load", 4, bus, [100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        AdmittanceLoad("load", 4, bus, [100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Y_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        AdmittanceLoad("load", 4, bus, [100, 100, 100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Y_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", 4, bus, [100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", 4, bus, [100, 100, 100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE

    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("load", 4, bus, [100, 100], [FlexibleParameter.constant()] * 3)
    assert "Incorrect number of powers" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("load", 4, bus, [100, 100, 100, 100], [FlexibleParameter.constant()] * 3)
    assert "Incorrect number of powers" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("load", 4, bus, [100, 100, 100], [FlexibleParameter.constant()] * 2)
    assert "Incorrect number of parameters" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("load", 4, bus, [100, 100, 100], [FlexibleParameter.constant()] * 4)
    assert "Incorrect number of parameters" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_PARAMETERS_SIZE

    # Bad impedance
    with pytest.raises(RoseauLoadFlowException) as e:
        ImpedanceLoad("load", 4, bus, [100, 100, 0.0])
    assert "An impedance for load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_VALUE

    # Update
    load = PowerLoad("load", 4, bus, [100, 100, 100])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_powers([100, 100])
    assert "Incorrect number of powers" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_powers([100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_SIZE

    load = AdmittanceLoad("load", 4, bus, [100, 100, 100])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_admittances([100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Y_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_admittances([100, 100, 100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Y_SIZE

    load = ImpedanceLoad("load", 4, bus, [100, 100, 100])
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_impedance([100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_impedance([100, 100, 100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_SIZE
    with pytest.raises(RoseauLoadFlowException) as e:
        load.update_impedance([100, 100, 0.0])
    assert "An impedance for load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_Z_VALUE


def test_flexible_load():
    bus = Bus("bus", 4)
    fp = FlexibleParameter.pq_u_production(
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
    fc = FlexibleParameter.constant()

    # Bad loads
    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("flexible load", 4, bus, [300 + 50j, 0, 0j], [fp, fc, fc])
    assert "The power is greater than the parameter s_max for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("flexible load", 4, bus, [100 + 50j, 0, 0j], [fp, fc, fc])
    assert "There is a production control but a positive power for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("flexible load", 4, bus, [0, 0, 0j], [fp, fc, fc])
    assert "There is a P control but a null active power for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    fp = FlexibleParameter.p_max_u_consumption(
        u_min=210, u_down=220, s_max=300, alpha_control=100.0, alpha_proj=100.0, epsilon_proj=0.01
    )

    with pytest.raises(RoseauLoadFlowException) as e:
        FlexibleLoad("flexible load", 4, bus, [-100 + 50j, 0, 0j], [fp, fc, fc])
    assert "There is a consumption control but a negative power for flexible load" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_S_VALUE

    # Good load
    _ = FlexibleParameter.pq_u_consumption(
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
