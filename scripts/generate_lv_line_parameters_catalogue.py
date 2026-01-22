import math
import statistics
import warnings

import polars as pl

import roseau.load_flow as rlf


def line_parameters(
    type: rlf.LineType, material: rlf.Material, insulator: rlf.Insulator, section: float, insulator_thickness: float
) -> tuple[float, float]:
    """Compute the line parameters (reactance and susceptance) using IEC/NFC approximate formulas.

    Args:
        type:
            The line type (overhead, underground, twisted).

        material:
            The conductor material (copper, aluminium, aluminium alloy).

        insulator:
            The insulator type.

        section:
            The conductor section in mm².

        insulator_thickness:
            The insulator thickness in mm.

    Returns:
        A tuple containing the linear reactance (Ohm/km) and linear susceptance (S/km).
    """
    if type == rlf.LineType.OVERHEAD and (insulator != rlf.Insulator.NONE and insulator_thickness != 0):
        warnings.warn("Overhead lines should not have an insulator or insulator thickness.", stacklevel=2)

    epsilon_r = rlf.constants.EPSILON_R[insulator].m

    #
    # IEC/NFC (approximate) computation
    #
    # Inductance
    radius = math.sqrt(section / math.pi) * 1e-3  # mm -> m
    # Geometric mean radius
    gmr = radius * math.exp(-1 / 4)  # m

    # Geometric mean distance (here distance between conductors in the case of a symmetrical line)
    gmd = 1 if type == rlf.LineType.OVERHEAD else 2 * (radius + insulator_thickness * 1e-3)  # m
    linear_inductance = rlf.constants.MU_0.m / (2 * math.pi) * math.log(gmd / gmr) * 1e3  # H/m -> H/km
    linear_capacitance = epsilon_r / (18 * math.log(gmd / radius))  # µF/km

    linear_reactance = linear_inductance * rlf.constants.OMEGA.m
    linear_susceptance = rlf.constants.OMEGA.m * linear_capacitance * 1e-6

    return linear_reactance, linear_susceptance


def approx[T](x: T, /) -> T:
    """Indicate that the value is approximate, not from a table or measurement."""
    return x


def extrapolate[X: float](table: dict[X, float], x: X) -> None:
    """Extrapolate a value inplace from a table using linear regression.

    Args:
        table:
            A dictionary mapping x values to y values.

        x:
            The x value to extrapolate.
    """
    if x in table:
        warnings.warn(f"Value for x={x} already exists in the table, no extrapolation needed.", stacklevel=2)
        return
    lr = statistics.linear_regression(list(table.keys()), list(table.values()))
    table[x] = x * lr.slope + lr.intercept


def generate_c33209_lv_twisted_parameters() -> pl.DataFrame:
    """Nexans: Network aerial bundled conductors 3-phases+neutral messenger (NF-C-33-209).

    Description
    -----------

    - Messenger
    - Core (1): circular stranded in AGS aluminum alloy, cross-section area 54.6 mm² or 70 mm²
    - Insulation (2): Black XLPE
    - Specifications (54.6 mm²):
    - Nominal cross section: 54.6 mm²,
    - Core diameter: 9.2 mm to 9.6 mm,
    - Insulated core diameter: min. 12.3 mm; max. 13.0 mm, min. breaking load 1660 daN,
    - Elasticity modulus: 62000 MPa,
    - Linear coefficient: 23x10⁶ °C⁻¹.
    - Specifications (70 mm²):
    - Nominal cross section: 70 mm²,
    - Core diameter: 10.0 mm to 10.2 mm,
    - Insulated core diameter: min. 12.9 mm; max. 13.6 mm, min. breaking load 2050 daN,
    - Elasticity modulus: 62000 MPa,
    - Linear coefficient: 23x10⁶ °C⁻¹.
    - Phase or public lighting conductor
    - Core (3): circular stranded (class 2) aluminum.
    - Insulation (4): black extruded XLPE.

    Markings
    --------

    - Neutral: 211 NF C 33-209 211 «manufacturing number», «metric marks» ink printed.
    - Phase 1, 2, 3: the identification number is printed and embossed on insulation.
    - Public lighting: «EP1», «EP2 » is printed and embossed on each conductor.
      «EP3» if three conductors are required.

    Electrical characteristics
    --------------------------

    - Rated voltage: 0.6/1 kV
    - Test voltage: 4 kV AC
    - Resistance to voltage surges: 1.2/50µs with a positive or negative polarity and a peak value
      of 20 kV.

    Correction coefficients
    -----------------------

    To apply to the intensity in accordance with the air temperature

    Ambient. temperature °C | 10   | 15   | 20   | 25   | 30   | 35   | 40   | 45   | 50   | 60   | 70
    Coefficient             | 1.17 | 1.13 | 1.09 | 1.04 | 1.00 | 0.95 | 0.91 | 0.85 | 0.80 | 0.67 | 0.52

    Technical characteristics
    -------------------------

    sections       | d_core_ph | d_core_pl | d_ins_ph | d_ins_pl | diam | weight | r_ph  | r_pl | imax_ph | imax_pl
    -------------- | --------- | --------- | -------- | -------- | ---- | ------ | ----- | ---- | ------- | -------
    3x35+54.6      | 6.8       | -         | 10.0     | -        | 29.0 | 622    | 0.868 | -    | 138     | -
    3x35+54.6+1x16 | 6.8       | 4.6       | 10.0     | 7.0      | 29.0 | 686    | 0.868 | 1.91 | 138     | 83
    3x35+54.6+2x16 | 6.8       | 4.6       | 10.0     | 7.0      | 29.0 | 753    | 0.868 | 1.91 | 138     | 83
    3+50+54.6      | 7.9       | -         | 11.1     | -        | 30.4 | 746    | 0.641 | -    | 168     | -
    3x50+54.6+1x16 | 7.9       | 4.6       | 11.1     | 7.0      | 30.4 | 812    | 0.641 | 1.91 | 168     | 83
    3x50+54.6+2x16 | 7.9       | 4.6       | 11.1     | 7.0      | 30.4 | 877    | 0.641 | 1.91 | 168     | 83
    3x70+54.6      | 9.7       | -         | 13.3     | -        | 34.0 | 954    | 0.443 | -    | 213     | -
    3x70+54.6+1x16 | 9.7       | 4.6       | 13.3     | 7.0      | 34.0 | 1020   | 0.443 | 1.91 | 213     | 83
    3x70+54.6+2x16 | 9.7       | 4.6       | 13.3     | 7.0      | 34.0 | 1085   | 0.443 | 1.91 | 213     | 83
    3x70+70        | 9.7       | -         | 13.3     | -        | 34.3 | 986    | 0.443 | -    | 213     | -
    3x70+70+1x16   | 9.7       | 4.6       | 13.3     | 7.0      | 34.3 | 1051   | 0.443 | 1.91 | 213     | 83
    3x70+70+2x16   | 9.7       | 4.6       | 13.3     | 7.0      | 34.3 | 1117   | 0.443 | 1.91 | 213     | 83
    3x95+70*       | 11.0      | -         | 14.6     | -        | 37.0 | 1228   | 0.343 | -    | 258     | -
    3x95+70+1x16*  | 11.0      | 4.6       | 14.6     | 7.0      | 37.0 | 1294   | 0.343 | 1.91 | 258     | 83
    3x95+70+2x16*  | 11.0      | 4.6       | 14.6     | 7.0      | 37.0 | 1338   | 0.343 | 1.91 | 258     | 83
    3x150+70       | 13.9      | -         | 17.3     | -        | 41.4 | 1698   | 0.206 | -    | 344     | -
    3x150+70+1x16  | 13.9      | 4.6       | 17.3     | 7.0      | 41.4 | 1763   | 0.206 | 1.91 | 344     | 83
    3x150+70+2x16  | 13.9      | 4.6       | 17.3     | 7.0      | 41.4 | 1828   | 0.206 | 1.91 | 344     | 83

    * on demand

    With the following original column names:
    - sections: Core cross section (mm²)
    - d_core_ph: Diameter in mm / Minimum on core / Phase conductor
    - d_core_pl: Diameter in mm / Minimum on core / Public lighting
    - d_ins_ph: Diameter in mm / Minimum insulation / Phase conductor
    - d_ins_pl: Diameter in mm / Minimum insulation / Public lighting
    - diam: Diameter in mm / Bundled conductors (approx.)
    - weight: Weight (kg/km)
    - r_ph: Maximum linear resistance on the core at 20 °C (Ω/km) / Phase conductor
    - r_pl: Maximum linear resistance on the core at 20 °C (Ω/km) / Public lighting
    - imax_ph: Current through conductors in continuous operation (A) / Phase conductor
    - imax_pl: Current through conductors in continuous operation (A) / Public lighting


    Full table Technical characteristics
    ------------------------------------

    sections       | imax_ph | imax_pl | ext_diam | weight | du   | r_ph  | r_pl | length | reel
    -------------- | ------- | ------- | -------- | ------ | ---- | ----- | ---- | ------ | ----
    3x25+54.6      | 112     | -       | 24       | 531    | 2.20 | 1.200 | -    | 2000   | CF
    3x25+54.6+1x16 | 112     | 83      | 25       | 600    | 2.20 | 1.200 | 1.91 | 2000   | CF
    3x25+54.6+2x16 | 112     | 83      | 27.5     | 670    | 2.20 | 1.200 | 1.91 | 2000   | CF
    3x35+54.6      | 138     | -       | 24.6     | 641    | 1.65 | 0.868 | -    | 2000   | CF
    3x35+54.6+1x16 | 138     | 83      | 25.5     | 710    | 1.65 | 0.868 | 1.91 | 2000   | CF
    3x35+54.6+2x16 | 138     | 83      | 27.5     | 779    | 1.65 | 0.868 | 1.91 | 2000   | CF
    3x50+54.6      | 168     | -       | 27       | 770    | 1.27 | 0.641 | -    | 2000   | DF
    3x50+54.6+1x16 | 168     | 83      | 28.5     | 839    | 1.27 | 0.641 | 1.91 | 2000   | DF
    3x50+54.6+2x16 | 168     | 83      | 30       | 907    | 1.27 | 0.641 | 1.91 | 2000   | DF
    3x70+54.6      | 213     | -       | 30       | 985    | 0.87 | 0.443 | -    | 2000   | EF
    3x70+54.6+1x16 | 213     | 83      | 32.2     | 1054   | 0.87 | 0.443 | 1.91 | 2000   | EF
    3x70+54.6+2x16 | 213     | 83      | 33       | 1122   | 0.87 | 0.443 | 1.91 | 2000   | EF
    3x70+70        | 213     | -       | 32       | 1019   | 0.87 | 0.443 | -    | 1000   | CF
    3x70+70+1x16   | 213     | 83      | 33       | 1087   | 0.87 | 0.443 | 1.91 | 1000   | CF
    3x70+70+2x16   | 213     | 83      | 34       | 1155   | 0.87 | 0.443 | 1.91 | 1000   | CF
    3x95+70        | 258     | -       | 35       | 1264   | 0.67 | 0.320 | -    | 1000   | CF
    3x95+70+1x16   | 258     | 83      | 36       | 1331   | 0.67 | 0.320 | 1.91 | 1000   | CF
    3x95+70+2x16   | 258     | 83      | 37       | 1398   | 0.67 | 0.320 | 1.91 | 1000   | DF
    3x120+70       | 300     | -       | 38       | 1488   | 0.55 | 0.253 | -    | 1000   | DF
    3x120+70+1x16  | 300     | 83      | 39       | 1555   | 0.55 | 0.253 | 1.91 | 1000   | DF
    3x120+70+2x16  | 300     | 83      | 40       | 1623   | 0.55 | 0.253 | 1.91 | 1000   | DF
    3x150+70       | 344     | -       | 40       | 1731   | 0.46 | 0.206 | -    | 1000   | EF
    3x150+70+1x16  | 344     | 83      | 41       | 1799   | 0.46 | 0.206 | 1.91 | 1000   | EF
    3x150+70+2x16  | 344     | 83      | 42       | 1866   | 0.46 | 0.206 | 1.91 | 1000   | EF
    3x120+95       | 300     | -       | 39       | 1569   | 0.55 | 0.253 | -    | 1000   | EF
    3x120+95+1x16  | 300     | 83      | 40       | 1637   | 0.55 | 0.253 | 1.91 | 1000   | EF
    3x120+95+2x16  | 300     | 83      | 41       | 1704   | 0.55 | 0.253 | 1.91 | 1000   | EF
    3x150+95       | 344     | -       | 42       | 1812   | 0.46 | 0.206 | -    | 1000   | EF
    3x150+95+1x16  | 344     | 83      | 43       | 1880   | 0.46 | 0.206 | 1.91 | 1000   | EF
    3x150+95+2x16  | 344     | 83      | 44       | 1948   | 0.46 | 0.206 | 1.91 | 1000   | EF

    With the following original column names:
    - sections: Core cross section (mm²)
    - imax_ph: Current through conductors in continuous operation (A) / Phase conductor
    - imax_pl: Current through conductors in continuous operation (A) / Public lighting
    - ext_diam: External diameter (mm)
    - weight: Weight (kg/km)
    - du: Voltage drop with cos(φ) = 0.8 (V/A/km)
    - r_ph: Maximum linear resistance on the core at 20 °C (Ω/km) / Phase conductor
    - r_pl: Maximum linear resistance on the core at 20 °C (Ω/km) / Public lighting
    - length: Length (m)
    - reel: Reel type
    """
    header = ("sections", "imax_ph", "ext_diam", "weight", "du", "r_ph")
    data = [
        ("3x25+54.6", 112, 24, 531, 2.20, 1.200),
        ("3x35+54.6", 138, 24.6, 641, 1.65, 0.868),
        ("3x50+54.6", 168, 27, 770, 1.27, 0.641),
        ("3x70+54.6", 213, 30, 985, 0.87, 0.443),
        ("3x70+70", 213, 32, 1019, 0.87, 0.443),
        ("3x95+70", 258, 35, 1264, 0.67, 0.320),
        ("3x120+70", 300, 38, 1488, 0.55, 0.253),
        ("3x150+70", 344, 40, 1731, 0.46, 0.206),
        ("3x120+95", 300, 39, 1569, 0.55, 0.253),
        ("3x150+95", 344, 42, 1812, 0.46, 0.206),
    ]
    c33209_phase_insulation_thickness = {
        # min and max of: insulated core diameter - core diameter (mm)
        # we take the max insulation thickness to calculate the max inductance; in line with
        # the max resistance value in the table
        16: max((7.0 - 4.6, 7.8 - 5.1)),
        25: max((8.6 - 5.8, 9.4 - 6.3)),
        35: max((10.0 - 6.8, 10.9 - 7.3)),
        50: max((11.1 - 7.9, 12.0 - 8.4)),
        70: max((13.3 - 9.7, 14.2 - 10.2)),
        95: max((14.6 - 11.0, 15.7 - 12.0)),
        120: max((15.6 - 12.0, 16.7 - 13.1)),
        150: max((17.3 - 13.9, 18.6 - 15.0)),
    }
    c33209_neutral_messenger_insulation_thickness = {
        # min and max of: insulated core diameter - core diameter (mm)
        # we take the max insulation thickness to calculate the max inductance; in line with
        # the max resistance value in the table
        54.6: max((12.3 - 9.2, 13.0 - 9.6)),
        70.0: max((12.9 - 10.0, 13.6 - 10.2)),
        95.0: max((15.3 - 12.2, 16.3 - 12.9)),
    }
    c33209_neutral_messenger_resistance = {
        54.6: 0.63,
        70: 0.50,
        95: 0.343,
    }
    twisted_df = (
        pl.DataFrame(data, schema=header, orient="row")
        .select(
            name=pl.format("T_AL_{}", pl.col("sections")),
            type=pl.lit(rlf.LineType.TWISTED),
            material=pl.lit(rlf.Material.AL),
            material_neutral=pl.lit(rlf.Material.AM),
            insulator=pl.lit(rlf.Insulator.XLPE),
            insulator_neutral=pl.lit(rlf.Insulator.XLPE),
            section=pl.col("sections").str.extract(r"^3x(\d+)\+\d+(?:\.\d+)?$", 1).cast(pl.Int64),
            section_neutral=pl.col("sections").str.extract(r"^3x\d+\+(\d+(?:\.\d+)?)$", 1).cast(pl.Float64),
            resistance=pl.col("r_ph"),
            resistance_neutral=pl.lit(None, dtype=pl.Float64),  # Computed below
            reactance=pl.lit(None, dtype=pl.Float64),  # Computed below
            reactance_neutral=pl.lit(None, dtype=pl.Float64),  # Computed below
            susceptance=pl.lit(None, dtype=pl.Float64),  # Computed below
            susceptance_neutral=pl.lit(None, dtype=pl.Float64),  # Computed below
            ampacity=pl.col("imax_ph"),
            # The neutral is usually assigned the same ampacity as the phase conductors
            ampacity_neutral=pl.col("imax_ph"),
        )
        .with_columns(
            resistance_neutral=pl.col("section_neutral").replace_strict(c33209_neutral_messenger_resistance),
        )
    )
    twisted_params = {"reactance": [], "susceptance": [], "reactance_neutral": [], "susceptance_neutral": []}
    for row in twisted_df.iter_rows(named=True):
        insulator_thickness = c33209_phase_insulation_thickness[row["section"]]
        reactance, susceptance = line_parameters(
            type=row["type"],
            material=row["material"],
            insulator=row["insulator"],
            section=row["section"],
            insulator_thickness=insulator_thickness,
        )
        insulator_thickness_neutral = c33209_neutral_messenger_insulation_thickness[row["section_neutral"]]
        reactance_neutral, susceptance_neutral = line_parameters(
            type=row["type"],
            material=row["material_neutral"],
            insulator=row["insulator_neutral"],
            section=row["section_neutral"],
            insulator_thickness=insulator_thickness_neutral,
        )
        twisted_params["reactance"].append(reactance)
        twisted_params["susceptance"].append(susceptance)
        twisted_params["reactance_neutral"].append(reactance_neutral)
        twisted_params["susceptance_neutral"].append(susceptance_neutral)
    twisted_df = twisted_df.with_columns(**{k: pl.Series(v) for k, v in twisted_params.items()})
    return twisted_df


def generate_c33210_lv_underground_parameters() -> pl.DataFrame:
    """Nexans: Distribution cable 3 conductors + neutral (NF-C-33-210).

    Description
    -----------

    1. Core (Neutral conductor): solid or stranded circular (class 2) aluminum depending on type.
    2. Protection (Neutral conductor): lead sheath
    3. Core (Phase conductor): aluminum stranded circular (class 2) of solid round, cross section 50 mm²;
       stranded sector-shaped (class 2), cross section 95 to 240 mm².
    4. Insulation (Phase conductor): black XLPE.
    5. Watertight textile material
    6. Armour: two lapped galvanized mild steel tapes
    7. Filler: PVC material only 50 mm².
    8. Sheath: black PVC, special antitermite treatment possible.

    Table of marking
    ----------------

    Section    | Marking + Manufact. nb / manufact. year / metric marks / manufact. date.
    ---------- | ------------------------------------------------------------------------
    3x50+1x50  | H1 XDV-AR 3x50+1x50 DISTRICABLE ® 211 NF C 33-210
    3x95+1x50  | H1 XDV-AS 3x95+1x50 DISTRICABLE ® 211 NF C 33-210
    3x150+1x70 | H1 XDV-AS 3x150+1x70 DISTRICABLE ® 211 NF C 33-210
    3x240+1x95 | H1 XDV-AS 3x240+1x95 DISTRICABLE ® 211 NF C 33-210

    Correction coefficients
    -----------------------

    To apply to the current in accordance with the ground temperature and its thermal resistivity

    Ground temp. | Ground thermal resistivity (K.m/W) | . | . | . | . | . | .
    ------------ | ---------------------------------- | - | - | - | - | - | -
    (°C)         | 0.7  | 0.85 | 1    | 1.2  | 1.5  | 2    | 2.5
    10           | 1.19 | 1.12 | 1.07 | 1.01 | 0.93 | 0.81 | 0.77
    15           | 1.16 | 1.09 | 1.04 | 0.98 | 0.90 | 0.79 | 0.74
    20           | 1.13 | 1.05 | 1.00 | 0.94 | 0.86 | 0.76 | 0.70
    25           | 1.08 | 1.01 | 0.96 | 0.90 | 0.83 | 0.72 | 0,66
    30           | 1.05 | 0.98 | 0.93 | 0.85 | 0.78 | 0.69 | 0.63
    35           | 1.00 | 0.93 | 0.89 | 0.82 | 0.75 | 0.65 | 0.60

    Technical characteristics
    -------------------------

    sections   | diam_min | diam_max | weight | bend_rad | r_ph  | r_neu | imax_bur | imax_air | delta_u
    ---------- | -------- | -------- | ------ | -------- | ----- | ----- | -------- | -------- | -------
    3x50+1x50  | 25.5     | 33.5     | 1670   | 270      | 0.641 | 0.641 | 160      | 149      | 1.18
    3x95+1x50  | 30.0     | 38.6     | 1845   | 310      | 0.320 | 0.641 | 234      | 241      | 0.64
    3x150+1x70 | 36.5     | 48.5     | 2570   | 390      | 0.206 | 0.443 | 300      | 324      | 0.51
    3x240+1x95 | 45.5     | 58.7     | 3900   | 470      | 0.125 | 0.320 | 388      | 439      | 0.31

    With the following original column names:
    - sections: Sections (mm²)
    - diam_min: Overall Diameter (mm) / minimum
    - diam_max: Overall Diameter (mm) / maximum
    - weight: Weight (kg/km)
    - bend_rad: Minimum bending radius (mm)
    - r_ph: Max. linear resistance at 20 °C (Ω/km) / Phase Cond.
    - r_neu: Max. linear resistance at 20 °C (Ω/km) / Neutral Cond.
    - imax_bur: Current (A) / Buried cables
    - imax_air: Current (A) / Open air
    - delta_u: Voltage drop between phases Cos ϕ = 0,8 (V/A.km)
    """
    header = (
        "sections",
        "diam_min",
        "diam_max",
        "weight",
        "bend_rad",
        "r_ph",
        "r_neu",
        "imax_bur",
        "imax_air",
        "delta_u",
    )
    data = [
        ("3x50+1x50", 25.5, 33.5, 1670, 270, 0.641, 0.641, 160, 149, 1.18),
        ("3x95+1x50", 30.0, 38.6, 1845, 310, 0.320, 0.641, 234, 241, 0.64),
        ("3x150+1x70", 36.5, 48.5, 2570, 390, 0.206, 0.443, 300, 324, 0.51),
        ("3x150+1x150", 38.5, 50.8, approx(3000), 390, 0.206, 0.206, 300, 324, 0.51),  # Source: NF-C-33-210
        ("3x240+1x95", 45.5, 58.7, 3900, 470, 0.125, 0.320, 388, 439, 0.31),
    ]

    nexans_underground_cable_reactance = {95: 0.08, 150: 0.08, 240: 0.08}  # Ohm/km
    nexans_underground_cable_capacitance = {95: 0.58, 150: 0.63, 240: 0.67}  # µF/km
    # c33210_phase_insulation_thickness = {50: 1.0, 95: 1.1, 150: 1.4, 240: 1.7}
    # c33210_neutral_insulation_thickness = {50: 0.9, 70: 0.9, 95: 0.9, 150: 0.9}
    extrapolate(nexans_underground_cable_reactance, 50)
    extrapolate(nexans_underground_cable_reactance, 70)
    extrapolate(nexans_underground_cable_capacitance, 50)
    extrapolate(nexans_underground_cable_capacitance, 70)

    underground_df = (
        pl.DataFrame(data, schema=header, orient="row")
        .select(
            name=pl.format("U_AL_{}", pl.col("sections").str.replace(r"\+1x", "+")),
            type=pl.lit(rlf.LineType.UNDERGROUND),
            material=pl.lit(rlf.Material.AL),
            material_neutral=pl.lit(rlf.Material.AL),
            insulator=pl.lit(rlf.Insulator.XLPE),
            insulator_neutral=pl.lit(rlf.Insulator.XLPE),  # maybe NONE?
            section=pl.col("sections").str.extract(r"^3x(\d+)\+1x\d+$", 1).cast(pl.Int64),
            section_neutral=pl.col("sections").str.extract(r"^3x\d+\+1x(\d+)$", 1).cast(pl.Float64),
            resistance=pl.col("r_ph"),
            resistance_neutral=pl.col("r_neu"),
            reactance=pl.lit(None, dtype=pl.Float64),  # Computed below
            reactance_neutral=pl.lit(None, dtype=pl.Float64),  # Computed below
            susceptance=pl.lit(None, dtype=pl.Float64),  # Computed below
            susceptance_neutral=pl.lit(None, dtype=pl.Float64),  # Computed below
            ampacity=pl.col("imax_bur"),
            ampacity_neutral=pl.col("imax_bur"),  # The neutral is usually assigned the same ampacity
        )
        .with_columns(
            reactance=pl.col("section").replace_strict(nexans_underground_cable_reactance),
            reactance_neutral=pl.col("section_neutral").replace_strict(nexans_underground_cable_reactance),
            susceptance=(
                pl.col("section").replace_strict(nexans_underground_cable_capacitance) * rlf.constants.OMEGA.m * 1e-6
            ),
            susceptance_neutral=(
                pl.col("section_neutral").replace_strict(nexans_underground_cable_capacitance)
                * rlf.constants.OMEGA.m
                * 1e-6
            ),
        )
    )
    return underground_df


if __name__ == "__main__":
    import io

    twisted_df = generate_c33209_lv_twisted_parameters()
    underground_df = generate_c33210_lv_underground_parameters()
    all_df = pl.concat([twisted_df, underground_df], how="vertical")

    s = io.StringIO()
    all_df.with_columns(
        # Round float columns for better CSV readability
        pl.col(pl.Float64).round(10)
    ).write_csv(s)
    print(s.getvalue())
