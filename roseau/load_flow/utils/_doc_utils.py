import pandas as pd


def to_markdown(df: pd.DataFrame, *, floatfmt: str = "g", index: bool = True, no_wrap_index: bool = False) -> str:
    """Format a dataframe as markdown for use in the docs.

    Features:
    - Pretty format complex numbers with the same format spec as floats.
    - Right-align numerical columns and left-align other columns.
    - Optionally wrap index in ``<nobr>`` tags to prevent line breaks.

    Args:
        df:
            The dataframe to format.

        floatfmt:
            Format specification used for columns which contain numeric data with a decimal point.
            It is also used for real and imaginary parts of complex numbers.

        index:
            Whether to include the index in the markdown table.

        no_wrap_index:
            Whether to wrap the index in ``<nobr>`` tags.

    Returns:
        A string representing the dataframe formatted as a markdown table.

    Examples:

        Print a results dataframe. Reset the multi-index for better display:

        >>> print(tomarkdown(en.res_buses_voltages.reset_index(), index=False))
        | bus_id          | phase   |          voltage | violated   |   voltage_level | ...
        |:----------------|:--------|-----------------:|:-----------|----------------:| ...
        | MVLV03045       | ab      |    17320.5+10000 | False      |               1 | ...
        | MVLV03045       | bc      |          0-20000 | False      |               1 | ...
        | MVLV03045       | ca      |   -17320.5+10000 | False      |               1 | ...

        Print catalogue of transformer parameters. Avoid line breaks in the index:

        >>> tr_catalogue = rlf.TransformerParameters.get_catalogue().sample(30, random_state=1)
        >>> print(to_markdown(tr_catalogue, no_wrap_index=True))
        | Name                                           | Manufacturer   | Product range   | ...
        |:-----------------------------------------------|:---------------|:----------------| ...
        | <nobr>FT 100kVA 15/20kV(20) 400V Dyn11</nobr>  | FT             |                 | ...
        | <nobr>FT 160kVA 15/20kV(20) 400V Dyn11</nobr>  | FT             |                 | ...

    """
    if df.empty:
        return df.to_markdown(index=index)

    df = df.copy()
    if index and no_wrap_index and pd.api.types.is_string_dtype(df.index):
        df.index = "<nobr>" + df.index + "</nobr>"

    colalign = []
    if index:
        colalign.append("left")
    for c in df.columns:
        if (
            (is_complex_dtype := pd.api.types.is_complex_dtype(df[c]))
            or pd.api.types.is_float_dtype(df[c])
            or pd.api.types.is_integer_dtype(df[c])
        ):
            colalign.append("right")
            if is_complex_dtype:
                df[c] = df[c].apply(lambda x: f"{x.real:{floatfmt}}{x.imag:+{floatfmt}}")
        else:
            colalign.append("left")

    return df.to_markdown(index=index, floatfmt=floatfmt, colalign=colalign)
