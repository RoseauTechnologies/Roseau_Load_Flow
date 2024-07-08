"""Generate the catalogue data of the networks folder. This json file contains some statistics on the available
networks."""

import json
from pathlib import Path

from roseau.load_flow import ElectricalNetwork

if __name__ == "__main__":
    catalogue_path = (Path(__file__).parents[1] / "roseau" / "load_flow" / "data" / "networks").expanduser().absolute()
    network_data = {}
    for p in catalogue_path.glob("*.json"):
        if p.stem == "Catalogue":
            continue

        network_name, load_point = p.stem.split("_")
        if network_name in network_data:
            network_data[network_name]["load_points"].append(load_point)
        else:
            en = ElectricalNetwork.from_json(p)
            network_data[network_name] = {
                "nb_buses": len(en.buses),
                "nb_lines": len(en.lines),
                "nb_transformers": len(en.transformers),
                "nb_switches": len(en.switches),
                "nb_loads": len(en.loads),
                "nb_sources": len(en.sources),
                "nb_grounds": len(en.grounds),
                "nb_potential_refs": len(en.potential_refs),
                "load_points": [load_point],
            }
    network_data = dict(sorted(network_data.items()))
    (catalogue_path / "Catalogue.json").write_text(json.dumps(obj=network_data, indent=4))
