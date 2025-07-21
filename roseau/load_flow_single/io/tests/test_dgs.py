import warnings

import numpy as np
import shapely

import roseau.load_flow_single as rlfs
from roseau.load_flow.testing import assert_json_close


def test_from_dgs(dgs_network_path):
    # Read DGS
    with warnings.catch_warnings():
        if dgs_network_path.stem == "Line_Without_Type":
            warnings.filterwarnings(
                "ignore", message=r"The network contains lines but it is missing line types", category=UserWarning
            )
            warnings.filterwarnings("ignore", message=r"Unbalanced loads are not supported", category=UserWarning)
        en = rlfs.ElectricalNetwork.from_dgs_file(dgs_network_path)
        # Also make sure use_name_as_id=True works
        en2 = rlfs.ElectricalNetwork.from_dgs_file(dgs_network_path, use_name_as_id=True)
    assert len(en2.buses) == len(en.buses)
    assert len(en2.lines) == len(en.lines)
    assert len(en2.loads) == len(en.loads)
    assert len(en2.sources) == len(en.sources)
    assert len(en2.transformers) == len(en.transformers)
    assert len(en2.switches) == len(en.switches)

    # Check the validity of the network
    en._check_validity(constructed=False)


def test_to_from_dgs_roundtrip():
    bus_mv = rlfs.Bus(
        "MV Bus",
        nominal_voltage=20e3,
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
        max_voltage_level=1.05,
        min_voltage_level=0.95,
    )
    bus1_lv = rlfs.Bus(
        "LV Bus 1",
        nominal_voltage=400,
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
        max_voltage_level=1.1,
        min_voltage_level=0.9,
    )
    bus2_lv = rlfs.Bus(
        "LV Bus 2",
        nominal_voltage=400,
        geometry=shapely.Point(5.738531306019317, 45.18776131177264),
        max_voltage_level=1.1,
        min_voltage_level=0.9,
    )

    tp = rlfs.TransformerParameters.from_catalogue("SE Vegeta AA0Ak 630kVA 20kV 410V Dyn11")
    rlfs.Transformer(
        "MV/LV Transformer",
        bus_hv=bus_mv,
        bus_lv=bus1_lv,
        parameters=tp,
        max_loading=0.9,
        tap=1.025,
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
    )

    lp = rlfs.LineParameters.from_catalogue("U_AL_240")
    rlfs.Line(
        "LV Line",
        bus1=bus1_lv,
        bus2=bus2_lv,
        parameters=lp,
        length=0.6,
        max_loading=0.95,
        geometry=shapely.LineString(
            [
                (5.741095497645757, 45.18848721409608),
                (5.740172817813646, 45.18832086229793),
                (5.7391643072994825, 45.18798815724316),
                (5.738531306019317, 45.18776131177264),
            ]
        ),
    )

    rlfs.Switch(
        "LV Switch",
        bus1=bus1_lv,
        bus2=bus2_lv,
        closed=False,  # Open switch
        geometry=shapely.Point(5.741095497645757, 45.18848721409608),
    )

    rlfs.VoltageSource("MV Grid", bus=bus_mv, voltage=21e3 * np.exp(1j * np.pi / 6))
    rlfs.PowerLoad("LV Load", bus=bus2_lv, power=7e3 + 2e3j)

    en = rlfs.ElectricalNetwork.from_element(bus_mv)
    en2 = rlfs.ElectricalNetwork.from_dgs_dict(en.to_dgs_dict(), use_name_as_id=True)
    assert_json_close(en2.to_dict(), en.to_dict())
