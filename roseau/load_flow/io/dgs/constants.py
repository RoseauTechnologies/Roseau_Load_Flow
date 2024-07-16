from typing import Final, Literal, TypeAlias

from roseau.load_flow.utils import ConductorType, InsulatorType, LineType

# Lines
LINE_TYPES: Final[dict[int, LineType]] = {
    0: LineType.UNDERGROUND,  # inAir=Ground
    1: LineType.OVERHEAD,  # inAir=Air
}
CONDUCTOR_TYPES: Final[dict[int | str, ConductorType]] = {
    0: ConductorType.AL,
    "Al": ConductorType.AL,
    1: ConductorType.CU,
    "Cu": ConductorType.CU,
    2: ConductorType.AM,
    "Ad": ConductorType.AM,
    3: ConductorType.AA,
    "As": ConductorType.AA,
    4: ConductorType.LA,
    "Ds": ConductorType.LA,
}
INSULATOR_TYPES: Final[dict[int, InsulatorType]] = {
    0: InsulatorType.PVC,  # PVC
    1: InsulatorType.XLPE,  # XLPE
    2: InsulatorType.UNKNOWN,  # Mineral # (aka MI, MICC, Pyro) not supported by RLF
    3: InsulatorType.IP,  # Paper
    4: InsulatorType.EPR,  # EPR
}

# Loads
PwFLoadType: TypeAlias = Literal["MV", "LV", "General", "PV", "GenStat"]
LOAD_I_SYM_FIELD_NAMES: Final[dict[PwFLoadType, str | None]] = {
    "MV": "ci_sym",
    "LV": "i_sym",
    "General": "i_sym",
    "PV": None,
    "GenStat": None,
}
MV_LOAD_PHASES: Final[dict[str, str]] = {
    "3PH-'D'": "abc",  # delta load
    "3PH-'YN'": "abcn",  # star load
}
LV_LOAD_PHASES: Final[dict[int, str]] = {
    2: "abc",  # "3PH PH-E" # No neutral connection according to the PwF diagram of the load
    3: "abcn",  # "3PH-'YN'"
    # 5: "abn",  # "2PH-'YN'" # which phases?
    # 7: "ab",  # "1PH PH-PH" # which phases?
    # 8: "an",  # "1PH PH-N" # which phases?
    # 9: "a",  # "1PH PH-E" # Not allowed in RLF
}
GENERAL_LOAD_PHASES: Final[dict[str, str]] = {
    "3PH-'D'": "abc",  # delta load
    "3PH-'YN'": "abcn",  # star load
}
PV_SYS_PHASES: Final[dict[int, str]] = {
    0: "abc",  # 3PH
    1: "abc",  # 3PH-E  # No neutral on the connected cubicle
    # 2: "a",  # "1PH PH-E" # Not allowed in RLF
    # 3: "an",  # "1PH PH-N" # which phases?
}
GEN_STAT_PHASES: Final[dict[int, str]] = {
    0: "abc",  # 3PH
    1: "abc",  # 3PH-E  # No neutral on the connected cubicle
    # 2: "a",  # "1PH PH-E" # Not allowed in RLF
    # 3: "an",  # "1PH PH-N" # which phases?
    # 4: "ab",  # "1PH PH-PH" # which phases?
}
GENERAL_LOAD_INPUT_MODE: Final[dict[str, tuple[str, ...]]] = {
    "DEF": ("plini", "qlini"),  # Can the default be changed?
    "PQ": ("plini", "qlini"),
    "PC": ("plini", "coslini", "pf_recap"),
    "IC": ("ilini", "coslini", "pf_recap"),
    "SC": ("slini", "coslini", "pf_recap"),
    "QC": ("qlini", "coslini", "pf_recap"),
    "IP": ("ilini", "plini"),
    "SP": ("slini", "plini", "pf_recap"),
    "SQ": ("slini", "qlini", "p_direc"),
}
GEN_STAT_INPUT_MODE: Final[dict[str, tuple[str, ...]]] = {
    "DEF": ("pgini", "qgini"),  # Can the default be changed?
    "PQ": ("pgini", "qgini"),
    "PC": ("pgini", "cosgini", "pf_recap"),
    "SC": ("sgini", "cosgini", "pf_recap"),
    "QC": ("qgini", "cosgini", "pf_recap"),
    "SP": ("sgini", "pgini", "pf_recap"),
    "SQ": ("sgini", "qgini", "p_direc"),
}

# Buses
BUS_PHASES: Final[dict[int, str]] = {
    # "xxx-N" considers an additional neutral conductor for the xxx phase technology.
    0: "abc",  # "ABC" corresponds to a three phase system with a phase shift of 120° between the phases.
    1: "abcn",  # "ABC-N"
    # 2: "ab",  # "BI" represents a dual phase system with a 180° phase shift between both phases.
    # 3: "abn",  # "BI-N"
    # 4: "ab",  # "2PH" is used if only two of the three phases of an ABC-system are connected.
    # 5: "abn",  # "2PH-N"
    # 6: "a",  # "1PH" is the choice if only a single phase has to be modelled.
    # 7: "an",  # "1PH-N"
    # 8: "n",  # "N"
}

# Switches
SWITCH_TYPES: Final[dict[str, str]] = {
    "cbk": "Circuit-Breaker",
    "dct": "Disconnector",
    "sdc": "Switch Disconnector",
    "swt": "Load-Break-Switch",
    "dcb": "Disconnecting Circuit-Breaker",
}

# External grids
EXT_GRID_N_CONNECTION: Final[dict[int, str]] = {  # iintgnd
    0: "None",
    1: "At terminal (ABC-N)",
    2: "Separate terminal",
}
EXT_GRID_STAR_POINT: Final[dict[int, bool]] = {  # cgnd
    0: True,  # "Connected"
    1: False,  # "Not connected"
}
EXT_GRID_INPUT_MODE: Final[dict[str, tuple[str, ...]]] = {
    "DEF": ("pgini", "qgini"),  # Can the default be changed?
    "PQ": ("pgini", "qgini"),
    "PC": ("pgini", "cosgini", "pf_recap"),
    "SC": ("sgini", "cosgini", "pf_recap"),
    "QC": ("qgini", "cosgini", "pf_recap"),
    "SP": ("sgini", "pgini", "pf_recap"),
    "SQ": ("sgini", "qgini", "p_direc"),
}

# Transformers
TRANSFORMER_N_CONNECTION: Final[dict[int, str]] = {  # cneutcon
    0: "None",
    1: "At terminals (ABC-N)",
    3: "Separate on LV",
}
TRANSFORMER_STAR_POINT: Final[dict[int, bool]] = {  # cgnd_l
    0: True,  # "Connected"
    1: False,  # "Not connected"
}

# Short-circuits
SC_METHOD: Final[dict[int, str]] = {  # iopt_mde
    0: "VDE 0102 Part 0 / DIN EN 60909-0",
    1: "IEC 60909",
    2: "ANSI",
    3: "complete",
    4: "IEC 61363",
    5: "IEC 61660 (DC)",
    6: "ANSI/IEEE 946 (DC)",
    7: "VDE 0102 Part 10 (DC) / DIN EN 61660",
}
SC_PUBLISHED: Final[list[str]] = ["1990", "2001", "2016"]
SC_FAULT_TYPE: Final[dict[str, str]] = {  # iopt_shc
    "3psc": "3-Phase Short-Circuit",
    "2psc": "2-Phase Short-Circuit",
    "spgf": "Single Phase to Ground",
    "2pgf": "2-Phase to Ground",
    "spnf": "1-Phase to Neutral",
    "spng": "1-Phase, Neutral to Ground",
    "2pnf": "2-Phase to Neutral",
    "2png": "2-Phase, Neutral to Ground",
    "3pnf": "3-Phase to Neutral",
    "3png": "3-Phase, Neutral to Ground",
    "3rst": "3-Phase Short-Circuit (Unbal.)",
}
SC_CALCULATE: Final[dict[int, str]] = {  # iopt_cur
    0: "max",  # Max. Short-Circuit Currents
    1: "min",  # Min. Short-Circuit Currents
}
SC_BREAK_TIME: Final[dict[int, str]] = {  # iBrkTime
    0: "global",
    1: "min. of local",
    2: "local",
}
SC_AT: Final[dict[int, str]] = {  # iopt_allbus
    0: "User Selection",
    1: "Busbars and Junction Nodes",
    2: "All Busbars",
}
SC_PROTECTION_DEVICES: Final[dict[int, str]] = {  # iopt_prot
    0: "none",
    1: "all",
    2: "main",
    3: "backup",
}
