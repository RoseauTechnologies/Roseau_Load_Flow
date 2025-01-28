from typing import Final

import pandas as pd

# pandas dtypes used in the data frames
PhaseDtype: Final = pd.CategoricalDtype(categories=["a", "b", "c", "n"], ordered=True)
"""Categorical data type used for the phase of potentials, currents, powers, etc."""
VoltagePhaseDtype: Final = pd.CategoricalDtype(categories=["an", "bn", "cn", "ab", "bc", "ca"], ordered=True)
"""Categorical data type used for the phase of voltages and flexible powers only."""
BranchTypeDtype: Final = pd.CategoricalDtype(categories=["line", "transformer", "switch"], ordered=True)
"""Categorical data type used for branch types."""
LoadTypeDtype: Final = pd.CategoricalDtype(categories=["power", "current", "impedance"], ordered=True)
"""Categorical data type used for load types."""
SequenceDtype: Final = pd.CategoricalDtype(categories=["zero", "pos", "neg"], ordered=True)
"""Categorical data type used for symmetrical components."""
DTYPES: Final = {
    "bus_id": object,
    "branch_id": object,
    "transformer_id": object,
    "line_id": object,
    "switch_id": object,
    "load_id": object,
    "source_id": object,
    "ground_id": object,
    "potential_ref_id": object,
    "type": object,
    "phase": PhaseDtype,
    "current": complex,
    "current1": complex,
    "current2": complex,
    "current_hv": complex,
    "current_lv": complex,
    "power": complex,
    "flexible_power": complex,
    "power1": complex,
    "power2": complex,
    "power_hv": complex,
    "power_lv": complex,
    "potential": complex,
    "potential1": complex,
    "potential2": complex,
    "potential_hv": complex,
    "potential_lv": complex,
    "voltage": complex,
    "voltage1": complex,
    "voltage2": complex,
    "voltage_hv": complex,
    "voltage_lv": complex,
    "series_losses": complex,
    "shunt_losses": complex,
    "series_current": complex,
    "max_current": float,
    "loading": float,
    "max_loading": float,
    "sn": float,
    "ampacity": float,
    "voltage_level": float,
    "nominal_voltage": float,
    "min_voltage_level": float,
    "max_voltage_level": float,
    "violated": pd.BooleanDtype(),
    "flexible": pd.BooleanDtype(),
}
