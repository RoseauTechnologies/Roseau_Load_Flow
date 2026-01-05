from abc import ABC
from typing import Self

import numpy as np

from roseau.load_flow.models import AbstractBranch, AbstractBranchSide, Bus, TransformerParameters
from roseau.load_flow.models.core import Element, _CyE_co
from roseau.load_flow.typing import Id, JsonDict
from roseau.load_flow_engine.cy_engine import CyACDCConvertor, CyBus, CyPowerLoad, CySimplifiedLine


class DCElement(Element[_CyE_co], ABC):
    def __init__(self, id: Id):
        self.phases = "an"
        super().__init__(id=id)

    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        raise NotImplementedError

    def _to_dict(self, include_results: bool) -> JsonDict:
        raise NotImplementedError

    def _results_to_dict(self, warning: bool, full: bool) -> JsonDict:
        raise NotImplementedError


class DCBus(DCElement[CyBus]):
    def __init__(self, id: Id):
        super().__init__(id=id)
        self._cy_element = CyBus(2, potentials=np.array([100, 0], dtype=np.complex128))

    def _refresh_results(self) -> None:
        pass


class DCLine(DCElement[CySimplifiedLine]):
    def __init__(
        self,
        id: Id,
        bus1: DCBus,
        bus2: DCBus,
        *,
        r_line: float,
        length: float,
    ):
        super().__init__(id=id)
        self.bus1 = bus1
        self.bus2 = bus2
        self.r = r_line * length
        self._cy_element = CySimplifiedLine(2, z_line=self.r * np.eye(2, dtype=np.complex128))

    def _refresh_results(self) -> None:
        pass


class DCPowerLoad(DCElement[CyPowerLoad]):
    def __init__(
        self,
        id: Id,
        bus: DCBus,
        *,
        p: float,
    ):
        super().__init__(id=id)
        self.bus = bus
        self._cy_element = CyPowerLoad(2, powers=np.array([p], dtype=np.complex128))

    def _refresh_results(self) -> None:
        pass


class ACDCConvertor(AbstractBranch["ConvertorSide", CyACDCConvertor]):
    element_type = "transformer"
    allowed_phases = {"an"}

    def __init__(
        self,
        id: Id,
        bus_ac: Bus,
        bus_dc: DCBus,
        *,
        efficiency: float,
        q: float,
        v_dc: float,
    ):
        super().__init__(id=id, bus1=bus_ac, bus2=bus_dc, phases1="an", phases2="an", geometry=None)
        self.efficiency = efficiency
        self.q = q
        self.v_dc = v_dc
        self.bus_ac = bus_ac
        self.bus_dc = bus_dc
        n = len(bus_ac.phases)
        self._cy_element = CyACDCConvertor(n, efficiency, q, v_dc)
        self._connect(bus_ac, bus_dc)
        connections = [[i, i] for i in range(n)]
        self._cy_element.connect_side(self.bus_ac._cy_element, connections, beginning=True)
        connections = [[0, 0], [1, 1]]
        self._cy_element.connect_side(self.bus_dc._cy_element, connections, beginning=False)
        self._side1 = ConvertorSide(branch=self, side=1, bus=bus_ac, phases="an", connect_neutral=None)
        self._side2 = ConvertorSide(branch=self, side=2, bus=bus_dc, phases="an", connect_neutral=None)

    def _refresh_results(self) -> None:
        pass

    @property
    def side_hv(self) -> "ConvertorSide":
        """The HV side of the transformer."""
        return self._side1

    @property
    def side_lv(self) -> "ConvertorSide":
        """The LV side of the transformer."""
        return self._side2

    @property
    def parameters(self) -> TransformerParameters:
        """The LV side of the transformer."""
        return TransformerParameters.from_catalogue("FT 250kVA 15/20kV(20) 400V Dyn11")


class ConvertorSide(AbstractBranchSide):
    element_type = "transformer"
    allowed_phases = ACDCConvertor.allowed_phases  # type: ignore
    _branch: ACDCConvertor
