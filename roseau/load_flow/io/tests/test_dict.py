import numpy as np
import pytest
from shapely import Point

from roseau.load_flow import Line
from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dict import v0_to_v1_converter
from roseau.load_flow.models import (
    AbstractLoad,
    Bus,
    Ground,
    LineParameters,
    PotentialRef,
    PowerLoad,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork


def test_to_dict():
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    p_ref = PotentialRef("pref", element=ground)
    vs = VoltageSource("vs", source_bus, phases="abcn", voltages=voltages)

    # Same id, different line parameters -> fail
    lp1 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex))
    lp2 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex) * 1.1)

    line1 = Line("line1", source_bus, load_bus, phases="abcn", ground=ground, parameters=lp1, length=10)
    line2 = Line("line2", source_bus, load_bus, phases="abcn", ground=ground, parameters=lp2, length=10)
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        branches=[line1, line2],
        loads=[],
        sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are multiple line parameters with id 'test'" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_LINE_PARAMETERS_DUPLICATES

    # Same id, same line parameters -> ok
    lp2 = LineParameters("test", z_line=np.eye(4, dtype=complex), y_shunt=np.eye(4, dtype=complex))
    line2.parameters = lp2
    en.to_dict()

    # Same id, different transformer parameters -> fail
    ground = Ground("ground")
    vn = 400 / np.sqrt(3)
    voltages = [vn, vn * np.exp(-2 / 3 * np.pi * 1j), vn * np.exp(2 / 3 * np.pi * 1j)]
    source_bus = Bus(id="source", phases="abcn")
    load_bus = Bus(id="load bus", phases="abcn")
    ground.connect(load_bus)
    ground.connect(source_bus)
    p_ref = PotentialRef("pref", element=ground)
    vs = VoltageSource("vs", source_bus, phases="abcn", voltages=voltages)

    # Same id, different transformer parameters -> fail
    tp1 = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    tp2 = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=200 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer1 = Transformer(id="Transformer1", bus1=source_bus, bus2=load_bus, parameters=tp1)
    transformer2 = Transformer(id="Transformer2", bus1=source_bus, bus2=load_bus, parameters=tp2)
    en = ElectricalNetwork(
        buses=[source_bus, load_bus],
        branches=[transformer1, transformer2],
        loads=[],
        sources=[vs],
        grounds=[ground],
        potential_refs=[p_ref],
    )
    with pytest.raises(RoseauLoadFlowException) as e:
        en.to_dict()
    assert "There are multiple transformer parameters with id 't'" in e.value.msg
    assert e.value.code == RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_PARAMETERS_DUPLICATES

    # Same id, same transformer parameters -> ok
    tp2 = TransformerParameters(
        "t", windings="Dyn11", uhv=20000, ulv=400, sn=160 * 1e3, p0=460, i0=2.3 / 100, psc=2350, vsc=4 / 100
    )
    transformer2.parameters = tp2
    en.to_dict()


def test_v0_to_v1_converter(monkeypatch):
    # Do not change `dict_v0` or the network manually, add/update the converters until the test passes

    # Test with floating neutral (monkeypatch the whole test function)
    monkeypatch.setattr(AbstractLoad, "_floating_neutral_allowed", True)
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
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dd0",
            },
            {
                "name": "160kVA_Dd6",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dd6",
            },
            {
                "name": "160kVA_Dyn11",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dyn11",
            },
            {
                "name": "160kVA_Dyn5",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dyn5",
            },
            {
                "name": "160kVA_Dzn0",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dzn0",
            },
            {
                "name": "160kVA_Dzn6",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "dzn6",
            },
            {
                "name": "160kVA_Yd11",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yd11",
            },
            {
                "name": "160kVA_Yd5",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yd5",
            },
            {
                "name": "160kVA_Yyn0",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yyn0",
            },
            {
                "name": "160kVA_Yyn6",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yyn6",
            },
            {
                "name": "160kVA_Yzn11",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "i0": 0.023,
                "p0": 460.0,
                "psc": 2350.0,
                "vsc": 0.04,
                "type": "yzn11",
            },
            {
                "name": "160kVA_Yzn5",
                "sn": 160000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
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
        1: Bus(1, phases="abcn", geometry=Point(0.0, 0.0)),
        2: Bus(2, phases="abc", geometry=Point(0.0, 1.0)),
        3: Bus(3, phases="abcn", geometry=Point(0.0, 1.0)),
        4: Bus(4, phases="abcn", geometry=Point(0.0, 1.0)),
        5: Bus(5, phases="abcn", geometry=Point(0.0, 1.0)),
        6: Bus(6, phases="abc", geometry=Point(0.0, 1.0)),
        7: Bus(7, phases="abcn", geometry=Point(0.0, 1.0)),
        8: Bus(8, phases="abc", geometry=Point(0.0, 1.0)),
        9: Bus(9, phases="abcn", geometry=Point(0.0, 1.0)),
        10: Bus(10, phases="abcn", geometry=Point(0.0, 1.0)),
        11: Bus(11, phases="abcn", geometry=Point(0.0, 1.0)),
        12: Bus(12, phases="abc", geometry=Point(0.0, 1.0)),
        13: Bus(13, phases="abcn", geometry=Point(0.0, 1.0)),
    }

    # Grounds and potential references
    ground = Ground("ground")
    for bus_id in (1, 3, 4, 5, 7, 9, 10, 11, 13):
        ground.connect(buses[bus_id])
    potential_refs = [
        PotentialRef("pref", ground),
        PotentialRef("tr12", buses[2]),
        PotentialRef("tr56", buses[6]),
        PotentialRef("tr78", buses[8]),
        PotentialRef("tr1112", buses[12]),
    ]

    # Sources and loads
    vs = VoltageSource(
        1,
        buses[1],
        voltages=[
            11547.005383792515 + 0.0j,
            -5773.502691896258 + -10000.000000179687j,
            -5773.502691896258 + 10000.000000179687j,
        ],
        phases="abcn",
    )
    loads = [
        PowerLoad(
            1,
            bus=buses[2],
            phases="abcn",
            powers=[
                41916.482229647016 + 20958.241114823508j,
                41916.482230776804 + 20958.2411153884j,
                41916.4822307768 + 20958.241115388402j,
            ],
        ),
        PowerLoad(
            2,
            bus=buses[3],
            phases="abcn",
            powers=[
                40459.7989783205 + 20229.89948916025j,
                40459.79897941102 + 20229.89948970551j,
                40459.79897941102 + 20229.89948970551j,
            ],
        ),
        PowerLoad(
            3,
            bus=buses[4],
            phases="abcn",
            powers=[
                37922.04164877094 + 18961.020824385465j,
                37922.04164985974 + 18961.020824929874j,
                37922.04164980375 + 18961.02082490188j,
            ],
        ),
        PowerLoad(
            4,
            bus=buses[5],
            phases="abcn",
            powers=[
                40459.798978684 + 20229.899489342002j,
                40459.79897977451 + 20229.89948988726j,
                40459.798978684004 + 20229.899489342002j,
            ],
        ),
        PowerLoad(
            5,
            bus=buses[6],
            phases="abcn",
            powers=[
                41916.48223002361 + 20958.24111501181j,
                41916.4822311534 + 20958.241115576697j,
                41916.48223002363 + 20958.241115011813j,
            ],
        ),
        PowerLoad(
            6,
            bus=buses[7],
            phases="abcn",
            powers=[
                40932.79932474136 + 20466.399662370677j,
                40932.79932583017 + 20466.39966291509j,
                40932.79932479737 + 20466.39966239868j,
            ],
        ),
        PowerLoad(
            7,
            bus=buses[8],
            phases="abcn",
            powers=[
                41916.482229647016 + 20958.241114823508j,
                41916.482230776804 + 20958.241115388402j,
                41916.4822307768 + 20958.241115388402j,
            ],
        ),
        PowerLoad(
            8,
            bus=buses[9],
            phases="abcn",
            powers=[
                40459.79897832049 + 20229.899489160252j,
                40459.79897941102 + 20229.89948970551j,
                40459.79897941101 + 20229.899489705513j,
            ],
        ),
        PowerLoad(
            9,
            bus=buses[10],
            phases="abcn",
            powers=[
                37922.04164877094 + 18961.020824385465j,
                37922.04164985973 + 18961.020824929878j,
                37922.04164980376 + 18961.02082490188j,
            ],
        ),
        PowerLoad(
            10,
            bus=buses[11],
            phases="abcn",
            powers=[
                40459.798978684 + 20229.899489342002j,
                40459.79897977452 + 20229.899489887266j,
                40459.798978684004 + 20229.899489342002j,
            ],
        ),
        PowerLoad(
            11,
            bus=buses[12],
            phases="abcn",
            powers=[
                41916.48223002361 + 20958.24111501181j,
                41916.4822311534 + 20958.241115576693j,
                41916.48223002362 + 20958.241115011817j,
            ],
        ),
        PowerLoad(
            12,
            bus=buses[13],
            phases="abcn",
            powers=[
                40932.79932474137 + 20466.399662370684j,
                40932.79932583017 + 20466.399662915086j,
                40932.799324797365 + 20466.399662398682j,
            ],
        ),
    ]

    # Branches
    tp = {
        "160kVA_Dd0": TransformerParameters(
            id="160kVA_Dd0",
            windings="dd0",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dd6": TransformerParameters(
            id="160kVA_Dd6",
            windings="dd6",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dyn11": TransformerParameters(
            id="160kVA_Dyn11",
            windings="dyn11",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dyn5": TransformerParameters(
            id="160kVA_Dyn5",
            windings="dyn5",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dzn0": TransformerParameters(
            id="160kVA_Dzn0",
            windings="dzn0",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Dzn6": TransformerParameters(
            id="160kVA_Dzn6",
            windings="dzn6",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yd11": TransformerParameters(
            id="160kVA_Yd11",
            windings="yd11",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yd5": TransformerParameters(
            id="160kVA_Yd5",
            windings="yd5",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yyn0": TransformerParameters(
            id="160kVA_Yyn0",
            windings="yyn0",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yyn6": TransformerParameters(
            id="160kVA_Yyn6",
            windings="yyn6",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yzn11": TransformerParameters(
            id="160kVA_Yzn11",
            windings="yzn11",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
        "160kVA_Yzn5": TransformerParameters(
            id="160kVA_Yzn5",
            windings="yzn5",
            sn=160000.0,
            uhv=20000.0,
            ulv=400.0,
            i0=0.023,
            p0=460.0,
            psc=2350.0,
            vsc=0.04,
        ),
    }
    p = Point(0.0, 0.5)
    branches = [
        Transformer(
            "tr1", buses[1], buses[2], phases1="abc", phases2="abc", parameters=tp["160kVA_Dd0"], tap=1, geometry=p
        ),
        Transformer(
            "tr2", buses[1], buses[3], phases1="abcn", phases2="abcn", parameters=tp["160kVA_Yyn0"], tap=1, geometry=p
        ),
        Transformer(
            "tr3", buses[1], buses[4], phases1="abc", phases2="abcn", parameters=tp["160kVA_Dzn0"], tap=1, geometry=p
        ),
        Transformer(
            "tr4", buses[1], buses[5], phases1="abc", phases2="abcn", parameters=tp["160kVA_Dyn11"], tap=1, geometry=p
        ),
        Transformer(
            "tr5", buses[1], buses[6], phases1="abcn", phases2="abc", parameters=tp["160kVA_Yd11"], tap=1, geometry=p
        ),
        Transformer(
            "tr6", buses[1], buses[7], phases1="abcn", phases2="abcn", parameters=tp["160kVA_Yzn11"], tap=1, geometry=p
        ),
        Transformer(
            "tr7", buses[1], buses[8], phases1="abc", phases2="abc", parameters=tp["160kVA_Dd6"], tap=1, geometry=p
        ),
        Transformer(
            "tr8", buses[1], buses[9], phases1="abcn", phases2="abcn", parameters=tp["160kVA_Yyn6"], tap=1, geometry=p
        ),
        Transformer(
            "tr9", buses[1], buses[10], phases1="abc", phases2="abcn", parameters=tp["160kVA_Dzn6"], tap=1, geometry=p
        ),
        Transformer(
            "tr10", buses[1], buses[11], phases1="abc", phases2="abcn", parameters=tp["160kVA_Dyn5"], tap=1, geometry=p
        ),
        Transformer(
            "tr11", buses[1], buses[12], phases1="abcn", phases2="abc", parameters=tp["160kVA_Yd5"], tap=1, geometry=p
        ),
        Transformer(
            "tr12", buses[1], buses[13], phases1="abcn", phases2="abcn", parameters=tp["160kVA_Yzn5"], tap=1, geometry=p
        ),
    ]

    net = ElectricalNetwork(
        buses=buses,
        branches=branches,
        loads=loads,
        sources=[vs],
        grounds=[ground],
        potential_refs=potential_refs,
    )

    net_dict = net.to_dict()
    expected_dict = dict_v0
    expected_dict = v0_to_v1_converter(expected_dict)
    # Uncomment the following lines as needed when new versions are added
    # expected_dict = v1_to_v2_converter(expected_dict)
    # expected_dict = v2_to_v3_converter(expected_dict)
    assert net_dict == expected_dict
