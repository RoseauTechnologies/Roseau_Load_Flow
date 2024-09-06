import logging
from typing import TYPE_CHECKING, Union

import numpy as np

if TYPE_CHECKING:
    from roseau.load_flow.models import Bus
    from roseau.load_flow.single import Bus as SingleBus

logger = logging.getLogger(__name__)


def propagate_limits(initial_bus: Union["Bus", "SingleBus"], force: bool):
    from roseau.load_flow import Bus, Line, RoseauLoadFlowException, RoseauLoadFlowExceptionCode, Switch
    from roseau.load_flow.single import Bus as SingleBus
    from roseau.load_flow.single import Line as SingleLine
    from roseau.load_flow.single import Switch as SingleSwitch
    from roseau.load_flow.utils.mixins import NetworkElement

    buses: set[Bus | SingleBus] = set()
    visited: set[NetworkElement] = set()
    remaining = set(initial_bus._connected_elements)

    while remaining:
        branch = remaining.pop()
        visited.add(branch)
        if not isinstance(branch, (Line, Switch, SingleLine, SingleSwitch)):
            continue
        for element in branch._connected_elements:
            if not isinstance(element, (Bus, SingleBus)) or element is initial_bus or element in buses:
                continue
            buses.add(element)
            to_add = set(element._connected_elements).difference(visited)
            remaining.update(to_add)
            if not (
                force
                or initial_bus._min_voltage is None
                or element._min_voltage is None
                or np.isclose(element._min_voltage, initial_bus._min_voltage)
            ):
                msg = (
                    f"Cannot propagate the minimum voltage ({initial_bus._min_voltage} V) of bus {initial_bus.id!r} "
                    f"to bus {element.id!r} with different minimum voltage ({element._min_voltage} V)."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)
            if not (
                force
                or initial_bus._max_voltage is None
                or element._max_voltage is None
                or np.isclose(element._max_voltage, initial_bus._max_voltage)
            ):
                msg = (
                    f"Cannot propagate the maximum voltage ({initial_bus._max_voltage} V) of bus {initial_bus.id!r} "
                    f"to bus {element.id!r} with different maximum voltage ({element._max_voltage} V)."
                )
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_VOLTAGES)

    for bus in buses:
        bus._min_voltage = initial_bus._min_voltage
        bus._max_voltage = initial_bus._max_voltage
