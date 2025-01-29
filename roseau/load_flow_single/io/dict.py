"""
This module is not for public use.

Use the `ElectricalNetwork.from_dict` and `ElectricalNetwork.to_dict` methods to serialize networks
from and to dictionaries, or the methods `ElectricalNetwork.from_json` and `ElectricalNetwork.to_json`
to read and write networks from and to JSON files.
"""

import copy
import logging
import warnings
from typing import TYPE_CHECKING

from roseau.load_flow import Insulator, Material, RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.io.dict import NETWORK_JSON_VERSION as NETWORK_JSON_VERSION
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow.utils import find_stack_level
from roseau.load_flow_single.models import (
    AbstractLoad,
    Bus,
    Line,
    LineParameters,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)

if TYPE_CHECKING:
    from roseau.load_flow_single.network import ElectricalNetwork

logger = logging.getLogger(__name__)


def network_from_dict(
    data: JsonDict, *, include_results: bool = True
) -> tuple[
    dict[Id, Bus],
    dict[Id, Line],
    dict[Id, Transformer],
    dict[Id, Switch],
    dict[Id, AbstractLoad],
    dict[Id, VoltageSource],
    bool,
]:
    """Create the electrical network elements from a dictionary.

    Args:
        data:
            The dictionary containing the network data.

        include_results:
            If True (default) and the results of the load flow are included in the dictionary,
            the results are also loaded into the network.

    Returns:
        The buses, lines, transformers, switches, loads, and sources to construct the electrical
        network and a boolean indicating if the network has results.
    """
    data = copy.deepcopy(data)  # Make a copy to avoid modifying the original

    # Check that the network is single phase with a clear error message
    is_multiphase = data.get("is_multiphase", True)
    if is_multiphase:
        raise AssertionError(
            "Trying to import a multi-phase network as a single-phase network. Did you mean to use "
            "`rlf.ElectricalNetwork` instead of `rlfs.ElectricalNetwork`?"
        )

    # Check the version, 3 was the first version to support RLFS
    version = data["version"]
    assert version >= 3, f"Unsupported network file version {version}, expected >=3."
    assert version <= NETWORK_JSON_VERSION, (
        f"Unsupported network file version {version}, expected <={NETWORK_JSON_VERSION}."
    )
    if version < NETWORK_JSON_VERSION:
        warnings.warn(
            f"Got an outdated network file (version {version}), trying to update to the current format "
            f"(version {NETWORK_JSON_VERSION}). Please save the network again.",
            category=UserWarning,
            stacklevel=find_stack_level(),
        )
        if version == 3:
            data = v3_to_v4_converter(data)
    assert data["version"] == NETWORK_JSON_VERSION, (
        f"Did not apply all JSON version converters, got {data['version']}, expected {NETWORK_JSON_VERSION}."
    )

    # Track if ALL results are included in the network
    has_results = include_results

    # Lines and transformers parameters
    lines_params = {
        lp["id"]: LineParameters.from_dict(data=lp, include_results=include_results) for lp in data["lines_params"]
    }
    transformers_params = {
        tp["id"]: TransformerParameters.from_dict(data=tp, include_results=include_results)
        for tp in data["transformers_params"]
    }

    # Buses, loads and sources
    buses: dict[Id, Bus] = {}
    for bus_data in data["buses"]:
        bus = Bus.from_dict(data=bus_data, include_results=include_results)
        buses[bus.id] = bus
        has_results = has_results and not bus._no_results
    loads: dict[Id, AbstractLoad] = {}
    for load_data in data["loads"]:
        load_data["bus"] = buses[load_data["bus"]]
        load = AbstractLoad.from_dict(data=load_data, include_results=include_results)
        loads[load.id] = load
        has_results = has_results and not load._no_results
    sources: dict[Id, VoltageSource] = {}
    for source_data in data["sources"]:
        source_data["bus"] = buses[source_data["bus"]]
        source = VoltageSource.from_dict(data=source_data, include_results=include_results)
        sources[source.id] = source
        has_results = has_results and not source._no_results

    # Lines
    lines_dict: dict[Id, Line] = {}
    for line_data in data["lines"]:
        line_data["bus1"] = buses[line_data["bus1"]]
        line_data["bus2"] = buses[line_data["bus2"]]
        line_data["parameters"] = lines_params[line_data.pop("params_id")]
        line = Line.from_dict(data=line_data, include_results=include_results)
        lines_dict[line.id] = line
        has_results = has_results and not line._no_results

    # Transformers
    transformers_dict: dict[Id, Transformer] = {}
    for transformer_data in data["transformers"]:
        transformer_data["bus_hv"] = buses[transformer_data["bus_hv"]]
        transformer_data["bus_lv"] = buses[transformer_data["bus_lv"]]
        transformer_data["parameters"] = transformers_params[transformer_data.pop("params_id")]
        transformer = Transformer.from_dict(data=transformer_data, include_results=include_results)
        transformers_dict[transformer.id] = transformer
        has_results = has_results and not transformer._no_results

    # Switches
    switches_dict: dict[Id, Switch] = {}
    for switch_data in data["switches"]:
        switch_data["bus1"] = buses[switch_data["bus1"]]
        switch_data["bus2"] = buses[switch_data["bus2"]]
        switch = Switch.from_dict(data=switch_data, include_results=include_results)
        switches_dict[switch.id] = switch
        has_results = has_results and not switch._no_results

    return buses, lines_dict, transformers_dict, switches_dict, loads, sources, has_results


def network_to_dict(en: "ElectricalNetwork", *, include_results: bool) -> JsonDict:
    """Return a dictionary of the current network data.

    Args:
        en:
            The electrical network.

        include_results:
            If True (default), the results of the load flow are included in the dictionary.
            If no results are available, this option is ignored.

    Returns:
        The created dictionary.
    """
    # Export the buses, loads and sources
    buses: list[JsonDict] = []
    loads: list[JsonDict] = []
    sources: list[JsonDict] = []
    for bus in en.buses.values():
        buses.append(bus.to_dict(include_results=include_results))
        for element in bus._connected_elements:
            if isinstance(element, AbstractLoad):
                assert element.bus is bus
                loads.append(element.to_dict(include_results=include_results))
            elif isinstance(element, VoltageSource):
                assert element.bus is bus
                sources.append(element.to_dict(include_results=include_results))

    # Export the lines with their parameters
    lines: list[JsonDict] = []
    lines_params_dict: dict[Id, LineParameters] = {}
    for line in en.lines.values():
        lines.append(line.to_dict(include_results=include_results))
        params_id = line.parameters.id
        if params_id in lines_params_dict and line.parameters != lines_params_dict[params_id]:
            msg = f"There are multiple line parameters with id {params_id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_LINE_PARAMETERS_DUPLICATES)
        lines_params_dict[line.parameters.id] = line.parameters

    # Export the transformers with their parameters
    transformers: list[JsonDict] = []
    transformers_params_dict: dict[Id, TransformerParameters] = {}
    for transformer in en.transformers.values():
        transformers.append(transformer.to_dict(include_results=include_results))
        params_id = transformer.parameters.id
        if params_id in transformers_params_dict and transformer.parameters != transformers_params_dict[params_id]:
            msg = f"There are multiple transformer parameters with id {params_id!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(
                msg=msg, code=RoseauLoadFlowExceptionCode.JSON_TRANSFORMER_PARAMETERS_DUPLICATES
            )
        transformers_params_dict[params_id] = transformer.parameters

    # Export the switches
    switches = [switch.to_dict(include_results=include_results) for switch in en.switches.values()]

    # Line parameters
    line_params: list[JsonDict] = []
    for lp in lines_params_dict.values():
        line_params.append(lp.to_dict(include_results=include_results))
    line_params.sort(key=lambda x: (type(x["id"]).__name__, str(x["id"])))  # Always keep the same order

    # Transformer parameters
    transformer_params: list[JsonDict] = []
    for tp in transformers_params_dict.values():
        transformer_params.append(tp.to_dict(include_results=include_results))
    transformer_params.sort(key=lambda x: (type(x["id"]).__name__, str(x["id"])))  # Always keep the same order

    res = {
        "version": NETWORK_JSON_VERSION,
        "is_multiphase": False,
        "buses": buses,
        "lines": lines,
        "transformers": transformers,
        "switches": switches,
        "loads": loads,
        "sources": sources,
        "lines_params": line_params,
        "transformers_params": transformer_params,
    }
    return res


def v3_to_v4_converter(data: JsonDict) -> JsonDict:
    assert data["version"] == 3, data["version"]
    loads = []
    for load in data["loads"]:
        # Remove the flexible power results
        if "results" in load and "flexible_power" in load["results"]:
            del load["results"]["flexible_power"]
        loads.append(load)

    sources = []
    for source in data["sources"]:
        # Add source type
        source["type"] = "voltage"
        sources.append(source)

    line_params = []
    for line_param_data in data["lines_params"]:
        # Normalize the insulator and material types
        if (material := line_param_data.pop("material", None)) is not None:
            line_param_data["material"] = Material(material).name
        if (insulator := line_param_data.pop("insulator", None)) is not None:
            line_param_data["insulator"] = Insulator(insulator).name
        line_params.append(line_param_data)

    buses_dict = {b["id"]: b for b in data["buses"]}

    transformers = []
    for tr_data in data["transformers"]:
        # Handle renamed keys
        tr_data["bus_hv"] = tr_data.pop("bus1")
        tr_data["bus_lv"] = tr_data.pop("bus2")
        if "results" in tr_data:
            tr_data["results"]["current_hv"] = tr_data["results"].pop("current1")
            tr_data["results"]["current_lv"] = tr_data["results"].pop("current2")
        # Handle missing results
        if "results" in tr_data:
            tr_data["results"]["voltage_hv"] = buses_dict[tr_data["bus_hv"]]["results"]["voltage"]
            tr_data["results"]["voltage_lv"] = buses_dict[tr_data["bus_lv"]]["results"]["voltage"]
        transformers.append(tr_data)

    lines = []
    for line_data in data["lines"]:
        # Handle missing results
        if "results" in line_data:
            line_data["results"]["voltage1"] = buses_dict[line_data["bus1"]]["results"]["voltage"]
            line_data["results"]["voltage2"] = buses_dict[line_data["bus2"]]["results"]["voltage"]
        lines.append(line_data)

    switches = []
    for switch_data in data["switches"]:
        # Handle missing results
        if "results" in switch_data:
            switch_data["results"]["voltage1"] = buses_dict[switch_data["bus1"]]["results"]["voltage"]
            switch_data["results"]["voltage2"] = buses_dict[switch_data["bus2"]]["results"]["voltage"]
        switches.append(switch_data)

    results = {
        "version": 4,
        "is_multiphase": data["is_multiphase"],  # Unchanged
        "buses": data["buses"],  # Unchanged
        "lines": lines,
        "transformers": transformers,
        "switches": switches,
        "loads": loads,
        "sources": sources,
        "lines_params": line_params,
        "transformers_params": data["transformers_params"],  # <---- Unchanged
    }

    return results
