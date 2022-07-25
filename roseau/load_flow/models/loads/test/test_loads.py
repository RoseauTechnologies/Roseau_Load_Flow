import numpy as np
import pytest

from roseau.load_flow import (
    AdmittanceLoad,
    Bus,
    ElectricalNetwork,
    FlexibleLoad,
    FlexibleParameter,
    Ground,
    ImpedanceLoad,
    LineCharacteristics,
    PotentialRef,
    PowerLoad,
    SimplifiedLine,
    VoltageSource,
)
from roseau.load_flow.utils import ThundersValueError


def test_loads():
    bus = Bus("bus", 4)
    # Bad number of phases
    with pytest.raises(ThundersValueError) as e:
        PowerLoad("load", 4, bus, [100, 100])
    assert "Incorrect number of powers" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        PowerLoad("load", 4, bus, [100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.args[0]

    with pytest.raises(ThundersValueError) as e:
        AdmittanceLoad("load", 4, bus, [100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        AdmittanceLoad("load", 4, bus, [100, 100, 100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]

    with pytest.raises(ThundersValueError) as e:
        ImpedanceLoad("load", 4, bus, [100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        ImpedanceLoad("load", 4, bus, [100, 100, 100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]

    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("load", 4, bus, [100, 100], [FlexibleParameter.constant()] * 3)
    assert "Incorrect number of powers" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("load", 4, bus, [100, 100, 100, 100], [FlexibleParameter.constant()] * 3)
    assert "Incorrect number of powers" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("load", 4, bus, [100, 100, 100], [FlexibleParameter.constant()] * 2)
    assert "Incorrect number of parameters" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("load", 4, bus, [100, 100, 100], [FlexibleParameter.constant()] * 4)
    assert "Incorrect number of parameters" in e.value.args[0]

    # Bad impedance
    with pytest.raises(ThundersValueError) as e:
        ImpedanceLoad("load", 4, bus, [100, 100, 0.0])
    assert "An impedance for load" in e.value.args[0]

    # Update
    load = PowerLoad("load", 4, bus, [100, 100, 100])
    with pytest.raises(ThundersValueError) as e:
        load.update_powers([100, 100])
    assert "Incorrect number of powers" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        load.update_powers([100, 100, 100, 100])
    assert "Incorrect number of powers" in e.value.args[0]

    load = AdmittanceLoad("load", 4, bus, [100, 100, 100])
    with pytest.raises(ThundersValueError) as e:
        load.update_admittances([100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        load.update_admittances([100, 100, 100, 100])
    assert "Incorrect number of admittance" in e.value.args[0]

    load = ImpedanceLoad("load", 4, bus, [100, 100, 100])
    with pytest.raises(ThundersValueError) as e:
        load.update_impedance([100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        load.update_impedance([100, 100, 100, 100])
    assert "Incorrect number of impedance" in e.value.args[0]
    with pytest.raises(ThundersValueError) as e:
        load.update_impedance([100, 100, 0.0])
    assert "An impedance for load" in e.value.args[0]


def test_flexible_load():
    vn = 400 / np.sqrt(3)
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

    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("flexible load", 4, bus, [300 + 50j, 0, 0j], [fp, fc, fc])
    assert "The power is greater than the parameter s_max for flexible load" in e.value.args[0]

    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("flexible load", 4, bus, [100 + 50j, 0, 0j], [fp, fc, fc])
    assert "There is a production control but a positive power for flexible load" in e.value.args[0]

    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("flexible load", 4, bus, [0, 0, 0j], [fp, fc, fc])
    assert "There is a P control but a null active power for flexible load" in e.value.args[0]

    fp = FlexibleParameter.p_max_u_consumption(
        u_min=210, u_down=220, s_max=300, alpha_control=100.0, alpha_proj=100.0, epsilon_proj=0.01
    )

    with pytest.raises(ThundersValueError) as e:
        FlexibleLoad("flexible load", 4, bus, [-100 + 50j, 0, 0j], [fp, fc, fc])
    assert "There is a consumption control but a negative power for flexible load" in e.value.args[0]

    # Good load
    fp = FlexibleParameter.pq_u_consumption(
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
    fp2 = FlexibleParameter.q_u(u_min=210, u_down=220, u_up=240, u_max=250, s_max=300)
    ground = Ground()
    _ = PotentialRef(ground)
    vs = VoltageSource("vs", 4, ground, [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)])
    bus = Bus("bus", 4)
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    _ = SimplifiedLine(id_="line", n=4, bus1=vs, bus2=bus, line_characteristics=line_characteristics, length=10)
    flexible_load = FlexibleLoad("flexible load", 4, bus, [100 + 50j, 100 + 50j, 0j], [fp, fp2, fc])
    _ = PowerLoad("load", 4, bus, [100, 100, 100])

    en = ElectricalNetwork.from_element(vs)
    en.solve_load_flow()

    powers = flexible_load.get_powers()
    assert powers[0].real > 0 and powers.real[0] < 100
    assert powers[1].real == 100 and powers[1].imag > 0 and powers.imag[1] < 50
    assert powers[2] == 0j
