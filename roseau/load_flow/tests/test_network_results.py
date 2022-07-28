import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from roseau.load_flow import AbstractTransformer, Switch
from roseau.load_flow.models.core import PotentialRef
from roseau.load_flow.network.electrical_network import ElectricalNetwork
from roseau.load_flow.utils.exceptions import RoseauLoadFlowException

EPSILON: float = 1e-7
MAX_ITERATIONS: int = 20


def test_electrical_network(all_network_path, all_network_result):  # noqa: C901
    try:
        # Create an electrical network
        en = ElectricalNetwork.from_json(all_network_path)
        # Solve the load flow
        en.solve_load_flow(max_iterations=MAX_ITERATIONS, epsilon=EPSILON)
    except RoseauLoadFlowException as e:
        if "is not implemented yet..." in e.args[0]:
            pytest.xfail(f"Need to implement other components: {e.args[0]}")
            return
        raise

    # Read the results' data frame
    results_df = pd.read_csv(all_network_result, index_col=["id_eb", "phase"])
    results_df = results_df.assign(
        v=(results_df["re_v"] + 1j * results_df["im_v"]),
        i1=(results_df["re_i1"] + 1j * results_df["im_i1"]),
        i2=(results_df["re_i2"] + 1j * results_df["im_i2"]),
    )
    results_df.sort_index(inplace=True)

    # kirchhoff_residuals = en.kirchhoff_residuals
    # npt.assert_allclose(kirchhoff_residuals, np.zeros((len(kirchhoff_residuals),)), atol=1e-4, rtol=1e-5)

    for bus_id, df in results_df.groupby(by="id_eb"):
        # Warning: careful with atol and rtol...
        if df["v"].values.shape[0] < en.bus_potentials(id=bus_id).shape[0]:  # TODO refactor
            bus_potentials = np.resize(en.bus_potentials(id=bus_id), 3)
        else:
            bus_potentials = en.bus_potentials(id=bus_id)
        npt.assert_allclose(bus_potentials, df["v"].values, atol=1e-5, rtol=1e-7)

    for branch in en.branches.values():
        id_bus1 = branch.connected_elements[0].id
        id_bus2 = branch.connected_elements[1].id

        if isinstance(branch, Switch) or isinstance(branch, AbstractTransformer):
            continue

        i1, i2 = branch.currents

        max_bus = max(id_bus1, id_bus2)
        if np.isnan(results_df.loc[max_bus, "i1"].values).all():
            npt.assert_allclose(
                results_df.loc[max_bus, "i1"].values, results_df.loc[max_bus, "i2"].values, equal_nan=True
            )
            # The direction of branches is not suitable to store the data using Victor's file format
        else:
            if max_bus == id_bus2:
                i1_tag = "i1"
                i2_tag = "i2"
            else:
                i1_tag = "i2"
                i2_tag = "i1"
            re_i1_check = results_df.loc[(max_bus,), "re_" + i1_tag].values
            if np.isnan(re_i1_check).any():
                re_i1_check = re_i1_check[:-1]  # Neutral which does not exist
            im_i1_check = results_df.loc[(max_bus,), "im_" + i1_tag].values
            if np.isnan(im_i1_check).any():
                im_i1_check = im_i1_check[:-1]  # Neutral which does not exist
            re_i2_check = results_df.loc[(max_bus,), "re_" + i2_tag].values
            if np.isnan(re_i2_check).any():
                re_i2_check = re_i2_check[:-1]  # Neutral which does not exist
            im_i2_check = results_df.loc[(max_bus,), "im_" + i2_tag].values
            if np.isnan(im_i2_check).any():
                im_i2_check = im_i2_check[:-1]  # Neutral which does not exist
            npt.assert_allclose(re_i1_check, i1.real, atol=1e-3, rtol=1e-5)  # Warning: careful with atol and rtol...
            npt.assert_allclose(im_i1_check, i1.imag, atol=1e-3, rtol=1e-5)  # Warning: careful with atol and rtol...
            npt.assert_allclose(re_i2_check, i2.real, atol=1e-3, rtol=1e-5)  # Warning: careful with atol and rtol...
            npt.assert_allclose(im_i2_check, i2.imag, atol=1e-3, rtol=1e-5)  # Warning: careful with atol and rtol...

    for special_element in en.special_elements:
        if isinstance(special_element, PotentialRef):
            npt.assert_allclose(special_element.current.real, 0.0, atol=1e-7)
            npt.assert_allclose(special_element.current.imag, 0.0, atol=1e-7)


def test_network_io(some_network_path, some_network_result):

    try:
        # Create an electrical network
        en = ElectricalNetwork.from_json(some_network_path)
        # Solve the load flow
        en.solve_load_flow(max_iterations=MAX_ITERATIONS, epsilon=EPSILON)
    except RoseauLoadFlowException as e:
        if "is not implemented yet..." in e.args[0]:
            pytest.xfail(f"Need to implement other components: {e.args[0]}")
            return
        raise

    buses_results, branches_results = en.results

    # Check the buses results
    assert isinstance(buses_results, pd.DataFrame)
    assert buses_results.index.names == ["bus_id", "phase"]
    assert buses_results.columns.tolist() == ["potential"]

    # Check the branches results
    assert isinstance(branches_results, pd.DataFrame)
    assert branches_results.index.names == ["branch_id", "phase"]
    assert branches_results.columns.tolist() == ["current1", "current2"]

    # Check the results
    expected_results = pd.read_csv(some_network_result).set_index(["id_eb", "phase"])

    # Build the expected results' data frames
    expected_buses_results: pd.DataFrame = expected_results.loc[:, ["re_v", "im_v"]]
    expected_buses_results.index.set_names(names=["bus_id", "phase"], inplace=True)
    expected_buses_results.loc[:, "potential"] = (
        expected_buses_results.loc[:, "re_v"] + 1j * expected_buses_results.loc[:, "im_v"]
    )
    expected_buses_results.drop(columns=["re_v", "im_v"], inplace=True)
    if len(buses_results) == len(expected_buses_results) + 1:
        expected_buses_results.at[(1, "n"), "potential"] = 0j  # Slack bus neutral connected to ground

    expected_branches_results: pd.DataFrame = expected_results.loc[:, ["re_i1", "im_i1", "re_i2", "im_i2"]]

    expected_branches_results["branch_id"] = None
    for branch_name, branch in en.branches.items():
        bus2 = branch.connected_elements[1].id
        expected_branches_results.loc[(bus2, slice(None)), "branch_id"] = branch_name
    expected_branches_results = (
        expected_branches_results.dropna(subset=["branch_id"]).reset_index().set_index(["branch_id", "phase"])
    )
    expected_branches_results.loc[:, "current1"] = (
        expected_branches_results.loc[:, "re_i1"] + 1j * expected_branches_results.loc[:, "im_i1"]
    )
    expected_branches_results.loc[:, "current2"] = (
        expected_branches_results.loc[:, "re_i2"] + 1j * expected_branches_results.loc[:, "im_i2"]
    )
    expected_branches_results.drop(columns=["bus_id", "re_i1", "im_i1", "re_i2", "im_i2"], inplace=True)

    # Check
    assert_frame_equal(buses_results, expected_buses_results, check_like=True)
    for idx in branches_results.index:
        if idx in expected_branches_results.index:
            if not np.isnan(expected_branches_results.loc[idx, "current1"]):
                assert np.isclose(
                    branches_results.at[idx, "current1"],
                    expected_branches_results.at[idx, "current1"],
                    atol=1e-2,
                    rtol=1e-5,
                )
            assert np.isclose(
                branches_results.at[idx, "current2"],
                expected_branches_results.at[idx, "current2"],
                atol=1e-2,
                rtol=1e-5,
            )

    # Recreate network from dict
    en_dict = en.to_dict()
    en = ElectricalNetwork.from_dict(en_dict)
    en.solve_load_flow()
    res = en.dict_results()

    # Check dict results
    for bus_res in res["buses"]:
        for phase, potential_list in bus_res["potentials"].items():
            potential = potential_list[0] + 1j * potential_list[1]
            npt.assert_almost_equal(potential, buses_results.at[(bus_res["id"], phase[1]), "potential"])
