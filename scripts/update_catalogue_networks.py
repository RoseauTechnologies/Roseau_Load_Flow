"""Update the networks in the catalogue.

See https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/181
"""

import re

import numpy as np

import roseau.load_flow as lf

PHASES = {"MV": "abc", "LV": "abcn"}
U_N = {"MV": 20_000, "LV": 230}
U_MAX = {"MV": int(20_000 * 1.05), "LV": int(230 * 1.1)}
U_MIN = {"MV": int(20_000 * 0.95), "LV": int(230 * 0.9)}

df = lf.ElectricalNetwork.get_catalogue()

if __name__ == "__main__":
    catalogue_path = lf.ElectricalNetwork.catalogue_path()
    rng = np.random.default_rng(len("Roseau_Load_Flow old networks are getting a rewrite") ** 5)
    name: str
    for name in df.index:
        feeder_type = name[:2]  # "MV" or "LV"
        load_points: list[str] = df.at[name, "Available load points"]
        for lp in load_points:
            print(f"Processing network {name}_{lp}")
            en = lf.ElectricalNetwork.from_catalogue(name, load_point_name=lp)

            source_bus_id: str | None = None
            feeder_bus_id: str | None = None
            new_buses = {}
            for bus_id in sorted(en.buses):  # we need to sort to get MVLV bus before VoltageSource bus
                assert isinstance(bus_id, str), repr(bus_id)
                bus = en.buses[bus_id]
                assert (
                    bus.phases == "abcn" if bus_id == "VoltageSource" else PHASES[feeder_type]
                ), f"{name=}, {bus_id=}, {bus.phases=}"
                bus_type = feeder_type
                if (feeder_type == "LV" and bus_id.startswith("MVLV")) or (
                    feeder_type == "MV" and bus_id.startswith("HVMV")
                ):
                    # This is a feeder bus, we use its name as the source bus name
                    # and we create add the word "Feeder" to the feeder's bus name
                    assert feeder_bus_id is None, f"{name=}, {bus_id=}, {feeder_bus_id=}"
                    assert source_bus_id is None, f"{name=}, {bus_id=}, {source_bus_id=}"
                    source_bus_id = bus_id
                    feeder_bus_id = f"{bus_id[:4]}Feeder{bus_id[4:]}"
                    bus_id = feeder_bus_id
                elif bus_id.startswith(feeder_type):
                    # Normal bus, nothing to do
                    pass
                elif bus_id == "VoltageSource":
                    assert source_bus_id is not None
                    bus_id = source_bus_id
                    if feeder_type == "LV":
                        # This is the only MV bus in the network
                        # Set the correct bus type to pick up the correct min/max voltages
                        bus_type = "MV"
                else:
                    raise AssertionError(bus_id)
                assert bus_id not in new_buses, bus_id
                new_bus = lf.Bus(
                    bus_id,
                    phases=PHASES[bus_type],
                    geometry=bus.geometry,
                    min_voltage=U_MIN[bus_type],
                    max_voltage=U_MAX[bus_type],
                )
                new_buses[bus_id] = new_bus
            assert feeder_bus_id is not None
            assert source_bus_id is not None

            new_grounds = {}
            assert len(en.grounds) == 1, en.grounds
            for ground_id in en.grounds:
                ground = en.grounds[ground_id]
                new_ground = lf.Ground(ground_id)
                if feeder_type == "LV":
                    new_ground.connect(new_buses[feeder_bus_id], phase="n")
                new_grounds[ground_id] = new_ground

            new_branches = {}
            for branch_id in en.branches:
                assert isinstance(branch_id, str), repr(branch_id)
                branch = en.branches[branch_id]
                if isinstance(branch, lf.Line):
                    assert branch.phases == PHASES[feeder_type], branch.phases
                    assert branch_id.startswith(feeder_type)
                    ground = new_grounds[branch.ground.id] if branch.ground is not None else None
                    bus1_id = branch.bus1.id
                    if bus1_id == source_bus_id:  # This was the feeder bus
                        bus1_id = feeder_bus_id
                    elif bus1_id == "VoltageSource":  # This was the source bus
                        bus1_id = source_bus_id
                    bus2_id = branch.bus2.id  # Always a regular bus
                    assert bus2_id not in ("VoltageSource", source_bus_id), bus2_id
                    new_params_id = branch.parameters.id.replace("S_", "U_").replace("A_", "O_")
                    iec_params = lf.LineParameters.from_catalogue(new_params_id)
                    new_params = lf.LineParameters(
                        new_params_id,
                        z_line=branch.parameters.z_line,
                        y_shunt=branch.parameters.y_shunt,
                        # Add missing data from the IEC catalogue
                        max_current=iec_params.max_current,
                        line_type=iec_params.line_type,
                        conductor_type=iec_params.conductor_type,
                        insulator_type=iec_params.insulator_type,
                        section=iec_params.section,
                    )
                    new_branch = lf.Line(
                        branch_id,
                        bus1=new_buses[bus1_id],
                        bus2=new_buses[bus2_id],
                        parameters=new_params,
                        length=branch.length,
                        phases=branch.phases,
                        ground=ground,
                        geometry=branch.geometry,
                    )
                elif isinstance(branch, lf.Transformer):
                    assert branch.bus1.id == "VoltageSource"  # This was the source bus
                    assert branch.bus2.id == source_bus_id  # This was the feeder bus
                    assert branch.phases1 == "abc"
                    assert branch.phases2 == "abcn"
                    new_branch = lf.Transformer(
                        branch_id,
                        bus1=new_buses[source_bus_id],
                        bus2=new_buses[feeder_bus_id],
                        parameters=branch.parameters,
                        tap=branch.tap,
                        phases1=branch.phases1,
                        phases2=branch.phases2,
                        geometry=branch.geometry,
                    )
                    assert isinstance(branch.parameters.id, str), repr(branch.parameters.id)
                    m = re.match(r"^.*_(\d+)kVA$", branch.parameters.id)
                    assert m, branch.parameters.id
                    branch.parameters.max_power = int(m.group(1)) * 1_000
                elif isinstance(branch, lf.Switch):
                    assert branch.bus1.id == "VoltageSource"  # This was the source bus
                    assert branch.bus2.id == source_bus_id  # This was the feeder bus
                    assert branch.phases == "abc"
                    new_branch = lf.Switch(
                        branch_id,
                        bus1=new_buses[source_bus_id],
                        bus2=new_buses[feeder_bus_id],
                        phases=branch.phases,
                        geometry=branch.geometry,
                    )
                else:
                    raise AssertionError(branch)
                assert new_branch.geometry == branch.geometry
                new_branches[branch_id] = new_branch

            new_loads = {}
            for load_id in sorted(en.loads):
                load = en.loads[load_id]
                assert load.phases == PHASES[feeder_type]
                assert isinstance(load.bus.id, str), repr(load.bus.id)
                assert load.bus.id.startswith(feeder_type), load.bus.id
                assert isinstance(load, lf.PowerLoad), repr(load)
                assert load.flexible_params is None, repr(load.flexible_params)
                if feeder_type == "LV":
                    power_mask = np.not_equal(load.powers.m, 0)
                    nb_powers = sum(power_mask)
                    assert nb_powers <= 1, load.powers  # only one phase has power (or none)
                    if nb_powers == 0:
                        # Dummy load with power=0, choose a random phase
                        new_phases = rng.choice(["a", "b", "c"]) + "n"
                        new_powers = np.array([0j])
                    else:
                        new_phases = "abc"[power_mask.argmax(axis=0)] + "n"
                        new_powers = np.round(load.powers[power_mask].m, -2)
                else:
                    new_phases = "abc"
                    new_powers = np.round(load.powers.m, -2)

                new_load = lf.PowerLoad(
                    load_id,
                    bus=new_buses[load.bus.id],
                    powers=new_powers,
                    phases=new_phases,
                )
                new_loads[load_id] = new_load

            new_sources = {}
            assert len(en.sources) == 1, en.sources
            for source_id in en.sources:
                source = en.sources[source_id]
                assert source.phases == "abcn"
                assert source.bus.id == "VoltageSource"
                v = source.voltages.m
                new_voltages = np.array([v[0] - v[1], v[1] - v[2], v[2] - v[0]])  # phase-to-phase
                new_source = lf.VoltageSource(
                    source_id,
                    bus=new_buses[source_bus_id],
                    voltages=new_voltages,
                    phases="abc",
                )
                new_sources[source_id] = new_source

            new_potential_refs = {}
            assert len(en.potential_refs) == 1, en.potential_refs
            for potential_ref_id in en.potential_refs:
                assert potential_ref_id == "pref", potential_ref_id
                potential_ref = en.potential_refs[potential_ref_id]
                assert potential_ref.phase is None
                assert potential_ref.element.id == "ground"
                new_potential_ref = lf.PotentialRef(potential_ref_id, element=new_grounds[potential_ref.element.id])
                new_potential_refs[potential_ref_id] = new_potential_ref
            if feeder_type == "LV":
                # Add a potential ref for the MV source bus
                new_potential_ref = lf.PotentialRef("MV_pref", element=new_buses[source_bus_id])
                new_potential_refs["MV_pref"] = new_potential_ref

            new_en = lf.ElectricalNetwork.from_element(new_buses[source_bus_id])
            new_en.to_json(catalogue_path / f"{name}_{lp}.json", include_results=False)

            # Test the new network
            new_en.solve_load_flow()
    print("Done")
