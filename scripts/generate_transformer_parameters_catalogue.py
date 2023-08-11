"""Generate the catalogue of transformers from the CSV files of manufacturers."""
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
        manufacturer = df.at[idx, "manufacturer"]
        range = df.at[idx, "range"]
        efficiency = df.at[idx, "efficiency"]
        destination_path = catalogue_path / manufacturer / range / efficiency
        destination_path.mkdir(exist_ok=True, parents=True)

        # Get parameters
        uhv = Q_(df.at[idx, "uhv"], "V")  # Phase-to-phase nominal voltages of the high voltages side
        ulv = Q_(df.at[idx, "ulv"], "V")  # Phase-to-phase nominal voltages of the low voltages side
        sn = Q_(df.at[idx, "sn"], "VA")  # Nominal power
        i0 = Q_(np.round(df.at[idx, "i0"], decimals=3), "")  # Current during off-load test
        p0 = Q_(df.at[idx, "p0"], "W")  # Losses during off-load test
        psc = Q_(df.at[idx, "psc"], "W")  # Losses during short-circuit test
        vsc = Q_(df.at[idx, "vsc"], "")  # Voltages on LV side during short-circuit test
        type = df.at[idx, "type"]

        # Build a name
        sn_kva = int(sn.m_as("kVA"))
        name = f"{manufacturer}_{range}_{efficiency}_{sn_kva}"

        # Generate transformer parameters
        tp = TransformerParameters(id=name, type=type, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc)
        res = tp.to_zyk()
        assert all(pd.notna(x) for x in res), name
        tp.to_json(destination_path / f"{sn_kva}.json")
