import copy

import pytest

from roseau.load_flow.io.dict import _convert_line_parameters_v2_to_v3, _convert_lines_v2_to_v3, v2_to_v3_converter
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.testing import assert_json_close


def test_v2_to_v3_converter():
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
    with pytest.warns(UserWarning, match=r"Starting with version 0.11.0 of roseau-load-flow \(JSON file v3\), .*"):
        net = ElectricalNetwork.from_dict(data=copy.deepcopy(dict_v2), include_results=True)
    net_dict = net.to_dict(include_results=True)
    expected_dict = copy.deepcopy(dict_v2)
    with pytest.warns(UserWarning, match=r"Starting with version 0.11.0 of roseau-load-flow \(JSON file v3\), .*"):
        expected_dict = v2_to_v3_converter(expected_dict)

    assert_json_close(net_dict, expected_dict)


def test_v2_to_v3_converter_max_loading():
    # Dict v2 (test the max_power -> max_loading conversion)
    # import roseau.load_flow as rlf
    #
    # bus1 = rlf.Bus(id=1, phases="abc")
    # bus2 = rlf.Bus(id=2, phases="abc")
    # data = {
    #     "id": "Yzn11 - 50kVA",
    #     "z2": rlf.Q_(8.64 + 9.444j, "centiohm"),  # Ohm
    #     "ym": rlf.Q_(0.3625 - 2.2206j, "uS"),  # S
    #     "ulv": rlf.Q_(400, "V"),  # V
    #     "uhv": rlf.Q_(20, "kV"),  # V
    #     "sn": rlf.Q_(50, "kVA"),  # VA
    #     "type": "yzn11",
    #     "max_power": rlf.Q_(60, "kVA"),
    # }
    # tp = rlf.TransformerParameters(**data)
    # t = rlf.Transformer(id="t", bus1=bus1, bus2=bus2, parameters=tp)
    # vs = rlf.VoltageSource(id="vs", bus=bus1, voltages=20_000)
    # p_ref = rlf.PotentialRef(id="pref", element=bus1)
    # p_ref2 = rlf.PotentialRef(id="pref2", element=bus2)
    # en = rlf.ElectricalNetwork.from_element(bus1)
    # en.to_json("test_max_power.json")
    dict_v2 = {
        "version": 2,
        "is_multiphase": True,
        "grounds": [],
        "potential_refs": [{"id": "pref", "bus": 1, "phases": None}, {"id": "pref2", "bus": 2, "phases": None}],
        "buses": [{"id": 1, "phases": "abc"}, {"id": 2, "phases": "abc"}],
        "lines": [],
        "transformers": [
            {
                "id": "t",
                "phases1": "abc",
                "phases2": "abc",
                "bus1": 1,
                "bus2": 2,
                "tap": 1.0,
                "params_id": "Yzn11 - 50kVA",
            }
        ],
        "switches": [],
        "loads": [],
        "sources": [
            {
                "id": "vs",
                "bus": 1,
                "phases": "abc",
                "voltages": [
                    [20000.0, 0.0],
                    [-10000.000000000007, -17320.50807568877],
                    [-9999.999999999996, 17320.508075688773],
                ],
                "connect_neutral": None,
            }
        ],
        "lines_params": [],
        "transformers_params": [
            {
                "id": "Yzn11 - 50kVA",
                "sn": 50000.0,
                "uhv": 20000.0,
                "ulv": 400.0,
                "type": "yzn11",
                "z2": [0.0864, 0.09444000000000001],
                "ym": [3.6249999999999997e-07, -2.2206e-06],
                "max_power": 60000.0,
            }
        ],
    }
    dict_v3 = v2_to_v3_converter(copy.deepcopy(dict_v2))
    tp_data = dict_v3["transformers_params"][0]
    assert tp_data["sn"] == 50000.0
    assert "max_power" not in tp_data
    t_data = dict_v3["transformers"][0]
    assert t_data["params_id"] == "Yzn11 - 50kVA"
    assert t_data["max_loading"] == 60 / 50

    # The same without max_power in the original transformer parameter
    dict_v2_bis = copy.deepcopy(dict_v2)
    dict_v2_bis["transformers_params"][0].pop("max_power")
    dict_v3 = v2_to_v3_converter(dict_v2_bis)
    tp_data = dict_v3["transformers_params"][0]
    assert tp_data["sn"] == 50000.0
    assert "max_power" not in tp_data
    t_data = dict_v3["transformers"][0]
    assert t_data["params_id"] == "Yzn11 - 50kVA"
    assert t_data["max_loading"] == 1


def test_v2_to_v3_converter_line_parameters():
    # Single phase line parameter
    lp = {"id": "lp", "z_line": [[[0.05, 0.0], [0.0, 0.05]], [[0.05, 0.0], [0.0, 0.05]]]}
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="an")
    assert_json_close(
        new_lp,
        {
            "id": "lp",
            "z_line": [
                [[0.05, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.05]],
                [[0.05, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.05]],
            ],
        },
    )

    # Three-phase balanced (no change here)
    lp = {
        "id": "lp",
        "z_line": [
            [[0.05, 0.0, 0.0, 0.0], [0.0, 0.05, 0.0, 0.0], [0.0, 0.0, 0.05, 0.0], [0.0, 0.0, 0.0, 0.05]],
            [[0.05, 0.0, 0.0, 0.0], [0.0, 0.05, 0.0, 0.0], [0.0, 0.0, 0.05, 0.0], [0.0, 0.0, 0.0, 0.05]],
        ],
    }
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="abcn")
    assert new_lp == lp

    # Three-phase with shunt
    lp = {
        "id": "lp",
        "z_line": [
            [[0.12918333333333334, 0.0, 0.0], [0.0, 0.12918333333333334, 0.0], [0.0, 0.0, 0.12918333333333334]],
            [
                [0.10995533333333332, 0.05497783333333334, 0.05497783333333334],
                [0.05497783333333334, 0.10995533333333332, 0.05497783333333334],
                [0.05497783333333334, 0.05497783333333334, 0.10995533333333332],
            ],
        ],
        "y_shunt": [
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
            [
                [4.930205666666666e-5, 6.073716666666661e-7, 6.073716666666661e-7],
                [6.073716666666661e-7, 4.930205666666666e-5, 6.073716666666661e-7],
                [6.073716666666661e-7, 6.073716666666661e-7, 4.930205666666666e-5],
            ],
        ],
    }
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="abc")
    assert_json_close(
        new_lp,
        {
            "id": "lp",
            "z_line": [
                [
                    [0.12918333333333334, 0.0, 0.0, 0.0],
                    [0.0, 0.12918333333333334, 0.0, 0.0],
                    [0.0, 0.0, 0.12918333333333334, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
                [
                    [0.10995533333333332, 0.05497783333333334, 0.05497783333333334, 0.0],
                    [0.05497783333333334, 0.10995533333333332, 0.05497783333333334, 0.0],
                    [0.05497783333333334, 0.05497783333333334, 0.10995533333333332, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
            ],
            "y_shunt": [
                [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                [
                    [4.930205666666666e-5, 6.073716666666661e-7, 6.073716666666661e-7, 0.0],
                    [6.073716666666661e-7, 4.930205666666666e-5, 6.073716666666661e-7, 0.0],
                    [6.073716666666661e-7, 6.073716666666661e-7, 4.930205666666666e-5, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
            ],
        },
    )

    # Full example
    lp = {
        "id": "U_AL_150",
        "z_line": [
            [[0.188, 0.0, 0.0, 0.0], [0.0, 0.188, 0.0, 0.0], [0.0, 0.0, 0.188, 0.0], [0.0, 0.0, 0.0, 0.188]],
            [
                [0.32828402771266313, 0.26757551559358256, 0.24579965469054643, 0.26757551559358234],
                [0.26757551559358256, 0.32828402771266313, 0.26757551559358234, 0.24579965469054643],
                [0.24579965469054643, 0.26757551559358234, 0.32828402771266313, 0.26757551559358256],
                [0.26757551559358234, 0.24579965469054643, 0.26757551559358256, 0.32828402771266313],
            ],
        ],
        "y_shunt": [
            [
                [4.063682544124005e-5, 0.0, 0.0, 0.0],
                [0.0, 4.063682544124003e-5, 0.0, 0.0],
                [0.0, 0.0, 4.063682544124003e-5, 0.0],
                [0.0, 0.0, 0.0, 4.0636825441240034e-5],
            ],
            [
                [0.0009990656421805131, -0.000185181796574586, 4.8578374989324777e-5, -0.00018518179657458464],
                [-0.00018518179657458608, 0.0009990656421805131, -0.00018518179657458462, 4.857837498932483e-5],
                [4.85783749893248e-5, -0.00018518179657458453, 0.000999065642180513, -0.00018518179657458602],
                [-0.00018518179657458456, 4.85783749893247e-5, -0.00018518179657458597, 0.0009990656421805131],
            ],
        ],
        "max_current": 325,
        "line_type": "UNDERGROUND",
        "conductor_type": "AL",
        "insulator_type": "UNKNOWN",
        "section": 150.0,
    }
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="abcn")
    assert_json_close(
        new_lp,
        {
            "id": "U_AL_150",
            "z_line": [
                [[0.188, 0.0, 0.0, 0.0], [0.0, 0.188, 0.0, 0.0], [0.0, 0.0, 0.188, 0.0], [0.0, 0.0, 0.0, 0.188]],
                [
                    [0.32828402771266313, 0.26757551559358256, 0.24579965469054643, 0.26757551559358234],
                    [0.26757551559358256, 0.32828402771266313, 0.26757551559358234, 0.24579965469054643],
                    [0.24579965469054643, 0.26757551559358234, 0.32828402771266313, 0.26757551559358256],
                    [0.26757551559358234, 0.24579965469054643, 0.26757551559358256, 0.32828402771266313],
                ],
            ],
            "y_shunt": [
                [
                    [4.063682544124005e-5, 0.0, 0.0, 0.0],
                    [0.0, 4.063682544124003e-5, 0.0, 0.0],
                    [0.0, 0.0, 4.063682544124003e-5, 0.0],
                    [0.0, 0.0, 0.0, 4.0636825441240034e-5],
                ],
                [
                    [0.0009990656421805131, -0.000185181796574586, 4.8578374989324777e-5, -0.00018518179657458464],
                    [-0.00018518179657458608, 0.0009990656421805131, -0.00018518179657458462, 4.857837498932483e-5],
                    [4.85783749893248e-5, -0.00018518179657458453, 0.000999065642180513, -0.00018518179657458602],
                    [-0.00018518179657458456, 4.85783749893247e-5, -0.00018518179657458597, 0.0009990656421805131],
                ],
            ],
            "ampacities": [325, 325, 325, 325],
            "line_type": "UNDERGROUND",
            "materials": ["AL", "AL", "AL", "AL"],
            # "insulators": None,
            "sections": [150.0, 150.0, 150.0, 150.0],
        },
    )

    # Other full example
    lp = {
        "id": "U_AL_150",
        "z_line": [
            [[0.19999999999999998, 0.0, 0.0], [0.0, 0.19999999999999998, 0.0], [0.0, 0.0, 0.19999999999999998]],
            [[0.1, 0.0, 0.0], [0.0, 0.1, 0.0], [0.0, 0.0, 0.1]],
        ],
        "y_shunt": [
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
            [
                [0.00014105751014618172, 0.0, 0.0],
                [0.0, 0.00014105751014618172, 0.0],
                [0.0, 0.0, 0.00014105751014618172],
            ],
        ],
        "max_current": 325,
        "line_type": "UNDERGROUND",
        "conductor_type": "AL",
        "insulator_type": "UNKNOWN",
        "section": 150.0,
    }
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="abc")
    assert_json_close(
        new_lp,
        {
            "id": "U_AL_150",
            "z_line": [
                [
                    [0.19999999999999998, 0.0, 0.0, 0.0],
                    [0.0, 0.19999999999999998, 0.0, 0.0],
                    [0.0, 0.0, 0.19999999999999998, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
                [[0.1, 0.0, 0.0, 0.0], [0.0, 0.1, 0.0, 0.0], [0.0, 0.0, 0.1, 0.0], [0.0, 0.0, 0.0, 0.0]],
            ],
            "y_shunt": [
                [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                [
                    [0.00014105751014618172, 0.0, 0.0, 0.0],
                    [0.0, 0.00014105751014618172, 0.0, 0.0],
                    [0.0, 0.0, 0.00014105751014618172, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
            ],
            "ampacities": [325, 325, 325, 325],
            "line_type": "UNDERGROUND",
            "materials": ["AL", "AL", "AL", "AL"],
            # "insulators": None,
            "sections": [150.0, 150.0, 150.0, 150.0],
        },
    )

    # Insulator provided and != UNKNOWN
    lp = {
        "id": "O_AM_54",
        "z_line": [
            [[0.6129629629629629, 0.0, 0.0], [0.0, 0.6129629629629629, 0.0], [0.0, 0.0, 0.6129629629629629]],
            [[0.35, 0.0, 0.0], [0.0, 0.35, 0.0], [0.0, 0.0, 0.35]],
        ],
        "y_shunt": [
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
            [[1.5707963267948965e-6, 0.0, 0.0], [0.0, 1.5707963267948965e-6, 0.0], [0.0, 0.0, 1.5707963267948965e-6]],
        ],
        "max_current": 193,
        "line_type": "OVERHEAD",
        "conductor_type": "AM",
        "insulator_type": "IP",
        "section": 54.0,
    }
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="abc")
    assert_json_close(
        new_lp,
        {
            "id": "O_AM_54",
            "z_line": [
                [
                    [0.6129629629629629, 0.0, 0.0, 0.0],
                    [0.0, 0.6129629629629629, 0.0, 0.0],
                    [0.0, 0.0, 0.6129629629629629, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
                [[0.35, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.35, 0.0], [0.0, 0.0, 0.0, 0.0]],
            ],
            "y_shunt": [
                [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                [
                    [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                    [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                    [0.0, 0.0, 1.5707963267948965e-6, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
            ],
            "ampacities": [193, 193, 193, 193],
            "line_type": "OVERHEAD",
            "materials": ["AM", "AM", "AM", "AM"],
            "insulators": ["IP", "IP", "IP", "IP"],
            "sections": [54.0, 54.0, 54.0, 54.0],
        },
    )

    # Same with a different set of phases
    new_lp = _convert_line_parameters_v2_to_v3(old_line_params_data=lp, line_phases="abn")
    assert_json_close(
        new_lp,
        {
            "id": "O_AM_54",
            "z_line": [
                [
                    [0.6129629629629629, 0.0, 0.0, 0.0],
                    [0.0, 0.6129629629629629, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.6129629629629629],
                ],
                [[0.35, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.35]],
            ],
            "y_shunt": [
                [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                [
                    [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                    [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 1.5707963267948965e-6],
                ],
            ],
            "ampacities": [193, 193, 193, 193],
            "line_type": "OVERHEAD",
            "materials": ["AM", "AM", "AM", "AM"],
            "insulators": ["IP", "IP", "IP", "IP"],
            "sections": [54.0, 54.0, 54.0, 54.0],
        },
    )


def test_v2_to_v3_lines():
    # Simple example
    lp = {"id": "lp", "z_line": [[[0.05, 0.0], [0.0, 0.05]], [[0.05, 0.0], [0.0, 0.05]]]}
    old_lines = [
        {
            "id": "line",
            "phases": "an",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "lp",
            "ground": "gnd",
        }
    ]
    old_lines_params = [lp]
    new_lines, new_lines_params = _convert_lines_v2_to_v3(old_lines=old_lines, old_lines_params=old_lines_params)
    assert_json_close(
        new_lines,
        [
            {
                "id": "line",
                "phases": "an",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "lp",
                "max_loading": 1,
                "ground": "gnd",
            }
        ],
    )
    assert_json_close(
        new_lines_params,
        [
            {
                "id": "lp",
                "z_line": [
                    [[0.05, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.05]],
                    [[0.05, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.05]],
                ],
            }
        ],
    )

    # Full example
    lp1 = {
        "id": "U_AL_150",
        "z_line": [
            [[0.188, 0.0, 0.0, 0.0], [0.0, 0.188, 0.0, 0.0], [0.0, 0.0, 0.188, 0.0], [0.0, 0.0, 0.0, 0.188]],
            [
                [0.32828402771266313, 0.26757551559358256, 0.24579965469054643, 0.26757551559358234],
                [0.26757551559358256, 0.32828402771266313, 0.26757551559358234, 0.24579965469054643],
                [0.24579965469054643, 0.26757551559358234, 0.32828402771266313, 0.26757551559358256],
                [0.26757551559358234, 0.24579965469054643, 0.26757551559358256, 0.32828402771266313],
            ],
        ],
        "y_shunt": [
            [
                [4.063682544124005e-5, 0.0, 0.0, 0.0],
                [0.0, 4.063682544124003e-5, 0.0, 0.0],
                [0.0, 0.0, 4.063682544124003e-5, 0.0],
                [0.0, 0.0, 0.0, 4.0636825441240034e-5],
            ],
            [
                [0.0009990656421805131, -0.000185181796574586, 4.8578374989324777e-5, -0.00018518179657458464],
                [-0.00018518179657458608, 0.0009990656421805131, -0.00018518179657458462, 4.857837498932483e-5],
                [4.85783749893248e-5, -0.00018518179657458453, 0.000999065642180513, -0.00018518179657458602],
                [-0.00018518179657458456, 4.85783749893247e-5, -0.00018518179657458597, 0.0009990656421805131],
            ],
        ],
        "max_current": 325,
        "line_type": "UNDERGROUND",
        "conductor_type": "AL",
        "insulator_type": "UNKNOWN",
        "section": 150.0,
    }
    lp2 = {
        "id": "O_AM_54",
        "z_line": [
            [[0.6129629629629629, 0.0, 0.0], [0.0, 0.6129629629629629, 0.0], [0.0, 0.0, 0.6129629629629629]],
            [[0.35, 0.0, 0.0], [0.0, 0.35, 0.0], [0.0, 0.0, 0.35]],
        ],
        "y_shunt": [
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
            [[1.5707963267948965e-6, 0.0, 0.0], [0.0, 1.5707963267948965e-6, 0.0], [0.0, 0.0, 1.5707963267948965e-6]],
        ],
        "max_current": 193,
        "line_type": "OVERHEAD",
        "conductor_type": "AM",
        "insulator_type": "UNKNOWN",
        "section": 54.0,
    }
    old_lines_params = [lp1, lp2]
    old_lines = [
        {
            "id": "line1",
            "phases": "abc",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "O_AM_54",
            "ground": "gnd",
        },
        {
            "id": "line2",
            "phases": "abcn",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "U_AL_150",
            "ground": "gnd",
        },
    ]
    new_lines, new_lines_params = _convert_lines_v2_to_v3(old_lines=old_lines, old_lines_params=old_lines_params)
    assert_json_close(
        new_lines,
        [
            {
                "id": "line1",
                "phases": "abc",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "O_AM_54",
                "max_loading": 1,
                "ground": "gnd",
            },
            {
                "id": "line2",
                "phases": "abcn",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "U_AL_150",
                "max_loading": 1,
                "ground": "gnd",
            },
        ],
    )
    assert_json_close(
        new_lines_params,
        [
            {
                "id": "O_AM_54",
                "z_line": [
                    [
                        [0.6129629629629629, 0.0, 0.0, 0.0],
                        [0.0, 0.6129629629629629, 0.0, 0.0],
                        [0.0, 0.0, 0.6129629629629629, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                    [[0.35, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.35, 0.0], [0.0, 0.0, 0.0, 0.0]],
                ],
                "y_shunt": [
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                    [
                        [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                        [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                        [0.0, 0.0, 1.5707963267948965e-6, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                ],
                "ampacities": [193, 193, 193, 193],
                "line_type": "OVERHEAD",
                "materials": ["AM", "AM", "AM", "AM"],
                "sections": [54.0, 54.0, 54.0, 54.0],
            },
            {
                "id": "U_AL_150",
                "z_line": [
                    [[0.188, 0.0, 0.0, 0.0], [0.0, 0.188, 0.0, 0.0], [0.0, 0.0, 0.188, 0.0], [0.0, 0.0, 0.0, 0.188]],
                    [
                        [0.32828402771266313, 0.26757551559358256, 0.24579965469054643, 0.26757551559358234],
                        [0.26757551559358256, 0.32828402771266313, 0.26757551559358234, 0.24579965469054643],
                        [0.24579965469054643, 0.26757551559358234, 0.32828402771266313, 0.26757551559358256],
                        [0.26757551559358234, 0.24579965469054643, 0.26757551559358256, 0.32828402771266313],
                    ],
                ],
                "y_shunt": [
                    [
                        [4.063682544124005e-5, 0.0, 0.0, 0.0],
                        [0.0, 4.063682544124003e-5, 0.0, 0.0],
                        [0.0, 0.0, 4.063682544124003e-5, 0.0],
                        [0.0, 0.0, 0.0, 4.0636825441240034e-5],
                    ],
                    [
                        [0.0009990656421805131, -0.000185181796574586, 4.8578374989324777e-5, -0.00018518179657458464],
                        [-0.00018518179657458608, 0.0009990656421805131, -0.00018518179657458462, 4.857837498932483e-5],
                        [4.85783749893248e-5, -0.00018518179657458453, 0.000999065642180513, -0.00018518179657458602],
                        [-0.00018518179657458456, 4.85783749893247e-5, -0.00018518179657458597, 0.0009990656421805131],
                    ],
                ],
                "ampacities": [325, 325, 325, 325],
                "line_type": "UNDERGROUND",
                "materials": ["AL", "AL", "AL", "AL"],
                # "insulators": None,
                "sections": [150.0, 150.0, 150.0, 150.0],
            },
        ],
    )

    # The same line parameters used two times with two different set of phases
    # An other used two times with two different sets of parameters
    old_lines_params = [lp1, lp2]
    old_lines = [
        # O_AM_54 used with two sets of phases
        {
            "id": "line1",
            "phases": "abc",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "O_AM_54",
            "ground": "gnd",
        },
        {
            "id": "line2",
            "phases": "can",  # Other phases
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "O_AM_54",
            "ground": "gnd",
        },
        # U_AL_150 used twice with same phases
        {
            "id": "line3",
            "phases": "abcn",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "U_AL_150",
            "ground": "gnd",
        },
        {
            "id": "line4",
            "phases": "abcn",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "U_AL_150",
            "ground": "gnd",
        },
    ]
    with pytest.warns(
        UserWarning,
        match=r"The line parameters 'O_AM_54' has been used for lines with several set of phases. Thus, it has been "
        "duplicated and renamed to fit the new requirements of the file format. The new parameters' id are: "
        "'O_AM_54_abc', 'O_AM_54_can'.",
    ):
        new_lines, new_lines_params = _convert_lines_v2_to_v3(old_lines=old_lines, old_lines_params=old_lines_params)
    assert_json_close(
        new_lines,
        [
            # O_AM_54 used with two sets of phases
            {
                "id": "line1",
                "phases": "abc",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "O_AM_54_abc",
                "max_loading": 1,
                "ground": "gnd",
            },
            {
                "id": "line2",
                "phases": "can",  # Other phases
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "O_AM_54_can",
                "max_loading": 1,
                "ground": "gnd",
            },
            # U_AL_150 used twice with same phases
            {
                "id": "line3",
                "phases": "abcn",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "U_AL_150",
                "max_loading": 1,
                "ground": "gnd",
            },
            {
                "id": "line4",
                "phases": "abcn",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "U_AL_150",
                "max_loading": 1,
                "ground": "gnd",
            },
        ],
    )
    assert_json_close(
        new_lines_params,
        [
            {
                "id": "O_AM_54_abc",
                "z_line": [
                    [
                        [0.6129629629629629, 0.0, 0.0, 0.0],
                        [0.0, 0.6129629629629629, 0.0, 0.0],
                        [0.0, 0.0, 0.6129629629629629, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                    [[0.35, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.35, 0.0], [0.0, 0.0, 0.0, 0.0]],
                ],
                "y_shunt": [
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                    [
                        [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                        [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                        [0.0, 0.0, 1.5707963267948965e-6, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                ],
                "ampacities": [193, 193, 193, 193],
                "line_type": "OVERHEAD",
                "materials": ["AM", "AM", "AM", "AM"],
                "sections": [54.0, 54.0, 54.0, 54.0],
            },
            {
                "id": "O_AM_54_can",
                "z_line": [
                    [
                        [0.6129629629629629, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.6129629629629629, 0.0],
                        [0.0, 0.0, 0.0, 0.6129629629629629],
                    ],
                    [[0.35, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.35, 0.0], [0.0, 0.0, 0.0, 0.35]],
                ],
                "y_shunt": [
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                    [
                        [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 1.5707963267948965e-6, 0.0],
                        [0.0, 0.0, 0.0, 1.5707963267948965e-6],
                    ],
                ],
                "ampacities": [193, 193, 193, 193],
                "line_type": "OVERHEAD",
                "materials": ["AM", "AM", "AM", "AM"],
                "sections": [54.0, 54.0, 54.0, 54.0],
            },
            {
                "id": "U_AL_150",
                "z_line": [
                    [[0.188, 0.0, 0.0, 0.0], [0.0, 0.188, 0.0, 0.0], [0.0, 0.0, 0.188, 0.0], [0.0, 0.0, 0.0, 0.188]],
                    [
                        [0.32828402771266313, 0.26757551559358256, 0.24579965469054643, 0.26757551559358234],
                        [0.26757551559358256, 0.32828402771266313, 0.26757551559358234, 0.24579965469054643],
                        [0.24579965469054643, 0.26757551559358234, 0.32828402771266313, 0.26757551559358256],
                        [0.26757551559358234, 0.24579965469054643, 0.26757551559358256, 0.32828402771266313],
                    ],
                ],
                "y_shunt": [
                    [
                        [4.063682544124005e-5, 0.0, 0.0, 0.0],
                        [0.0, 4.063682544124003e-5, 0.0, 0.0],
                        [0.0, 0.0, 4.063682544124003e-5, 0.0],
                        [0.0, 0.0, 0.0, 4.0636825441240034e-5],
                    ],
                    [
                        [0.0009990656421805131, -0.000185181796574586, 4.8578374989324777e-5, -0.00018518179657458464],
                        [-0.00018518179657458608, 0.0009990656421805131, -0.00018518179657458462, 4.857837498932483e-5],
                        [4.85783749893248e-5, -0.00018518179657458453, 0.000999065642180513, -0.00018518179657458602],
                        [-0.00018518179657458456, 4.85783749893247e-5, -0.00018518179657458597, 0.0009990656421805131],
                    ],
                ],
                "ampacities": [325, 325, 325, 325],
                "line_type": "UNDERGROUND",
                "materials": ["AL", "AL", "AL", "AL"],
                # "insulators": None,
                "sections": [150.0, 150.0, 150.0, 150.0],
            },
        ],
    )

    # The line parameters name already exists
    lp = {
        "id": "O_AM_54",
        "z_line": [[[0.6129629629629629, 0.0], [0.0, 0.6129629629629629]], [[0.35, 0.0], [0.0, 0.35]]],
        "y_shunt": [[[0.0, 0.0], [0.0, 0.0]], [[1.5707963267948965e-6, 0.0], [0.0, 1.5707963267948965e-6]]],
        "max_current": 193,
        "line_type": "OVERHEAD",
        "conductor_type": "AM",
        "insulator_type": "UNKNOWN",
        "section": 54.0,
    }
    lp_copy = copy.deepcopy(lp)
    lp_copy["id"] = "O_AM_54_ab"
    old_lines_params = [lp, lp_copy]
    old_lines = [
        {
            "id": "line1",
            "phases": "ab",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "O_AM_54",
            "ground": "gnd",
        },
        {
            "id": "line2",
            "phases": "bc",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "O_AM_54",
            "ground": "gnd",
        },
        {
            "id": "line3",
            "phases": "ab",
            "bus1": "sb",
            "bus2": "lb",
            "length": 10,
            "params_id": "O_AM_54_ab",
            "ground": "gnd",
        },
    ]
    with pytest.warns(
        UserWarning,
        match=r"The line parameters 'O_AM_54' has been used for lines with several set of phases. Thus, it has been "
        r"duplicated and renamed to fit the new requirements of the file format. The new parameters' id are: 'O_AM_54_ab_0', 'O_AM_54_bc'.",
    ):
        new_lines, new_lines_params = _convert_lines_v2_to_v3(old_lines=old_lines, old_lines_params=old_lines_params)
    assert_json_close(
        new_lines,
        [
            {
                "id": "line1",
                "phases": "ab",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "O_AM_54_ab_0",
                "max_loading": 1,
                "ground": "gnd",
            },
            {
                "id": "line2",
                "phases": "bc",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "O_AM_54_bc",
                "max_loading": 1,
                "ground": "gnd",
            },
            {
                "id": "line3",
                "phases": "ab",
                "bus1": "sb",
                "bus2": "lb",
                "length": 10,
                "params_id": "O_AM_54_ab",
                "max_loading": 1,
                "ground": "gnd",
            },
        ],
    )
    assert_json_close(
        new_lines_params,
        [
            {
                "id": "O_AM_54_ab_0",
                "z_line": [
                    [
                        [0.6129629629629629, 0.0, 0.0, 0.0],
                        [0.0, 0.6129629629629629, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                    [[0.35, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                ],
                "y_shunt": [
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                    [
                        [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                        [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                ],
                "ampacities": [193, 193, 193, 193],
                "line_type": "OVERHEAD",
                "materials": ["AM", "AM", "AM", "AM"],
                "sections": [54.0, 54.0, 54.0, 54.0],
            },
            {
                "id": "O_AM_54_bc",
                "z_line": [
                    [
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.6129629629629629, 0.0, 0.0],
                        [0.0, 0.0, 0.6129629629629629, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.35, 0.0], [0.0, 0.0, 0.0, 0.0]],
                ],
                "y_shunt": [
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                    [
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                        [0.0, 0.0, 1.5707963267948965e-6, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                ],
                "ampacities": [193, 193, 193, 193],
                "line_type": "OVERHEAD",
                "materials": ["AM", "AM", "AM", "AM"],
                "sections": [54.0, 54.0, 54.0, 54.0],
            },
            {
                "id": "O_AM_54_ab",
                "z_line": [
                    [
                        [0.6129629629629629, 0.0, 0.0, 0.0],
                        [0.0, 0.6129629629629629, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                    [[0.35, 0.0, 0.0, 0.0], [0.0, 0.35, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                ],
                "y_shunt": [
                    [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                    [
                        [1.5707963267948965e-6, 0.0, 0.0, 0.0],
                        [0.0, 1.5707963267948965e-6, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0],
                    ],
                ],
                "ampacities": [193, 193, 193, 193],
                "line_type": "OVERHEAD",
                "materials": ["AM", "AM", "AM", "AM"],
                "sections": [54.0, 54.0, 54.0, 54.0],
            },
        ],
    )
