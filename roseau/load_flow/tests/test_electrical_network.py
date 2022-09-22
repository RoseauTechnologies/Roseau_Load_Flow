import numpy as np
import pytest
import requests_mock

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.models import (
    Bus,
    DeltaWyeTransformer,
    Ground,
    LineCharacteristics,
    PotentialRef,
    PowerLoad,
    SimplifiedLine,
    Switch,
    TransformerCharacteristics,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork


def test_add_and_remove():
    ground = Ground()
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    vs = VoltageSource(
        id="source",
        n=4,
        ground=ground,
        voltages=voltages,
    )
    load_bus = Bus(id="load bus", n=4)
    load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    line_characteristics = LineCharacteristics("test", z_line=np.eye(4, dtype=complex))
    line = SimplifiedLine(
        id="line", n=4, bus1=vs, bus2=load_bus, line_characteristics=line_characteristics, length=10  # km
    )
    _ = PotentialRef(element=ground)
    en = ElectricalNetwork.from_element(vs)
    en.remove_element(load.id)
    new_load = PowerLoad(id="power load", n=4, bus=load_bus, s=[100 + 0j, 100 + 0j, 100 + 0j])
    en.add_element(new_load)

    # Bad key
    with pytest.raises(RoseauLoadFlowException) as e:
        en.remove_element("unknown element")
    assert "is not a valid bus, branch or load id" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_ELEMENT_ID

    # Adding ground
    ground2 = Ground()
    with pytest.raises(RoseauLoadFlowException) as e:
        en.add_element(ground2)
    assert e.value.args[0] == "Only lines, loads and buses can be added to the network."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_ELEMENT_OBJECT

    # Remove line => 2 separated connected components
    with pytest.raises(RoseauLoadFlowException) as e:
        en.remove_element(line.id)
        en.solve_load_flow(auth=("", ""))
    assert "does not have a potential reference" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE


def test_bad_networks():
    # No voltage source
    ground = Ground()
    bus1 = Bus("bus1", 3)
    bus2 = Bus("bus2", 3)
    ground.connect(bus2)
    line_characteristics = LineCharacteristics("test", z_line=np.eye(3, dtype=complex))
    line = SimplifiedLine(id="line", n=3, bus1=bus1, bus2=bus2, line_characteristics=line_characteristics, length=10)
    p_ref = PotentialRef(ground)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(bus1)
    assert e.value.args[0] == "There is no voltage source provided in the network, you must provide at least one."
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_VOLTAGE_SOURCE

    # Bad constructor
    vs = VoltageSource("vs", 4, ground, [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    switch = Switch("switch", 4, vs, bus1)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork([vs, bus1], [line, switch], [], [ground, p_ref])  # no bus2
    assert "but has not been added to the network, you should add it with 'add_element'." in e.value.args[0]
    assert bus2.id in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.UNKNOWN_ELEMENT

    # No potential reference
    bus3 = Bus("bus3", 4)
    transformer_characteristics = TransformerCharacteristics(
        type_name="t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    _ = DeltaWyeTransformer("transfo", bus2, bus3, transformer_characteristics)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(vs)
    assert "does not have a potential reference" in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_POTENTIAL_REFERENCE

    # Good network
    ground.connect(bus3)

    # 2 potential reference
    _ = PotentialRef(bus3)
    with pytest.raises(RoseauLoadFlowException) as e:
        ElectricalNetwork.from_element(vs)
    assert "has 2 potential references, it should have only one." in e.value.args[0]
    assert e.value.args[1] == RoseauLoadFlowExceptionCode.SEVERAL_POTENTIAL_REFERENCE


def test_solve_load_flow():
    ground = Ground()
    vs = VoltageSource("vs", 4, ground, [20000.0 + 0.0j, -10000.0 - 17320.508076j, -10000.0 + 17320.508076j])
    load_bus = Bus("bus", 4)
    ground.connect(load_bus)
    load = PowerLoad("load", 4, load_bus, [100, 100, 100])
    pref = PotentialRef(ground)

    lc = LineCharacteristics("test", 10 * np.eye(4, dtype=complex))
    line = SimplifiedLine("line", 4, vs, load_bus, lc, 1.0)

    en = ElectricalNetwork([vs, load_bus], [line], [load], [pref, ground])

    with requests_mock.Mocker() as m:
        # Good result
        json_result = {
            "info": {
                "status": "success",
                "resolutionMethod": "newton",
                "iterations": 1,
                "targetError": 1e-06,
                "finalError": 6.296829377361313e-14,
            },
            "buses": [
                {
                    "id": "vs",
                    "potentials": {
                        "va": [20000.0, 0.0],
                        "vb": [-10000.0, -17320.508076],
                        "vc": [-10000.0, 17320.508076],
                        "vn": [0.0, 0.0],
                    },
                },
                {
                    "id": "bus",
                    "potentials": {
                        "va": [19999.949999875, 0.0],
                        "vb": [-9999.9749999375, -17320.464774621556],
                        "vc": [-9999.9749999375, 17320.464774621556],
                        "vn": [1.3476526914363477e-12, 0.0],
                    },
                },
            ],
            "branches": [
                {
                    "id": "line",
                    "currents1": {
                        "ia": [0.005, 0.0],
                        "ib": [-0.0025, -0.0043],
                        "ic": [-0.0025, 0.0043],
                        "in": [-1.347e-13, 0.0],
                    },
                    "currents2": {
                        "ia": [0.005, 0.0],
                        "ib": [-0.0025, -0.0043],
                        "ic": [-0.0025, 0.0043],
                        "in": [-1.347e-13, 0.0],
                    },
                }
            ],
            "loads": [
                {
                    "id": "load",
                    "currents": {
                        "ia": [0.005, -0.0],
                        "ib": [-0.0025, -0.0043],
                        "ic": [-0.0025, 0.0043],
                        "in": [-1.347e-13, 0.0],
                    },
                }
            ],
        }
        m.post(f"{ElectricalNetwork.DEFAULT_BASE_URL}/solve/", status_code=200, json=json_result)
        en.solve_load_flow(auth=("", ""))
        assert len(load_bus.potentials) == 4

        # No convergence
        load.update_powers([10000000, 100, 100])
        json_result = {
            "info": {
                "status": "failure",
                "resolutionMethod": "newton",
                "iterations": 50,
                "targetError": 1e-06,
                "finalError": 14037.977318668112,
            },
            "buses": [
                {
                    "id": "vs",
                    "potentials": {
                        "va": [20000.0, 0.0],
                        "vb": [-10000.0, -17320.508076],
                        "vc": [-10000.0, 17320.508076],
                        "vn": [0.0, 0.0],
                    },
                },
                {
                    "id": "bus",
                    "potentials": {
                        "va": [110753.81558442864, 1.5688245436058308e-26],
                        "vb": [-9999.985548801811, -17320.50568183019],
                        "vc": [-9999.985548801811, 17320.50568183019],
                        "vn": [-90753.844486825, -2.6687106473172017e-26],
                    },
                },
            ],
            "branches": [
                {
                    "id": "line",
                    "currents1": {"ia": [0.0, 0.0], "ib": [0.0, 0.0], "ic": [0.0, 0.0], "in": [0.0, 0.0]},
                    "currents2": {"ia": [0.0, 0.0], "ib": [0.0, 0.0], "ic": [0.0, 0.0], "in": [0.0, 0.0]},
                }
            ],
            "loads": [
                {"id": "load", "currents": {"ia": [0.0, 0.0], "ib": [0.0, 0.0], "ic": [0.0, 0.0], "in": [0.0, 0.0]}}
            ],
        }
        m.post(f"{ElectricalNetwork.DEFAULT_BASE_URL}/solve/", status_code=200, json=json_result)
        with pytest.raises(RoseauLoadFlowException) as e:
            en.solve_load_flow(auth=("", ""))
        assert "The load flow did not converge after 50 iterations" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.NO_LOAD_FLOW_CONVERGENCE

        # Bad request
        json_result = {"msg": "Error while parsing the provided JSON", "code": "parse_error"}
        m.post(f"{ElectricalNetwork.DEFAULT_BASE_URL}/solve/", status_code=400, json=json_result)
        with pytest.raises(RoseauLoadFlowException) as e:
            en.solve_load_flow(auth=("", ""))
        assert "There is a problem in the request" in e.value.args[0]
        assert "Error while parsing the provided JSON" in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_REQUEST

        # Authentication fail
        json_result = {"detail": "not_authenticated"}
        m.post(f"{ElectricalNetwork.DEFAULT_BASE_URL}/solve/", status_code=401, json=json_result)
        with pytest.raises(RoseauLoadFlowException) as e:
            en.solve_load_flow(auth=("", ""))
        assert "Authentication failed." in e.value.args[0]
        assert e.value.args[1] == RoseauLoadFlowExceptionCode.BAD_REQUEST
