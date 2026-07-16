from typing import TypedDict, final

from roseau.load_flow.typing import CRSLike, Id
from roseau.load_flow_single.models import Bus, Line, Load, Switch, Transformer, VoltageRegulator, VoltageSource


@final
class NetworkElements(TypedDict):
    """A dictionary of the network elements."""

    name: str
    buses: dict[Id, Bus]
    loads: dict[Id, Load]
    sources: dict[Id, VoltageSource]
    lines: dict[Id, Line]
    transformers: dict[Id, Transformer]
    regulators: dict[Id, VoltageRegulator]
    switches: dict[Id, Switch]
    crs: CRSLike | None
