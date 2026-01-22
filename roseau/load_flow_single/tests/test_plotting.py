import roseau.load_flow_single as rlfs
from roseau.load_flow.testing import assert_json_close


def test_plot_interactive_map(all_elements_network_with_results):
    en = all_elements_network_with_results
    en.crs = "EPSG:4326"
    rlfs.plotting.plot_interactive_map(en)
    rlfs.plotting.plot_results_interactive_map(en)


def test_voltage_profile(all_elements_network_with_results):
    en = all_elements_network_with_results
    for bus_id, vn in en._get_nominal_voltages().items():
        en.buses[bus_id].nominal_voltage = vn
    en.buses["bus1"].min_voltage_level = 0.9
    en.buses["bus1"].max_voltage_level = 1.1
    profile = rlfs.plotting.voltage_profile(en)
    assert profile.starting_bus_id == next(iter(profile.network.sources.values())).bus.id
    assert_json_close(
        profile.buses,
        {
            "bus0": {
                "distance": 0.0,
                "voltage": profile.network.buses["bus0"].res_voltage_level.m * 100,  # type: ignore
                "voltages": None,
                "min_voltage": None,
                "max_voltage": None,
                "state": "unknown",  # no voltage limits
                "is_tr_bus": False,
            },
            "bus1": {
                "distance": 1.5,
                "voltage": profile.network.buses["bus1"].res_voltage_level.m * 100,  # type: ignore
                "voltages": None,
                "min_voltage": 90,
                "max_voltage": 110,
                "state": "normal",
                "is_tr_bus": False,  # because traverse_transformers=False by default
            },
        },
    )
    assert_json_close(
        profile.lines,
        {
            "line0": {
                "from_bus": "bus0",
                "to_bus": "bus1",
                "loading": profile.network.lines["line0"].res_loading.m * 100,  # type: ignore
                "loadings": None,
                "max_loading": 100.0,
                "state": "normal",
            },
        },
    )
    assert not profile.transformers  # because traverse_transformers=False by default


def test_voltage_profile_traverse_transformers(all_elements_network_with_results):
    en = all_elements_network_with_results
    for bus_id, vn in en._get_nominal_voltages().items():
        en.buses[bus_id].nominal_voltage = vn
    profile = rlfs.plotting.voltage_profile(en, traverse_transformers=True)
    assert profile.starting_bus_id == next(iter(profile.network.sources.values())).bus.id
    assert len(profile.buses) == len(profile.network.buses)
    assert profile.buses["bus0"]["is_tr_bus"] is False
    assert profile.buses["bus1"]["is_tr_bus"] is True
    assert profile.buses["bus2"]["is_tr_bus"] is True
    assert profile.buses["bus3"]["is_tr_bus"] is False
    assert len(profile.lines) == len(profile.network.lines)
    tr = profile.network.transformers["transformer0"]
    assert_json_close(
        profile.transformers,
        {
            "transformer0": {
                "from_bus": "bus1",
                "to_bus": "bus2",
                "loading": tr.res_loading.m * 100,
                "loadings": None,
                "max_loading": tr.max_loading.m * 100,
                "state": "normal",
            },
        },
    )


def test_voltage_profile_parallel_branches():
    bus1 = rlfs.Bus(id="Bus 1", nominal_voltage=400)
    bus2 = rlfs.Bus(id="Bus 2", nominal_voltage=400)
    lp = rlfs.LineParameters.from_catalogue("U_AL_120")
    line1 = rlfs.Line(id="Line 1", bus1=bus1, bus2=bus2, parameters=lp, length=1.0)
    line2 = rlfs.Line(id="Line 2", bus1=bus1, bus2=bus2, parameters=lp, length=2.0)
    src = rlfs.VoltageSource(id="Src", bus=bus1, voltage=400)

    # Set fake results
    bus1._res_voltage = 400 + 0j
    bus2._res_voltage = 380 + 0j
    line1.side1._res_current = 50 + 0j
    line1.side2._res_current = -50 + 0j
    line2.side1._res_current = 25 + 0j
    line2.side2._res_current = -25 + 0j
    src._res_current = -75 + 0j
    en = rlfs.ElectricalNetwork.from_element(bus1)
    for e in en._elements:
        e._fetch_results = False
        e._no_results = False
    en._results_valid = True
    en._no_results = False

    profile = rlfs.plotting.voltage_profile(en)
    assert sorted(profile.lines) == ["Line 1", "Line 2"]
    assert profile.buses["Bus 1"]["distance"] == 0.0
    assert profile.buses["Bus 2"]["distance"] == 1.0  # shortest path

    line2._length = 1.0
    profile = rlfs.plotting.voltage_profile(en)
    assert sorted(profile.lines) == ["Line 1", "Line 2"]
    assert profile.buses["Bus 1"]["distance"] == 0.0
    assert profile.buses["Bus 2"]["distance"] == 1.0  # both paths equal length
