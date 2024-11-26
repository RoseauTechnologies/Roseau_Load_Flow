import copy

from roseau.load_flow.io.dict import v1_to_v2_converter, v2_to_v3_converter
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow.typing import JsonDict


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
