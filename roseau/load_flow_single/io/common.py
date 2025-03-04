from typing import TypedDict, final

from roseau.load_flow.typing import Id
from roseau.load_flow_single.models import AbstractLoad, Bus, Line, Switch, Transformer, VoltageSource


@final
class NetworkElements(TypedDict):
    """A dictionary of the network elements."""

    buses: dict[Id, Bus]
    loads: dict[Id, AbstractLoad]
    sources: dict[Id, VoltageSource]
    lines: dict[Id, Line]
    transformers: dict[Id, Transformer]
    switches: dict[Id, Switch]
