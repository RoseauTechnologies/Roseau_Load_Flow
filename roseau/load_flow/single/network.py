"""
This module defines the electrical network class.
"""

import logging

from pyproj import CRS

from roseau.load_flow.models import (
    AbstractLoad,
    Bus,
    Element,
    Ground,
    Line,
    PotentialRef,
    Switch,
    Transformer,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork as TriElectricalNetwork
from roseau.load_flow.typing import MapOrSeq, Solver

logger = logging.getLogger(__name__)


class ElectricalNetwork(TriElectricalNetwork):
    """Electrical network class.

    This class represents an electrical network, its elements, and their connections. After
    creating the network, the load flow solver can be run on it using the
    :meth:`solve_load_flow` method.

    Args:
        buses:
            The buses of the network. Either a list of buses or a dictionary of buses with
            their IDs as keys. Buses are the nodes of the network. They connect other elements
            such as loads and sources. Buses can be connected together with branches.

        branches:
            The branches of the network. Either a list of branches or a dictionary of branches
            with their IDs as keys. Branches are the elements that connect two buses together.
            They can be lines, transformers, or switches.

        loads:
            The loads of the network. Either a list of loads or a dictionary of loads with their
            IDs as keys. There are three types of loads: constant power, constant current, and
            constant impedance.

        sources:
            The sources of the network. Either a list of sources or a dictionary of sources with
            their IDs as keys. A network must have at least one source. Note that two sources
            cannot be connected with a switch.

        ground:
            The grounds of the network. Either a list of grounds or a dictionary of grounds with
            their IDs as keys. LV networks typically have one ground element connected to the
            neutral of the main source bus (secondary of the MV/LV transformer). HV networks
            may have one or more grounds connected to the shunt components of their lines.

        crs:
            An optional Coordinate Reference System to use with geo data frames. If not provided,
            the ``EPSG:4326`` CRS will be used.

    Attributes:
        buses (dict[Id, roseau.load_flow.Bus]):
            Dictionary of buses of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<buses_frame>`.

        branches (dict[Id, roseau.load_flow.AbstractBranch]):
            Dictionary of branches of the network indexed by their IDs. Also available as a
            :attr:`GeoDataFrame<branches_frame>`.

        loads (dict[Id, roseau.load_flow.AbstractLoad]):
            Dictionary of loads of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<loads_frame>`.

        sources (dict[Id, roseau.load_flow.VoltageSource]):
            Dictionary of voltage sources of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<sources_frame>`.

        grounds (dict[Id, roseau.load_flow.Ground]):
            Dictionary of grounds of the network indexed by their IDs. Also available as a
            :attr:`DataFrame<grounds_frame>`.

        potential_refs (dict[Id, roseau.load_flow.PotentialRef]):
            Dictionary of potential references of the network indexed by their IDs. Also available
            as a :attr:`DataFrame<potential_refs_frame>`.
    """

    _DEFAULT_SOLVER: Solver = "newton_goldstein"

    #
    # Methods to build an electrical network
    #
    def __init__(
        self,
        buses: MapOrSeq[Bus],
        lines: MapOrSeq[Line],
        transformers: MapOrSeq[Transformer],
        switches: MapOrSeq[Switch],
        loads: MapOrSeq[AbstractLoad],
        sources: MapOrSeq[VoltageSource],
        ground: Ground,
        crs: str | CRS | None = None,
    ) -> None:
        potential_ref = PotentialRef(id="pref", element=ground)
        for bus in buses:
            ground.connect(bus)
        super().__init__(
            buses=buses,
            lines=lines,
            transformers=transformers,
            switches=switches,
            loads=loads,
            sources=sources,
            grounds=[ground],
            potential_refs=[potential_ref],
            crs=crs,
        )

    @classmethod
    def from_element(cls, initial_bus: Bus):
        """Construct the network from only one element (bus) and add the others automatically.

        Args:
            initial_bus:
                Any bus of the network. The network is constructed from this bus and all the
                elements connected to it. This is usually the main source bus of the network.

        Returns:
            The network constructed from the given bus and all the elements connected to it.
        """
        buses: list[Bus] = []
        lines: list[Line] = []
        transformers: list[Transformer] = []
        switches: list[Switch] = []
        loads: list[AbstractLoad] = []
        sources: list[VoltageSource] = []
        grounds: list[Ground] = []
        potential_refs: list[PotentialRef] = []

        elements: list[Element] = [initial_bus]
        visited_elements: set[Element] = set()
        while elements:
            e = elements.pop(-1)
            visited_elements.add(e)
            if isinstance(e, Bus):
                buses.append(e)
            elif isinstance(e, Line):
                lines.append(e)
            elif isinstance(e, Transformer):
                transformers.append(e)
            elif isinstance(e, Switch):
                switches.append(e)
            elif isinstance(e, AbstractLoad):
                loads.append(e)
            elif isinstance(e, VoltageSource):
                sources.append(e)
            elif isinstance(e, Ground):
                grounds.append(e)
            elif isinstance(e, PotentialRef):
                potential_refs.append(e)
            for connected_element in e._connected_elements:
                if connected_element not in visited_elements and connected_element not in elements:
                    elements.append(connected_element)
        return cls(
            buses=buses,
            lines=lines,
            transformers=transformers,
            switches=switches,
            loads=loads,
            sources=sources,
            ground=grounds[0],  # TODO
        )
