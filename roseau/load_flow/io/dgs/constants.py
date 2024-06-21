from typing import Final, Literal, TypeAlias

from roseau.load_flow.utils import ConductorType, InsulatorType, LineType

# Lines
LINE_TYPES: Final[dict[int, LineType]] = {
    0: LineType.UNDERGROUND,  # inAir=Ground
    1: LineType.OVERHEAD,  # inAir=Air
}
CONDUCTOR_TYPES: Final[dict[int, ConductorType]] = {
    0: ConductorType.AL,
    1: ConductorType.CU,
    2: ConductorType.AM,
    3: ConductorType.AA,
    4: ConductorType.LA,
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
GENERAL_LOAD_INPUT_MODE: Final[dict[str, str]] = {
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
GEN_STAT_INPUT_MODE: Final[dict[str, str]] = {
    "DEF": ("pgini", "qgini"),  # Can the default be changed?
    "PQ": ("pgini", "qgini"),
    "PC": ("pgini", "cosgini", "pf_recap"),
    "SC": ("sgini", "cosgini", "pf_recap"),
    "QC": ("qgini", "cosgini", "pf_recap"),
    "SP": ("sgini", "pgini", "pf_recap"),
    "SQ": ("sgini", "qgini", "p_direc"),
}

# Buses
BUS_PHASES: Final[dict[str, str]] = {
    0: "abc",  # "ABC"
    1: "abcn",  # "ABC-N"
    # 2: "ab",  # "BI" # which phases?
    # 3: "abn",  # "BI-N" # which phases?
    # 4: "ab",  # "2PH" # which phases?
    # 5: "abn",  # "2PH-N" # which phases?
    # 6: "a",  # "1PH" # Not allowed in RLF
    # 7: "an",  # "1PH-N" # which phases?
    # 8: "n",  # "N" # Not allowed in RLF
}
