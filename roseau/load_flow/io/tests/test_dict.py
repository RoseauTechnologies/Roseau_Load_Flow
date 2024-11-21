import copy

import numpy as np
import pytest
from shapely import LineString, Point

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dict import v0_to_v1_converter, v1_to_v2_converter, v2_to_v3_converter
from roseau.load_flow.models import (
    Bus,
    Ground,
    Line,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow.typing import JsonDict
from roseau.load_flow.utils import Insulator, LineType, Material


def test_to_dict():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    source_bus = Bus(id="source", phases="abcn", geometry=Point(0.0, 0.0), min_voltage_level=0.9, nominal_voltage=400)
    load_bus = Bus(id="load bus", phases="abcn", geometry=Point(0.0, 1.0), max_voltage_level=1.1, nominal_voltage=400)
    ground.connect(load_bus)
    p_ref = PotentialRef(id="pref", element=ground)
    vs = VoltageSource(id="vs", bus=source_bus, phases="abcn", voltages=vn)

    # Same id, different line parameters -> fail
    lp1 = LineParameters(
        id="test",
        z_line=np.eye(4, dtype=complex),
        y_shunt=np.eye(4, dtype=complex),
        line_type=LineType.UNDERGROUND,
        materials=Material.AA,
        insulators=Insulator.PVC,
        sections=120,
    )
    lp2 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex) * 1.1)

    geom = LineString([(0.0, 0.0), (0.0, 1.0)])
    line1 = Line(
        id="line1",
        bus1=source_bus,
        bus2=load_bus,
        phases="abcn",
        ground=ground,
        parameters=lp1,
        length=10,
        geometry=geom,
    )
    line2 = Line(
        id="line2",
        bus1=source_bus,
        bus2=load_bus,
        phases="abcn",
        ground=ground,
        parameters=lp2,
        length=10,
        geometry=geom,
    )
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[line1, line2],
        transformers=[],
        switches=[],
        loads=[],
        sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
    )

    # Same id, different line parameters -> fail
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict(include_results=False)
    assert "There are multiple line parameters with id 'test'" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_LINE_PARAMETERS_DUPLICATES

    # Same id, same line parameters -> ok
    lp2 = LineParameters(
        id="test",
        z_line=np.eye(4, dtype=complex),
        y_shunt=np.eye(4, dtype=complex),
        line_type=LineType.UNDERGROUND,
        materials=Material.AA,
        insulators=Insulator.PVC,
        sections=120,
    )
    line2.parameters = lp2
    en.to_dict(include_results=False)

    # Dict content
    line2.parameters = lp1
    lp1.ampacities = 1000
    res = en.to_dict(include_results=False)
    res_bus0, res_bus1 = res["buses"]
    res_line0, res_line1 = res["lines"]
    assert "geometry" in res_bus0
    assert "geometry" in res_bus1
    assert "geometry" in res_line0
    assert "geometry" in res_line1
    assert np.isclose(res_bus0["nominal_voltage"], 400.0)
    assert np.isclose(res_bus0["min_voltage_level"], 0.9)
    assert np.isclose(res_bus1["nominal_voltage"], 400.0)
    assert np.isclose(res_bus1["max_voltage_level"], 1.1)
    lp_dict = res["lines_params"][0]
    assert np.allclose(lp_dict["ampacities"], 1000)
    assert lp_dict["line_type"] == "UNDERGROUND"
    assert lp_dict["materials"] == ["AA"] * 4
    assert lp_dict["insulators"] == ["PVC"] * 4
    assert np.allclose(lp_dict["sections"], 120)
    assert "results" not in res_bus0
    assert "results" not in res_bus1
    assert "results" not in res_line0
    assert "results" not in res_line1

    # Same id, different transformer parameters -> fail
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    geom = Point(0.0, 0.0)
    source_bus = Bus(id="source", phases="abcn", geometry=geom)
    load_bus = Bus(id="load bus", phases="abcn", geometry=geom)
    ground.connect(load_bus)
    ground.connect(source_bus)
    p_ref = PotentialRef(id="pref", element=ground)
    vs = VoltageSource(id="vs", bus=source_bus, phases="abcn", voltages=vn)

    # Same id, different transformer parameters -> fail
    tp1 = TransformerParameters.from_open_and_short_circuit_tests(
        id="t", type="Dyn11", up=20000, us=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    tp2 = TransformerParameters.from_open_and_short_circuit_tests(
        id="t", type="Dyn11", up=20000, us=400, sn=200 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer1 = Transformer(id="Transformer1", bus1=source_bus, bus2=load_bus, parameters=tp1, geometry=geom)
    transformer2 = Transformer(id="Transformer2", bus1=source_bus, bus2=load_bus, parameters=tp2, geometry=geom)
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        lines=[],
        transformers=[transformer1, transformer2],
        switches=[],
        loads=[],
        sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
    )

    # Same id, different transformer parameters -> fail
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict(include_results=False)
    assert "There are multiple transformer parameters with id 't'" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_PARAMETERS_DUPLICATES

    # Same id, same transformer parameters -> ok
    tp2 = TransformerParameters.from_open_and_short_circuit_tests(
        id="t", type="Dyn11", up=20000, us=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer2.parameters = tp2
    en.to_dict(include_results=False)

    # Dict content
    transformer2.parameters = tp1
    res = en.to_dict(include_results=False)
    assert "geometry" in res["buses"][0]
    assert "geometry" in res["buses"][1]
    assert "geometry" in res["transformers"][0]
    assert "geometry" in res["transformers"][1]


def test_v0_to_v3_converter():
    # Do not change `dict_v0` or the network manually, add/update the converters until the test passes

    dict_v0 = {
        "buses": [
            {
                "id": 1,
                "type": "slack",
                "loads": [],
                "voltages": {
                    "va": [11547.005383792515, 0.0],
                    "vb": [-5773.502691896258, -10000.000000179687],
                    "vc": [-5773.502691896258, 10000.000000179687],
                },
                "geometry": "POINT (0 0)",
            },
            {
                "id": 2,
                "type": "bus",
                "loads": [
                    {
                        "id": 1,
                        "function": "ys",
                        "powers": {
                            "sa": [41916.482229647016, 20958.241114823508],
                            "sb": [41916.482230776804, 20958.2411153884],
                            "sc": [41916.4822307768, 20958.241115388402],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 3,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 2,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [40459.7989783205, 20229.89948916025],
                            "sb": [40459.79897941102, 20229.89948970551],
                            "sc": [40459.79897941102, 20229.89948970551],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 4,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 3,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [37922.04164877094, 18961.020824385465],
                            "sb": [37922.04164985974, 18961.020824929874],
                            "sc": [37922.04164980375, 18961.02082490188],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 5,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 4,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [40459.798978684, 20229.899489342002],
                            "sb": [40459.79897977451, 20229.89948988726],
                            "sc": [40459.798978684004, 20229.899489342002],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 6,
                "type": "bus",
                "loads": [
                    {
                        "id": 5,
                        "function": "ys",
                        "powers": {
                            "sa": [41916.48223002361, 20958.24111501181],
                            "sb": [41916.4822311534, 20958.241115576697],
                            "sc": [41916.48223002363, 20958.241115011813],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 7,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 6,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [40932.79932474136, 20466.399662370677],
                            "sb": [40932.79932583017, 20466.39966291509],
                            "sc": [40932.79932479737, 20466.39966239868],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 8,
                "type": "bus",
                "loads": [
                    {
                        "id": 7,
                        "function": "ys",
                        "powers": {
                            "sa": [41916.482229647016, 20958.241114823508],
                            "sb": [41916.482230776804, 20958.241115388402],
                            "sc": [41916.4822307768, 20958.241115388402],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 9,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 8,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [40459.79897832049, 20229.899489160252],
                            "sb": [40459.79897941102, 20229.89948970551],
                            "sc": [40459.79897941101, 20229.899489705513],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 10,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 9,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [37922.04164877094, 18961.020824385465],
                            "sb": [37922.04164985973, 18961.020824929878],
                            "sc": [37922.04164980376, 18961.02082490188],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 11,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 10,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [40459.798978684, 20229.899489342002],
                            "sb": [40459.79897977452, 20229.899489887266],
                            "sc": [40459.798978684004, 20229.899489342002],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 12,
                "type": "bus",
                "loads": [
                    {
                        "id": 11,
                        "function": "ys",
                        "powers": {
                            "sa": [41916.48223002361, 20958.24111501181],
                            "sb": [41916.4822311534, 20958.241115576693],
                            "sc": [41916.48223002362, 20958.241115011817],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
            {
                "id": 13,
                "type": "bus_neutral",
                "loads": [
                    {
                        "id": 12,
                        "function": "ys_neutral",
                        "powers": {
                            "sa": [40932.79932474137, 20466.399662370684],
                            "sb": [40932.79932583017, 20466.399662915086],
                            "sc": [40932.799324797365, 20466.399662398682],
                        },
                    }
                ],
                "geometry": "POINT (0 1)",
            },
        ],
        "branches": [
            {
                "id": "tr1",
                "bus1": 1,
                "bus2": 2,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Dd0",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr2",
                "bus1": 1,
                "bus2": 3,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Yyn0",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr3",
                "bus1": 1,
                "bus2": 4,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Dzn0",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr4",
                "bus1": 1,
                "bus2": 5,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Dyn11",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr5",
                "bus1": 1,
                "bus2": 6,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Yd11",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr6",
                "bus1": 1,
                "bus2": 7,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Yzn11",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr7",
                "bus1": 1,
                "bus2": 8,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Dd6",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr8",
                "bus1": 1,
                "bus2": 9,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Yyn6",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr9",
                "bus1": 1,
                "bus2": 10,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Dzn6",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr10",
                "bus1": 1,
                "bus2": 11,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Dyn5",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr11",
                "bus1": 1,
                "bus2": 12,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Yd5",
                "tap": 1.0,
                "type": "transformer",
            },
            {
                "id": "tr12",
                "bus1": 1,
                "bus2": 13,
                "geometry": "POINT (0 0.5)",
                "type_name": "160kVA_Yzn5",
                "tap": 1.0,
                "type": "transformer",
            },
        ],
        "line_types": [],
        "transformer_types": [
            {
                "name": "160kVA_Dd0",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dd0",
            },
            {
                "name": "160kVA_Dd6",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dd6",
            },
            {
                "name": "160kVA_Dyn11",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dyn11",
            },
            {
                "name": "160kVA_Dyn5",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dyn5",
            },
            {
                "name": "160kVA_Dzn0",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dzn0",
            },
            {
                "name": "160kVA_Dzn6",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dzn6",
            },
            {
                "name": "160kVA_Yd11",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yd11",
            },
            {
                "name": "160kVA_Yd5",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yd5",
            },
            {
                "name": "160kVA_Yyn0",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yyn0",
            },
            {
                "name": "160kVA_Yyn6",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yyn6",
            },
            {
                "name": "160kVA_Yzn11",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yzn11",
            },
            {
                "name": "160kVA_Yzn5",
                "sn": 160000.0,
                "up": 20000.0,
                "us": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yzn5",
            },
        ],
    }

    # Buses
    buses = {
        1: Bus(id=1, phases="abcn", geometry=Point(0.0, 0.0)),
        2: Bus(id=2, phases="abc", geometry=Point(0.0, 1.0)),
        3: Bus(id=3, phases="abcn", geometry=Point(0.0, 1.0)),
        4: Bus(id=4, phases="abcn", geometry=Point(0.0, 1.0)),
        5: Bus(id=5, phases="abcn", geometry=Point(0.0, 1.0)),
        6: Bus(id=6, phases="abc", geometry=Point(0.0, 1.0)),
        7: Bus(id=7, phases="abcn", geometry=Point(0.0, 1.0)),
        8: Bus(id=8, phases="abc", geometry=Point(0.0, 1.0)),
        9: Bus(id=9, phases="abcn", geometry=Point(0.0, 1.0)),
        10: Bus(id=10, phases="abcn", geometry=Point(0.0, 1.0)),
        11: Bus(id=11, phases="abcn", geometry=Point(0.0, 1.0)),
        12: Bus(id=12, phases="abc", geometry=Point(0.0, 1.0)),
        13: Bus(id=13, phases="abcn", geometry=Point(0.0, 1.0)),
    }

    # Grounds and potential references
    ground = Ground("ground")
    for bus_id in (1, 3, 4, 5, 7, 9, 10, 11, 13):
        ground.connect(buses[bus_id])
    potential_refs = [
        PotentialRef(id="pref", element=ground),
        PotentialRef(id="tr12", element=buses[2]),
        PotentialRef(id="tr56", element=buses[6]),
        PotentialRef(id="tr78", element=buses[8]),
        PotentialRef(id="tr1112", element=buses[12]),
    ]

    # Sources and loads
    vs = VoltageSource(
        id=1,
        bus=buses[1],
        voltages=[
            11547.005383792515 + 0.0j,
            -5773.502691896258 + -10000.000000179687j,
            -5773.502691896258 + 10000.000000179687j,
        ],
        phases="abcn",
    )
    loads = [
        PowerLoad(
            id=1,
            bus=buses[2],
            phases="abcn",
            powers=[
                41916.482229647016 + 20958.241114823508j,
                41916.482230776804 + 20958.2411153884j,
                41916.4822307768 + 20958.241115388402j,
            ],
        ),
        PowerLoad(
            id=2,
            bus=buses[3],
            phases="abcn",
            powers=[
                40459.7989783205 + 20229.89948916025j,
                40459.79897941102 + 20229.89948970551j,
                40459.79897941102 + 20229.89948970551j,
            ],
        ),
        PowerLoad(
            id=3,
            bus=buses[4],
            phases="abcn",
            powers=[
                37922.04164877094 + 18961.020824385465j,
                37922.04164985974 + 18961.020824929874j,
                37922.04164980375 + 18961.02082490188j,
            ],
        ),
        PowerLoad(
            id=4,
            bus=buses[5],
            phases="abcn",
            powers=[
                40459.798978684 + 20229.899489342002j,
                40459.79897977451 + 20229.89948988726j,
                40459.798978684004 + 20229.899489342002j,
            ],
        ),
        PowerLoad(
            id=5,
            bus=buses[6],
            phases="abcn",
            powers=[
                41916.48223002361 + 20958.24111501181j,
                41916.4822311534 + 20958.241115576697j,
                41916.48223002363 + 20958.241115011813j,
            ],
        ),
        PowerLoad(
            id=6,
            bus=buses[7],
            phases="abcn",
            powers=[
                40932.79932474136 + 20466.399662370677j,
                40932.79932583017 + 20466.39966291509j,
                40932.79932479737 + 20466.39966239868j,
            ],
        ),
        PowerLoad(
            id=7,
            bus=buses[8],
            phases="abcn",
            powers=[
                41916.482229647016 + 20958.241114823508j,
                41916.482230776804 + 20958.241115388402j,
                41916.4822307768 + 20958.241115388402j,
            ],
        ),
        PowerLoad(
            id=8,
            bus=buses[9],
            phases="abcn",
            powers=[
                40459.79897832049 + 20229.899489160252j,
                40459.79897941102 + 20229.89948970551j,
                40459.79897941101 + 20229.899489705513j,
            ],
        ),
        PowerLoad(
            id=9,
            bus=buses[10],
            phases="abcn",
            powers=[
                37922.04164877094 + 18961.020824385465j,
                37922.04164985973 + 18961.020824929878j,
                37922.04164980376 + 18961.02082490188j,
            ],
        ),
        PowerLoad(
            id=10,
            bus=buses[11],
            phases="abcn",
            powers=[
                40459.798978684 + 20229.899489342002j,
                40459.79897977452 + 20229.899489887266j,
                40459.798978684004 + 20229.899489342002j,
            ],
        ),
        PowerLoad(
            id=11,
            bus=buses[12],
            phases="abcn",
            powers=[
                41916.48223002361 + 20958.24111501181j,
                41916.4822311534 + 20958.241115576693j,
                41916.48223002362 + 20958.241115011817j,
            ],
        ),
        PowerLoad(
            id=12,
            bus=buses[13],
            phases="abcn",
            powers=[
                40932.79932474137 + 20466.399662370684j,
                40932.79932583017 + 20466.399662915086j,
                40932.799324797365 + 20466.399662398682j,
            ],
        ),
    ]

    # Transformers
    tp = {
        "160kVA_Dd0": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Dd0",
            type="dd0",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dd6": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Dd6",
            type="dd6",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dyn11": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Dyn11",
            type="dyn11",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dyn5": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Dyn5",
            type="dyn5",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dzn0": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Dzn0",
            type="dzn0",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dzn6": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Dzn6",
            type="dzn6",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yd11": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Yd11",
            type="yd11",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yd5": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Yd5",
            type="yd5",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yyn0": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Yyn0",
            type="yyn0",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yyn6": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Yyn6",
            type="yyn6",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yzn11": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Yzn11",
            type="yzn11",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yzn5": TransformerParameters.from_open_and_short_circuit_tests(
            id="160kVA_Yzn5",
            type="yzn5",
            sn=160000.0,
            up=20000.0,
            us=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
    }
    p = Point(0.0, 0.5)
    transformers = [
        Transformer(
            id="tr1",
            bus1=buses[1],
            bus2=buses[2],
            phases1="abc",
            phases2="abc",
            parameters=tp["160kVA_Dd0"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr2",
            bus1=buses[1],
            bus2=buses[3],
            phases1="abcn",
            phases2="abcn",
            parameters=tp["160kVA_Yyn0"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr3",
            bus1=buses[1],
            bus2=buses[4],
            phases1="abc",
            phases2="abcn",
            parameters=tp["160kVA_Dzn0"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr4",
            bus1=buses[1],
            bus2=buses[5],
            phases1="abc",
            phases2="abcn",
            parameters=tp["160kVA_Dyn11"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr5",
            bus1=buses[1],
            bus2=buses[6],
            phases1="abcn",
            phases2="abc",
            parameters=tp["160kVA_Yd11"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr6",
            bus1=buses[1],
            bus2=buses[7],
            phases1="abcn",
            phases2="abcn",
            parameters=tp["160kVA_Yzn11"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr7",
            bus1=buses[1],
            bus2=buses[8],
            phases1="abc",
            phases2="abc",
            parameters=tp["160kVA_Dd6"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr8",
            bus1=buses[1],
            bus2=buses[9],
            phases1="abcn",
            phases2="abcn",
            parameters=tp["160kVA_Yyn6"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr9",
            bus1=buses[1],
            bus2=buses[10],
            phases1="abc",
            phases2="abcn",
            parameters=tp["160kVA_Dzn6"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr10",
            bus1=buses[1],
            bus2=buses[11],
            phases1="abc",
            phases2="abcn",
            parameters=tp["160kVA_Dyn5"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr11",
            bus1=buses[1],
            bus2=buses[12],
            phases1="abcn",
            phases2="abc",
            parameters=tp["160kVA_Yd5"],
            tap=1,
            geometry=p,
        ),
        Transformer(
            id="tr12",
            bus1=buses[1],
            bus2=buses[13],
            phases1="abcn",
            phases2="abcn",
            parameters=tp["160kVA_Yzn5"],
            tap=1,
            geometry=p,
        ),
    ]

    net = ElectricalNetwork(
        buses=buses,
        lines=[],
        transformers=transformers,
        switches=[],
        loads=loads,
        sources=[vs],
        grounds=[ground],
        potential_refs=potential_refs,
    )

    net_dict = net.to_dict(include_results=False)
    expected_dict = dict_v0
    expected_dict = v0_to_v1_converter(expected_dict)
    expected_dict = v1_to_v2_converter(expected_dict)
    expected_dict = v2_to_v3_converter(expected_dict)
    # Uncomment the following lines as needed when new versions are added
    # expected_dict = v2_to_v3_converter(expected_dict)
    # expected_dict = v3_to_v4_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)


def test_v1_to_v2_converter():
    # Do not change `dict_v1` or the network manually, add/update the converters until the test passes

    dict_v1 = {
        "version": 1,
        "grounds": [],
        "potential_refs": [
            {
                "id": "pref",
                "bus": 1,
                "phases": None,
                "results": {"current": [-7.771563289958464e-16, -2.220444725761333e-16]},
            }
        ],
        "buses": [
            {
                "id": 1,
                "phases": "abc",
                "geometry": {"type": "Point", "coordinates": (0.0, 0.0)},
                "results": {
                    "potentials": [
                        [5773.502691896258, -3333.3333333932287],
                        [-5773.502691896258, -3333.3333333932287],
                        [9.888685758712307e-24, 6666.666666786457],
                    ]
                },
            },
            {
                "id": 2,
                "phases": "abc",
                "geometry": {"type": "Point", "coordinates": (0.0, 1.0)},
                "results": {
                    "potentials": [
                        [5772.521060368325, -3330.7830499173137],
                        [-5770.803265855299, -3333.7583572908047],
                        [-1.7177945130259364, 6664.5414072081185],
                    ]
                },
            },
        ],
        "branches": [
            {
                "id": 1,
                "type": "line",
                "phases1": "abc",
                "phases2": "abc",
                "bus1": 1,
                "bus2": 2,
                "geometry": {"type": "LineString", "coordinates": ((0.0, 0.0), (1.0, 0.0))},
                "results": {
                    "currents1": [
                        [2.804661508377779, -7.286524216899904],
                        [-7.712645831309471, 1.214353993074318],
                        [4.907984322931247, 6.072170223825586],
                    ],
                    "currents2": [
                        [-2.804661508377779, 7.286524216899904],
                        [7.712645831309471, -1.214353993074318],
                        [-4.907984322931247, -6.072170223825586],
                    ],
                },
                "length": 1.0,
                "params_id": "lp",
            }
        ],
        "loads": [
            {
                "id": 1,
                "bus": 2,
                "phases": "abc",
                "powers": [
                    [38000.0, 12489.9959967968],
                    [38000.0, 12489.9959967968],
                    [38000.0, 12489.9959967968],
                ],
                "results": {
                    "currents": [
                        [-0.9366300237736715, -1.623256890969888],
                        [-0.9374666925612338, 1.6227738400201663],
                        [1.8740967163349054, 0.00048305094972167506],
                    ],
                    "powers": [
                        [-0.0, 12489.9959967968],
                        [-0.0, 12489.9959967968],
                        [-0.0, 12489.9959967968],
                    ],
                },
                "flexible_params": [
                    {
                        "control_p": {
                            "type": "p_max_u_consumption",
                            "u_min": 18000,
                            "u_down": 19000,
                            "alpha": 1000.0,
                            "epsilon": 1e-08,
                        },
                        "control_q": {"type": "constant"},
                        "projection": {"type": "euclidean", "alpha": 1000.0, "epsilon": 1e-08},
                        "s_max": 45000.0,
                    },
                    {
                        "control_p": {
                            "type": "p_max_u_consumption",
                            "u_min": 18000,
                            "u_down": 19000,
                            "alpha": 1000.0,
                            "epsilon": 1e-08,
                        },
                        "control_q": {"type": "constant"},
                        "projection": {"type": "euclidean", "alpha": 1000.0, "epsilon": 1e-08},
                        "s_max": 45000.0,
                    },
                    {
                        "control_p": {
                            "type": "p_max_u_consumption",
                            "u_min": 18000,
                            "u_down": 19000,
                            "alpha": 1000.0,
                            "epsilon": 1e-08,
                        },
                        "control_q": {"type": "constant"},
                        "projection": {"type": "euclidean", "alpha": 1000.0, "epsilon": 1e-08},
                        "s_max": 45000.0,
                    },
                ],
            },
            {
                "id": 2,
                "bus": 2,
                "phases": "abc",
                "powers": [
                    [40459.7989783205, 20229.89948916025],
                    [40459.79897941102, 20229.89948970551],
                    [40459.79897941102, 20229.89948970551],
                ],
                "results": {
                    "currents": [
                        [3.7412915321516125, -5.663267325930873],
                        [-6.775179138747953, -0.40841984694689626],
                        [3.0338876065963407, 6.07168717287777],
                    ]
                },
            },
        ],
        "sources": [
            {
                "id": 1,
                "bus": 1,
                "phases": "abc",
                "voltages": [
                    [11547.005383792515, 0.0],
                    [-5773.502691896258, -10000.000000179687],
                    [-5773.502691896258, 10000.000000179687],
                ],
                "results": {
                    "currents": [
                        [-2.80466150837794, 7.286524216900761],
                        [7.712645831309187, -1.2143539930732696],
                        [-4.907984322931247, -6.0721702238274915],
                    ]
                },
            }
        ],
        "lines_params": [
            {
                "id": "lp",
                "z_line": [
                    [[0.35, 0.0, 0.0], [0.0, 0.35, 0.0], [0.0, 0.0, 0.35]],
                    [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                ],
            }
        ],
        "transformers_params": [],
    }

    # # Buses
    # buses = {
    #     1: Bus(id=1, phases="abc", geometry=Point(0.0, 0.0)),
    #     2: Bus(id=2, phases="abc", geometry=Point(0.0, 1.0)),
    # }
    #
    # # Potential reference
    # potential_ref = PotentialRef(id="pref", element=buses[1])
    #
    # # Sources and loads
    # vs = VoltageSource(
    #     id=1,
    #     bus=buses[1],
    #     voltages=[
    #         11547.005383792515 + 0.0j,
    #         -5773.502691896258 + -10000.000000179687j,
    #         -5773.502691896258 + 10000.000000179687j,
    #     ],
    #     phases="abc",
    # )
    # fp = FlexibleParameter(
    #     control_p=Control.p_max_u_consumption(u_min=18_000, u_down=19_000),
    #     control_q=Control.constant(),
    #     projection=Projection(type="euclidean"),
    #     s_max=45e3,
    # )
    # power = cmath.rect(40e3, math.acos(0.95))
    # loads = [
    #     PowerLoad(id=1, bus=buses[2], phases="abc", powers=[power, power, power], flexible_params=[fp, fp, fp]),
    #     PowerLoad(
    #         id=2,
    #         bus=buses[2],
    #         phases="abc",
    #         powers=[
    #             40459.7989783205 + 20229.89948916025j,
    #             40459.79897941102 + 20229.89948970551j,
    #             40459.79897941102 + 20229.89948970551j,
    #         ],
    #     ),
    # ]
    #
    # line_parameters = LineParameters(id="lp", z_line=0.35 * np.eye(3, dtype=complex))
    # lines = {
    #     1: Line(
    #         id=1,
    #         bus1=buses[1],
    #         bus2=buses[2],
    #         parameters=line_parameters,
    #         length=1.0,
    #         geometry=LineString([(0, 0), (1, 0)]),
    #     )
    # }
    #
    # net = ElectricalNetwork(
    #     buses=buses,
    #     lines=lines,
    #     transformers=[],
    #     switches=[],
    #     loads=loads,
    #     sources=[vs],
    #     grounds=[],
    #     potential_refs=[potential_ref],
    # )

    # Include results=True
    net = ElectricalNetwork.from_dict(data=copy.deepcopy(dict_v1), include_results=True)
    net_dict = net.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v1)
    expected_dict = v1_to_v2_converter(expected_dict)
    expected_dict = v2_to_v3_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)

    # Include results=False
    def _delete(d: JsonDict, k: str) -> JsonDict:
        if k in d:
            d.pop(k)
        return d

    net = ElectricalNetwork.from_dict(data=copy.deepcopy(dict_v1), include_results=False)
    net_dict = net.to_dict(include_results=False)
    dict_v1_without_results = {
        k: [_delete(d=x, k="results") for x in v] if isinstance(v, list) else v
        for k, v in copy.deepcopy(dict_v1).items()
    }
    expected_dict = copy.deepcopy(dict_v1_without_results)
    expected_dict = v1_to_v2_converter(expected_dict)
    expected_dict = v2_to_v3_converter(expected_dict)
    assert_json_close(net_dict, expected_dict)


def test_v2_to_v3_converter(recwarn):
    # Do not change `dict_v2` or the network manually, add/update the converters until the test passes

    dict_v2 = {
        "version": 2,
        "is_multiphase": True,
        "buses": [
            {
                "geometry": {"coordinates": (0.0, 0.0), "type": "Point"},
                "id": 1,
                "max_voltage": 420,
                "min_voltage": 380,
                "phases": "abc",
            },
            {
                "geometry": {"coordinates": (0.0, 1.0), "type": "Point"},
                "id": 2,
                "max_voltage": 420,
                "min_voltage": 380,
                "phases": "abc",
            },
        ],
        "grounds": [],
        "lines": [
            {
                "bus1": 1,
                "bus2": 2,
                "geometry": {"coordinates": ((0.0, 0.0), (1.0, 0.0)), "type": "LineString"},
                "id": 1,
                "length": 1.0,
                "params_id": "lp",
                "phases": "abc",
            }
        ],
        "lines_params": [
            {
                "id": "lp",
                "z_line": [
                    [[0.35, 0.0, 0.0], [0.0, 0.35, 0.0], [0.0, 0.0, 0.35]],
                    [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                ],
            }
        ],
        "loads": [
            {
                "bus": 2,
                "connect_neutral": None,
                "flexible_params": [
                    {
                        "control_p": {
                            "alpha": 1000.0,
                            "epsilon": 1e-08,
                            "type": "p_max_u_consumption",
                            "u_down": 19000,
                            "u_min": 18000,
                        },
                        "control_q": {"type": "constant"},
                        "projection": {"alpha": 1000.0, "epsilon": 1e-08, "type": "euclidean"},
                        "s_max": 45000.0,
                    },
                    {
                        "control_p": {
                            "alpha": 1000.0,
                            "epsilon": 1e-08,
                            "type": "p_max_u_consumption",
                            "u_down": 19000,
                            "u_min": 18000,
                        },
                        "control_q": {"type": "constant"},
                        "projection": {"alpha": 1000.0, "epsilon": 1e-08, "type": "euclidean"},
                        "s_max": 45000.0,
                    },
                    {
                        "control_p": {
                            "alpha": 1000.0,
                            "epsilon": 1e-08,
                            "type": "p_max_u_consumption",
                            "u_down": 19000,
                            "u_min": 18000,
                        },
                        "control_q": {"type": "constant"},
                        "projection": {"alpha": 1000.0, "epsilon": 1e-08, "type": "euclidean"},
                        "s_max": 45000.0,
                    },
                ],
                "id": 1,
                "phases": "abc",
                "powers": [[38000.0, 12489.9959967968], [38000.0, 12489.9959967968], [38000.0, 12489.9959967968]],
                "type": "power",
            },
            {
                "bus": 2,
                "connect_neutral": None,
                "id": 2,
                "phases": "abc",
                "powers": [
                    [40459.7989783205, 20229.89948916025],
                    [40459.79897941102, 20229.89948970551],
                    [40459.79897941102, 20229.89948970551],
                ],
                "type": "power",
            },
        ],
        "potential_refs": [{"bus": 1, "id": "pref", "phases": None}],
        "sources": [
            {
                "bus": 1,
                "connect_neutral": None,
                "id": 1,
                "phases": "abc",
                "voltages": [
                    [11547.005383792515, 0.0],
                    [-5773.502691896258, -10000.000000179687],
                    [-5773.502691896258, 10000.000000179687],
                ],
            }
        ],
        "switches": [],
        "transformers": [],
        "transformers_params": [],
    }

    # # Buses
    # buses = {
    #     1: Bus(
    #         id=1,
    #         phases="abc",
    #         geometry=Point(0.0, 0.0),
    #         nominal_voltage=400,
    #         min_voltage_level=0.95,
    #         max_voltage_level=1.05,
    #     ),
    #     2: Bus(
    #         id=2,
    #         phases="abc",
    #         geometry=Point(0.0, 1.0),
    #         nominal_voltage=400,
    #         min_voltage_level=0.95,
    #         max_voltage_level=1.05,
    #     ),
    # }
    #
    # # Potential reference
    # potential_ref = PotentialRef(id="pref", element=buses[1])
    #
    # # Sources and loads
    # vs = VoltageSource(
    #     id=1,
    #     bus=buses[1],
    #     voltages=[
    #         11547.005383792515 + 0.0j,
    #         -5773.502691896258 + -10000.000000179687j,
    #         -5773.502691896258 + 10000.000000179687j,
    #     ],
    #     phases="abc",
    # )
    # fp = FlexibleParameter(
    #     control_p=Control.p_max_u_consumption(u_min=18_000, u_down=19_000),
    #     control_q=Control.constant(),
    #     projection=Projection(type="euclidean"),
    #     s_max=45e3,
    # )
    # power = cmath.rect(40e3, math.acos(0.95))
    # loads = [
    #     PowerLoad(id=1, bus=buses[2], phases="abc", powers=[power, power, power], flexible_params=[fp, fp, fp]),
    #     PowerLoad(
    #         id=2,
    #         bus=buses[2],
    #         phases="abc",
    #         powers=[
    #             40459.7989783205 + 20229.89948916025j,
    #             40459.79897941102 + 20229.89948970551j,
    #             40459.79897941102 + 20229.89948970551j,
    #         ],
    #     ),
    # ]
    #
    # line_parameters = LineParameters(id="lp", z_line=0.35 * np.eye(3, dtype=complex))
    # lines = {
    #     1: Line(
    #         id=1,
    #         bus1=buses[1],
    #         bus2=buses[2],
    #         parameters=line_parameters,
    #         length=1.0,
    #         geometry=LineString([(0, 0), (1, 0)]),
    #     )
    # }
    #
    # net = ElectricalNetwork(
    #     buses=buses,
    #     lines=lines,
    #     transformers=[],
    #     switches=[],
    #     loads=loads,
    #     sources=[vs],
    #     grounds=[],
    #     potential_refs=[potential_ref],
    # )

    # Include results=True
    net = ElectricalNetwork.from_dict(data=copy.deepcopy(dict_v2), include_results=True)
    net_dict = net.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v2)
    recwarn.clear()
    expected_dict = v2_to_v3_converter(expected_dict)
    assert len(recwarn) == 1
    assert (
        recwarn[0].message.args[0]
        == "Starting with version 0.11.0 of roseau-load-flow (JSON file v3), `min_voltage` and `max_voltage` are "
        "replaced with `min_voltage_level`, `max_voltage_level` and `nominal_voltage`. The found values of "
        "`min_voltage` or `max_voltage` are dropped."
    )
    assert_json_close(net_dict, expected_dict)
