"""Generate the catalogue of transformers from the CSV file of transformers."""

from pathlib import Path

import numpy as np
import pandas as pd

from roseau.load_flow import Q_, TransformerParameters

if __name__ == "__main__":
    catalogue_path = (
        (Path(__file__).parents[1] / "roseau" / "load_flow" / "data" / "transformers").expanduser().absolute()
    )
    catalogue_data_path = catalogue_path / "Catalogue.csv"
    df = pd.read_csv(catalogue_data_path)

    for idx in df.index:
        id = df.at[idx, "id"]
        manufacturer = df.at[idx, "manufacturer"]
        range = df.at[idx, "range"]
        efficiency = df.at[idx, "efficiency"]
        destination_path = catalogue_path / manufacturer / range / efficiency
        destination_path.mkdir(exist_ok=True, parents=True)

        # Get parameters
        uhv = Q_(df.at[idx, "uhv"], "V")  # Phase-to-phase nominal voltages of the primary side
        ulv = Q_(df.at[idx, "ulv"], "V")  # Phase-to-phase nominal voltages of the secondary side
        sn = Q_(df.at[idx, "sn"], "VA")  # Nominal power
        i0 = Q_(np.round(df.at[idx, "i0"], decimals=3), "")  # Current during open-circuit test
        p0 = Q_(df.at[idx, "p0"], "W")  # Losses during open-circuit test
        psc = Q_(df.at[idx, "psc"], "W")  # Losses during short-circuit test
        vsc = Q_(df.at[idx, "vsc"], "")  # Voltages on LV side during short-circuit test
        vg = df.at[idx, "vg"]

        # Check the canonical name
        sn_kva = int(sn.m_as("kVA"))
        assert id == f"{manufacturer}_{range}_{efficiency}_{sn_kva}kVA"

        # Generate transformer parameters
        tp = TransformerParameters.from_open_and_short_circuit_tests(
            id=id, vg=vg, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc
        )
        assert tp.z2 is not None, id
        assert tp.ym is not None, id
        assert tp.k is not None, id
        tp.to_json(destination_path / f"{sn_kva}.json")

    # Sort the catalogue and write it
    df.sort_values(by=["manufacturer", "range", "efficiency", "sn"]).to_csv(catalogue_data_path, index=False)
