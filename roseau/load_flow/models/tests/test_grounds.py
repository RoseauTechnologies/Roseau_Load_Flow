import pytest

from roseau.load_flow.models import Bus, Ground
from roseau.load_flow.testing import assert_json_close


def test_ground_to_multiple_bus_phases():
    bus = Bus("B", phases="abcn")
    ground = Ground("G")
    ground.connect(bus, phase="n")
    with pytest.warns(UserWarning, match=r"Ground 'G' is already connected to bus 'B'"):
        ground.connect(bus, phase="a")
    assert ground.connected_buses == {"B": "na"}

    ground_dict = ground.to_dict()
    expected_dict = {"id": "G", "buses": [{"id": "B", "phase": "na"}]}
    assert_json_close(ground_dict, expected_dict)
    for d in expected_dict["buses"]:
        d["bus"] = bus
    with pytest.warns(UserWarning, match=r"Ground 'G' is already connected to bus 'B'"):
        new_ground = Ground.from_dict(expected_dict)
    assert new_ground.connected_buses == {"B": "na"}
