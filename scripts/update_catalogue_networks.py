"""Update the networks in the catalogue.

See https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/181
"""

import re

import numpy as np

import roseau.load_flow as rlf

PHASES = {"MV": "abc", "LV": "abcn"}
U_N = {"MV": 20_000, "LV": 400}
U_MAX = {"MV": 1.05, "LV": 1.1}
U_MIN = {"MV": 0.95, "LV": 0.9}

df = rlf.ElectricalNetwork.get_catalogue()

if __name__ == "__main__":
    catalogue_path = rlf.ElectricalNetwork.catalogue_path()
    rng = np.random.default_rng(len("Roseau_Load_Flow old networks are getting a rewrite") ** 5)
    name: str
    for name in df.index:
        feeder_type = name[:2]  # "MV" or "LV"
        load_points: list[str] = df.at[name, "Available load points"]
        for lp in load_points:
            print(f"Processing network {name}_{lp}")
            en = rlf.ElectricalNetwork.from_catalogue(name=name, load_point_name=lp)

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
                new_bus = rlf.Bus(
                    id=bus_id,
                    phases=PHASES[bus_type],
                    geometry=bus.geometry,
                    nominal_voltage=U_N[bus_type],
                    min_voltage_level=U_MIN[bus_type],
                    max_voltage_level=U_MAX[bus_type],
                )
                new_buses[bus_id] = new_bus
            assert feeder_bus_id is not None
            assert source_bus_id is not None

            new_grounds = {}
            assert len(en.grounds) == 1, en.grounds
            for ground_id in en.grounds:
                ground = en.grounds[ground_id]
                new_ground = rlf.Ground(ground_id)
                if feeder_type == "LV":
                    new_ground.connect(bus=new_buses[feeder_bus_id], phase="n")
                new_grounds[ground_id] = new_ground

            new_lines = {}
            for line_id, line in en.lines.items():
                assert isinstance(line_id, str), repr(line_id)
                assert line.phases == PHASES[feeder_type], line.phases
                assert line_id.startswith(feeder_type)
                ground = new_grounds[line.ground.id] if line.ground is not None else None
                bus1_id = line.bus1.id
                if bus1_id == source_bus_id:  # This was the feeder bus
                    bus1_id = feeder_bus_id
                elif bus1_id == "VoltageSource":  # This was the source bus
                    bus1_id = source_bus_id
                bus2_id = line.bus2.id  # Always a regular bus
                assert bus2_id not in ("VoltageSource", source_bus_id), bus2_id
                new_params_id = line.parameters.id.replace("S_", "U_").replace("A_", "O_")
                iec_params = rlf.LineParameters.from_catalogue(new_params_id)
                new_params = rlf.LineParameters(
                    id=new_params_id,
                    z_line=line.parameters.z_line,
                    y_shunt=line.parameters.y_shunt,
                    # Add missing data from the IEC catalogue
                    max_currents=iec_params.max_currents,
                    line_type=iec_params.line_type,
                    materials=iec_params.materials,
                    insulators=iec_params.insulators,
                    sections=iec_params.sections,
                )
                new_line = rlf.Line(
                    id=line_id,
                    bus1=new_buses[bus1_id],
                    bus2=new_buses[bus2_id],
                    parameters=new_params,
                    length=line.length,
                    phases=line.phases,
                    ground=ground,
                    geometry=line.geometry,
                )
                assert new_line.geometry == line.geometry
                new_lines[line_id] = new_line

            new_transformers = {}
            for transformer_id, transformer in en.transformers.items():
                assert isinstance(transformer_id, str), repr(transformer_id)
                assert transformer.bus1.id == "VoltageSource"  # This was the source bus
                assert transformer.bus2.id == source_bus_id  # This was the feeder bus
                assert transformer.phases1 == "abc"
                assert transformer.phases2 == "abcn"
                new_transformer = rlf.Transformer(
                    id=transformer_id,
                    bus1=new_buses[source_bus_id],
                    bus2=new_buses[feeder_bus_id],
                    parameters=transformer.parameters,
                    tap=transformer.tap,
                    phases1=transformer.phases1,
                    phases2=transformer.phases2,
                    geometry=transformer.geometry,
                )
                assert isinstance(transformer.parameters.id, str), repr(transformer.parameters.id)
                m = re.match(pattern=r"^.*_(\d+)kVA$", string=transformer.parameters.id)
                assert m, transformer.parameters.id
                transformer.parameters.max_power = int(m.group(1)) * 1_000
                assert new_transformer.geometry == transformer.geometry
                new_transformers[transformer_id] = new_transformer

            new_switches = {}
            for switch_id, switch in en.switches.items():
                assert isinstance(switch_id, str), repr(switch_id)
                assert switch.bus1.id == "VoltageSource"  # This was the source bus
                assert switch.bus2.id == source_bus_id  # This was the feeder bus
                assert switch.phases == "abc"
                new_branch = rlf.Switch(
                    id=switch_id,
                    bus1=new_buses[source_bus_id],
                    bus2=new_buses[feeder_bus_id],
                    phases=switch.phases,
                    geometry=switch.geometry,
                )
                assert new_branch.geometry == switch.geometry
                new_switches[switch_id] = new_branch

            new_loads = {}
            for load_id in sorted(en.loads):
                load = en.loads[load_id]
                assert load.phases == PHASES[feeder_type]
                assert isinstance(load.bus.id, str), repr(load.bus.id)
                assert load.bus.id.startswith(feeder_type), load.bus.id
                assert isinstance(load, rlf.PowerLoad), repr(load)
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

                new_load = rlf.PowerLoad(
                    id=load_id,
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
                new_source = rlf.VoltageSource(
                    id=source_id,
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
                assert potential_ref.phases is None
                assert potential_ref.element.id == "ground"
                new_potential_ref = rlf.PotentialRef(potential_ref_id, element=new_grounds[potential_ref.element.id])
                new_potential_refs[potential_ref_id] = new_potential_ref
            if feeder_type == "LV":
                # Add a potential ref for the MV source bus
                new_potential_ref = rlf.PotentialRef("MV_pref", element=new_buses[source_bus_id])
                new_potential_refs["MV_pref"] = new_potential_ref

            new_en = rlf.ElectricalNetwork.from_element(new_buses[source_bus_id])
            new_en.to_json(path=catalogue_path / f"{name}_{lp}.json", include_results=False)

            # Test the new network
            new_en.solve_load_flow()
    print("Done")
