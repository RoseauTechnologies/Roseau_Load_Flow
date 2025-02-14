from typing import TypedDict, final

from roseau.load_flow.models import (
    AbstractLoad,
    Bus,
    Ground,
    GroundConnection,
    Line,
    PotentialRef,
    Switch,
    Transformer,
    VoltageSource,
)
from roseau.load_flow.typing import Id


@final
class NetworkElements(TypedDict):
    """A dictionary of network elements."""

    buses: dict[Id, Bus]
    loads: dict[Id, AbstractLoad]
    sources: dict[Id, VoltageSource]
    lines: dict[Id, Line]
    transformers: dict[Id, Transformer]
    switches: dict[Id, Switch]
    grounds: dict[Id, Ground]
    potential_refs: dict[Id, PotentialRef]
    ground_connections: dict[Id, GroundConnection]
