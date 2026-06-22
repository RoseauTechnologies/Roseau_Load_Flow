from typing import TypedDict, final

from roseau.load_flow.models import (
    Bus,
    Ground,
    GroundConnection,
    Line,
    Load,
    PotentialRef,
    Switch,
    Transformer,
    VoltageSource,
)
from roseau.load_flow.typing import CRSLike, Id


@final
class NetworkElements(TypedDict):
    """A dictionary of network elements."""

    name: str
    buses: dict[Id, Bus]
    loads: dict[Id, Load]
    sources: dict[Id, VoltageSource]
    lines: dict[Id, Line]
    transformers: dict[Id, Transformer]
    switches: dict[Id, Switch]
    grounds: dict[Id, Ground]
    potential_refs: dict[Id, PotentialRef]
    ground_connections: dict[Id, GroundConnection]
    crs: CRSLike | None
