import logging
import re
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Final, Literal, NoReturn, Self

import numpy as np
import pandas as pd

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.types import TransformerCooling, TransformerInsulation
from roseau.load_flow.typing import FloatArrayLike1D, Id, JsonDict
from roseau.load_flow.units import Q_, ureg_wraps
from roseau.load_flow.utils import CatalogueMixin, Identifiable, JsonMixin
from roseau.load_flow_engine.cy_engine import (
    CyCenterTransformer,
    CySingleTransformer,
    CyThreePhaseTransformer,
    CyTransformer,
)

logger = logging.getLogger(__name__)


class TransformerParameters(Identifiable, JsonMixin, CatalogueMixin[pd.DataFrame]):
    """Parameters that define electrical models of transformers."""

    is_multi_phase: Final = True

    # Power Transformers General specification can be found in IEC 60076-1

    # fmt: off
    allowed_vector_groups: Final = {
        # Common connections (clock numbers 0, 1, 5, 6, 11)
        "Dd0", "Yy0", "YNy0", "Yyn0", "YNyn0", "Dz0", "Dzn0",
        "Dy1", "Dyn1", "Yz1", "YNz1", "Yzn1", "YNzn1", "Yd1", "YNd1",
        "Dy5", "Dyn5", "Yz5", "YNz5", "Yzn5", "YNzn5", "Yd5", "YNd5",
        "Dd6", "Yy6", "YNy6", "Yyn6", "YNyn6", "Dz6", "Dzn6",
        "Dy11", "Dyn11", "Yz11", "YNz11", "Yzn11", "YNzn11", "Yd11", "YNd11",
        # Additional connections (clock numbers 2, 4, 7, 8, 10)
        "Dd2", "Dz2", "Dzn2",
        "Dd4", "Dz4", "Dzn4",
        "Dy7", "Dyn7", "Yz7", "YNz7", "Yzn7", "YNzn7", "Yd7", "YNd7",
        "Dd8", "Dz8", "Dzn8",
        "Dd10", "Dz10", "Dzn10",
        # Single-phase transformers
        "Ii0", "Iii0",
        "Ii6", "Iii6",
    }
    """Allowed vector groups for transformers."""
    # fmt: on

    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "ohm", "S", "Hz", None, None, None, None, None))
    def __init__(
        self,
        id: Id,
        *,
        vg: str,
        uhv: float | Q_[float],
        ulv: float | Q_[float],
        sn: float | Q_[float],
        z2: complex | Q_[complex],
        ym: complex | Q_[complex],
        fn: float | Q_[float] | None = None,
        manufacturer: str | None = None,
        range: str | None = None,
        efficiency: str | None = None,
        cooling: str | TransformerCooling | None = None,
        insulation: str | TransformerInsulation | None = None,
    ) -> None:
        """TransformerParameters constructor.

        Args:
            id:
                A unique ID of the transformer parameters, typically its canonical name.

            vg:
                The vector group of the transformer.

                For three-phase transformers, ``Dyn11`` denotes a delta-wye connection with -30° phase
                displacement. Allowed windings are ``D`` for delta, ``Y`` for wye, ``Z`` for zigzag.

                For single-phase transformers, ``Ii0`` denotes a normal in-phase connection and
                ``Ii6`` denotes an inverted connection.

                For center-tapped transformers, ``Iii0`` denotes a normal in-phase connection and
                ``Iii6`` denotes an inverted connection.

            uhv:
                Rated phase-to-phase voltage of the HV side (V)

            ulv:
                Rated no-load phase-to-phase voltage of the LV side (V)

            sn:
                The nominal power of the transformer (VA)

            z2:
                The series impedance located at the LV side of the transformer.

            ym:
                The magnetizing admittance located at the HV side of the transformer.

            fn:
                The nominal frequency of the transformer (Hz). Default is None. The frequency is not
                currently used in the transformer model as the transformer parameters already in Ohm
                and Siemens. It is only used when converting the transformer parameters to other
                formats, like PowerFactory.

            manufacturer:
                The name of the manufacturer for the transformer. Informative only, it has no impact
                on the load flow. It is filled automatically when the parameters when imported from
                the catalogue.

            range:
                The product range for the transformer as defined by the manufacturer. Informative
                only, it has no impact on the load flow. It is filled automatically when the
                parameters when imported from the catalogue.

            efficiency:
                The efficiency class of the transformer. Informative only, it has no impact on the
                load flow. It is filled automatically when the parameters when imported from the
                catalogue. The efficiency class used in the catalogue follows the `Eco-Design`
                requirements as defined by the `EN 50629` standard.

            cooling:
                The cooling class of the transformer according to IEC 60076 (ONAN, ONAF, etc.).
                Informative only, it has no impact on the load flow. The cooling class is defined by
                IEC 60076 parts 2, 11 and 15.

            insulation:
                The transformer insulation technology (dry-type, liquid-immersed, gas-filled).
                Informative only, it has no impact on the load flow.
        """
        super().__init__(id)

        # Check
        if uhv < ulv:
            msg = (
                f"Transformer parameters {id!r} has the low voltage higher than the high voltage: "
                f"uhv={uhv!s} V and ulv={ulv!s} V."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VOLTAGES)
        if np.isclose(z2, 0.0):
            msg = (
                f"Transformer parameters {id!r} has a null series impedance z2. Ideal transformers "
                f"are not supported yet."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_IMPEDANCE)

        # Extract the windings of the HV and LV sides of the transformer
        whv, wlv, clock = self.extract_windings(vg=vg)

        self._vg: str = f"{whv}{wlv}{clock}"  # normalized vector group
        self._sn: float = sn
        self._uhv: float = uhv
        self._ulv: float = ulv
        self._fn: float | None = fn
        self._z2: complex = z2
        self._ym: complex = ym
        self._manufacturer: str | None = manufacturer
        self._range: str | None = range
        self._efficiency: str | None = efficiency
        self._cooling = TransformerCooling(cooling) if cooling else None
        self._insulation = TransformerInsulation(insulation) if insulation else None

        # Change the voltages if the reference voltages is phase-to-neutral
        if whv[0] == "Y":
            uhv /= np.sqrt(3.0)
        elif whv[0] == "Z":
            uhv /= 3.0
        if wlv[0] == "y":
            ulv /= np.sqrt(3.0)
        elif wlv[0] == "z":
            ulv /= 3.0

        n_of_winding = {"y": 4, "z": 4, "yn": 4, "zn": 4, "d": 3, "i": 2, "ii": 3}
        n1 = n_of_winding[whv.lower()]
        n2 = n_of_winding[wlv.lower()]

        self._k: float = ulv / uhv
        self._n1: int = n1
        self._n2: int = n2
        self._whv: str = whv
        self._wlv: str = wlv
        self._clock: int = clock

        self._elements = set()  # Set of elements using this transformer parameters object

        # Filled using alternative constructor `from_open_and_short_circuit_tests`
        self._p0: float | None = None
        self._i0: float | None = None
        self._psc: float | None = None
        self._vsc: float | None = None
        self._has_test_results: bool = False

    def __repr__(self) -> str:
        s = f"<{type(self).__name__}: id={self.id!r}, vg={self._vg!r}, sn={self._sn}, uhv={self._uhv}, ulv={self._ulv}"
        for attr, val, tp in (
            ("fn", self._fn, float),
            ("p0", self._p0, float),
            ("i0", self._i0, float),
            ("psc", self._psc, float),
            ("vsc", self._vsc, float),
            ("manufacturer", self._manufacturer, str),
            ("range", self._range, str),
            ("efficiency", self._efficiency, str),
            ("cooling", self._cooling, str),
            ("insulation", self._insulation, str),
        ):
            if val is not None:
                s += f", {attr}={tp(val)!r}"
        s += ">"
        return s

    @property
    def type(self) -> Literal["three-phase", "single-phase", "center-tapped"]:
        """The type of transformer parameters.

        It can be ``three-phase``, ``single-phase`` or ``center-tapped``.
        """
        if self._vg in ("Ii0", "Ii6"):
            return "single-phase"
        elif self._vg in ("Iii0", "Iii6"):
            return "center-tapped"
        else:
            return "three-phase"

    @property
    def vg(self) -> str:
        """The vector group of the transformer.

        For three-phase transformers, ``Dyn11`` denotes a delta-wye connection with 30° lead phase
        displacement. Allowed windings are ``D`` for delta, ``Y`` for wye, ``Z`` for zigzag.

        For single-phase transformers, ``Ii0`` denotes a normal in-phase connection and ``Ii6``
        denotes an inverted connection.

        For center-tapped transformers, ``Iii0`` denotes a normal in-phase connection and ``Iii6``
        denotes an inverted connection.
        """
        return self._vg

    @property
    def whv(self) -> str:
        """The HV winding of the transformer.

        The following values are used:
        - ``D``: a Delta connection
        - ``Y`` or ``Yn``: a Wye connection
        - ``Z`` or ``Zn``: a Zigzag connection
        - ``I``: single-phase
        """
        return self._whv

    @property
    def wlv(self) -> str:
        """The LV winding of the transformer.

        The following values are used:
        - ``d``: a Delta connection
        - ``y`` or ``yn``: a Wye connection
        - ``z`` or ``zn``: a Zigzag connection
        - ``i``: single-phase
        - ``ii`` split-phase (i.e center-tapped)
        """
        return self._wlv

    @property
    def clock(self) -> int:
        """The clock number (phase displacement) as indicated by the vector group."""
        return self._clock

    # Keep old properties for backward compatibility
    winding1 = whv
    winding2 = wlv
    phase_displacement = clock

    @property
    @ureg_wraps("V", (None,))
    def uhv(self) -> Q_[float]:
        """Rated phase-to-phase voltage of the HV side (V)."""
        return self._uhv

    @property
    @ureg_wraps("V", (None,))
    def ulv(self) -> Q_[float]:
        """Rated no-load phase-to-phase voltage of the LV side (V)."""
        return self._ulv

    @property
    @ureg_wraps("VA", (None,))
    def sn(self) -> Q_[float]:
        """The nominal power of the transformer (VA)."""
        return self._sn

    @property
    def fn(self) -> Q_[float]:
        """The nominal frequency of the transformer (Hz)."""
        return Q_(self._fn, "Hz") if self._fn is not None else None

    @property
    @ureg_wraps("ohm", (None,))
    def z2(self) -> Q_[complex]:
        """The series impedance of the transformer (Ohm)."""
        return self._z2

    @property
    @ureg_wraps("S", (None,))
    def ym(self) -> Q_[complex]:
        """The magnetizing admittance of the transformer (S)."""
        return self._ym

    @property
    @ureg_wraps("", (None,))
    def k(self) -> Q_[float]:
        """The transformation ratio of the transformer."""
        return self._k

    @property
    def orientation(self) -> float:
        """The orientation of the transformer: 1 for direct windings or -1 for reverse windings."""
        return -1.0 if 3 < self._clock < 9 else 1.0

    @property
    def p0(self) -> Q_[float]:
        """Losses during open-circuit test (W)."""
        if self._p0 is None:
            assert not self._has_test_results, "Missing p0 from open-circuit test results."
            self._p0, self._i0 = self._compute_open_circuit_parameters()
        return Q_(self._p0, "W")

    @property
    def i0(self) -> Q_[float]:
        """Current during open-circuit test (%)."""
        if self._i0 is None:
            assert not self._has_test_results, "Missing i0 from open-circuit test results."
            self._p0, self._i0 = self._compute_open_circuit_parameters()
        return Q_(self._i0, "")

    @property
    def psc(self) -> Q_[float]:
        """Losses during short-circuit test (W)."""
        if self._psc is None:
            assert not self._has_test_results, "Missing psc from short-circuit test results."
            self._psc, self._vsc = self._compute_short_circuit_parameters()
        return Q_(self._psc, "W")

    @property
    def vsc(self) -> Q_[float]:
        """Voltages on LV side during short-circuit test (%)."""
        if self._vsc is None:
            assert not self._has_test_results, "Missing vsc from short-circuit test results."
            self._psc, self._vsc = self._compute_short_circuit_parameters()
        return Q_(self._vsc, "")

    @property
    def manufacturer(self) -> str | None:
        """The name of the manufacturer for the transformer.

        Informative only, it has no impact on the load flow. It is filled automatically when the
        parameters are imported from the catalogue.
        """
        return self._manufacturer

    @property
    def range(self) -> str | None:
        """The product range for the transformer as defined by the manufacturer.

        Informative only, it has no impact on the load flow. It is filled automatically when the
        parameters are imported from the catalogue.
        """
        return self._range

    @property
    def efficiency(self) -> str | None:
        """The efficiency class of the transformer.

        Informative only, it has no impact on the load flow. It is filled automatically when the
        parameters imported from the catalogue. The efficiency class used in the catalogue follows
        the `Eco-Design` requirements as defined by the `EN 50629` standard.
        """
        return self._efficiency

    @property
    def cooling(self) -> TransformerCooling | None:
        """The cooling class of the transformer according to IEC 60076 (ONAN, ONAF, AN, ...)."""
        return self._cooling

    @property
    def insulation(self) -> TransformerInsulation | None:
        """The insulation technology of the transformer (dry-type, liquid-immersed, gas-filled)."""
        return self._insulation

    @classmethod
    def _compute_zy(
        cls, vg: str, uhv: float, ulv: float, sn: float, p0: float, i0: float, psc: float, vsc: float
    ) -> tuple[complex, complex]:
        whv, wlv, _ = cls.extract_windings(vg=vg)

        # Open-circuit (no-load) test
        # ---------------------------
        # Iron losses resistance (Ohm)
        if p0 > 0:
            r_iron = uhv**2 / p0
            y_iron = 1 / r_iron
        else:  # no iron losses
            y_iron = 0
        # Magnetizing inductance (Henry) * omega (rad/s)
        s0 = i0 * sn
        if s0 > p0:
            lm_omega = uhv**2 / np.sqrt(s0**2 - p0**2)
            y_lm = 1 / (1j * lm_omega)
        else:  # no magnetizing reactance
            y_lm = 0j
        ym = y_iron + y_lm
        if whv[0] == "D":
            ym /= 3

        # Short-circuit test
        # ------------------
        # Copper losses resistance (Ohm)
        r2 = psc * (ulv / sn) ** 2
        z2_mag = vsc * ulv**2 / sn
        # Leakage inductance (Henry) * omega (rad/s)
        if z2_mag > r2:  # noqa: SIM108
            l2_omega = np.sqrt(z2_mag**2 - r2**2)
        else:  # no leakage reactance
            l2_omega = 0.0
        z2 = r2 + 1j * l2_omega
        if wlv[0] == "d":
            z2 *= 3

        return z2, ym

    @classmethod
    @ureg_wraps(
        None,
        (
            None,
            None,
            None,
            "MVA",
            "kV",
            "kV",
            None,
            None,
            None,
            "percent",
            "kW",
            "percent",
            "kW",
            None,
            None,
            None,
            None,
            None,
        ),
    )
    def from_power_factory(
        cls,
        id: Id,
        *,
        tech: Literal[2, "single-phase", 3, "three-phase"],
        sn: float | Q_[float],
        uhv: float | Q_[float],
        ulv: float | Q_[float],
        vg_hv: str,
        vg_lv: str,
        phase_shift: int,
        uk: float | Q_[float],
        pc: float | Q_[float],
        curmg: float | Q_[float],
        pfe: float | Q_[float],
        # Roseau parameters
        manufacturer: str | None = None,
        range: str | None = None,
        efficiency: str | None = None,
        cooling: str | TransformerCooling | None = None,
        insulation: str | TransformerInsulation | None = None,
    ) -> Self:
        """Create a transformer parameters object from PowerFactory "TypTr2" data.

        Note that only two-winding three-phase transformers are currently supported.

        Args:
            id:
                A unique ID of the transformer parameters.

            tech:
                PwF parameter `nt2ph` (Technology). The technology of the transformer; either
                `'single-phase'` or `2` for single-phase transformers or `'three-phase'` or `3` for
                three-phase transformers.

            sn:
                PwF parameter `strn` (Rated Power). The rated power of the transformer in (MVA).

            uhv:
                PwF parameter `utrn_h` (Rated Voltage HV-Side). The rated phase-to-phase voltage of
                the transformer on the HV side.

            ulv:
                PwF parameter `utrn_l` (Rated Voltage LV-Side). The rated phase-to-phase voltage of
                the transformer on the LV side.

            vg_hv:
                PwF parameter `tr2cn_h` (Vector Group HV-Side). The vector group of the high voltage
                side. It can be one of `'D'`, `'Y'`, `'Yn'`, `'Z'`, `'Zn'`.

            vg_lv:
                PwF parameter `tr2cn_l` (Vector Group LV-Side). The vector group of the low voltage
                side. It can be one of `'d'`, `'y'`, `'yn'`, `'z'`, `'zn'`.

            phase_shift:
                PwF parameter `nt2ag` (Vector Group Phase Shift). The phase shift of the vector
                group in (degrees).

            uk:
                PwF parameter `uktr` (Positive Sequence Impedance Short-Circuit Voltage). The
                positive sequence impedance i.e the voltage in (%) obtained from the short-circuit
                test.

            pc:
                PwF parameter `pcutr` (Positive Sequence Impedance Copper Losses). The positive
                sequence impedance copper losses i.e the power in (kW) obtained from the short
                circuit test.

            curmg:
                PwF parameter `curmg` (Magnetizing Impedance - No Load Current). The magnetizing
                current i.e. the current in (%) obtained from the no-load (open-circuit) test.

            pfe:
                PwF parameter `pfe` (Magnetizing Impedance - No Load Losses). The magnetizing
                impedance i.e. the power losses in (kW) obtained from the no-load test.

            manufacturer:
                The name of the manufacturer for the transformer. Informative only, it has no impact
                on the load flow.

            range:
                The name of the product range for the transformer. Informative only, it has no impact
                on the load flow.

            efficiency:
                The efficiency class of the transformer. Informative only, it has no impact on the
                load flow.

            cooling:
                The cooling class of the transformer according to IEC 60076 (ONAN, ONAF, etc.).
                Informative only, it has no impact on the load flow. The cooling class is defined by
                IEC 60076 parts 2, 11 and 15.

            insulation:
                The transformer insulation technology (dry-type, liquid-immersed, gas-filled).
                Informative only, it has no impact on the load flow.

        Returns:
            The corresponding transformer parameters object.
        """
        # Type: from vector group data and technology
        tech_norm = str(tech).upper().replace(" ", "-")
        if tech_norm.startswith("SINGLE-PHASE") or tech_norm == "2":
            vg = "Ii0"  # TODO do we have vector group data for single-phase transformers?
        elif tech_norm.startswith("THREE-PHASE") or tech_norm == "3":
            vg = f"{vg_hv.upper()}{vg_lv.lower()}{phase_shift}"
        else:
            msg = f"Expected tech='single-phase' or 'three-phase', got {tech!r} for transformer parameters {id!r}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_TYPE)

        uhv *= 1e3
        ulv *= 1e3
        sn *= 1e6
        p0 = pfe * 1e3
        psc = pc * 1e3
        i0 = curmg / 100
        vsc = uk / 100

        z2, ym = cls._compute_zy(vg=vg, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc)

        instance = cls(
            id=id,
            vg=vg,
            uhv=uhv,
            ulv=ulv,
            sn=sn,
            z2=z2,
            ym=ym,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            cooling=cooling,
            insulation=insulation,
        )
        instance._p0 = p0
        instance._i0 = i0
        instance._psc = psc
        instance._vsc = vsc
        instance._has_test_results = True
        return instance

    @classmethod
    @ureg_wraps(
        None,
        (
            None,
            None,
            None,
            "kV",
            "kVA",
            None,
            "percent",
            "percent",
            "percent",
            "percent",
            "percent",
            None,
            None,
            None,
            None,
            None,
        ),
    )
    def from_open_dss(
        cls,
        id: Id,
        *,
        conns: tuple[str, str],
        kvs: tuple[float, float] | FloatArrayLike1D,
        kvas: float | Q_[float] | tuple[float, float] | FloatArrayLike1D,
        leadlag: str,
        xhl: float,
        loadloss: float | Q_[float] | None = None,
        noloadloss: float | Q_[float] = 0,
        imag: float | Q_[float] = 0,
        rs: float | Q_[float] | tuple[float, float] | FloatArrayLike1D | None = None,
        # Roseau parameters
        manufacturer: str | None = None,
        range: str | None = None,
        efficiency: str | None = None,
        cooling: str | TransformerCooling | None = None,
        insulation: str | TransformerInsulation | None = None,
    ) -> Self:
        """Create a transformer parameters object from OpenDSS "Transformer" data.

        Note that only two-winding three-phase transformers are currently supported.

        Args:
            id:
                The unique ID of the transformer parameters.

            conns:
                OpenDSS parameter: `Conns`. Connection of the windings. One of {wye | ln} for wye
                connected banks or {delta | ll} for delta (line-line) connected banks.

            kvs:
                OpenDSS parameter: `KVs`. Rated phase-to-phase voltage of the windings, kV. This is
                a sequence of two values equivalent to (Up, Us).

            kvas:
                OpenDSS parameter: `KVAs`. Base kVA rating (OA rating) of the windings. Note that
                only one value is accepted as only two-winding transformers are accepted.

            xhl:
                OpenDSS parameter: `XHL`. Percent reactance high-to-low (winding 1 to winding 2).

            loadloss:
                OpenDSS parameter: `%Loadloss`. Percent Losses at rated load. Causes the %r values
                (cf. the `%Rs` parameter) to be set for windings 1 and 2.

            noloadloss:
                OpenDSS parameter: `%Noloadloss`. Percent No load losses at nominal voltage. Default
                is 0. Causes a resistive branch to be added in parallel with the magnetizing inductance.

            imag:
                OpenDSS parameter: `%Imag`. Percent magnetizing current. Default is 0. An inductance
                is used to represent the magnetizing current. This is embedded within the transformer
                model as the primitive Y matrix is being computed.

            leadlag:
                OpenDSS parameter: `LeadLag`. {Lead | Lag | ANSI | Euro} Designation in mixed
                Delta-wye connections signifying the relationship between HV to LV winding.
                Default is ANSI 30 deg lag, e.g., Dy1 of Yd1 vector group. To get typical European Dy11
                connection, specify either "lead" or "Euro".

            rs:
                OpenDSS parameter: `%Rs`. [OPTIONAL] Percent resistance of the windings on the rated
                kVA base. Only required if `loadloss` is not passed. Note that if `rs` is used along
                with `loadloss`, they have to have equivalent values. For a two-winding transformer,
                `%rs=[0.1, 0.1]` is equivalent to `%loadloss=0.2`.

            manufacturer:
                The name of the manufacturer for the transformer. Informative only, it has no impact
                on the load flow.

            range:
                The name of the product range for the transformer. Informative only, it has no impact
                on the load flow.

            efficiency:
                The efficiency class of the transformer. Informative only, it has no impact on the
                load flow.

            cooling:
                The cooling class of the transformer according to IEC 60076 (ONAN, ONAF, etc.).
                Informative only, it has no impact on the load flow. The cooling class is defined by
                IEC 60076 parts 2, 11 and 15.

            insulation:
                The transformer insulation technology (dry-type, liquid-immersed, gas-filled).
                Informative only, it has no impact on the load flow.

        Returns:
            The corresponding transformer parameters object.

        Example usage::

            # DSS command: `New transformer.LVTR Buses=[sourcebus, A.1.2.3] Conns=[delta wye] KVs=[11, 0.4] KVAs=[250 250] %Rs=0.00 xhl=2.5 %loadloss=0`
            tp = rlf.TransformerParameters.from_open_dss(
                id="dss-tp",
                conns=("delta", "wye"),
                kvs=(11, 0.4),
                kvas=(250, 250),  # alternatively pass a scalar `kvas=250`
                leadlag="ansi",  # (Dyn1 or Yd1) or "euro" (Dyn11 or Yd11)
                xhl=2.5,
                loadloss=0,
                noloadloss=0,  # default value used in OpenDSS
                imag=0,  # default value used in OpenDSS
                rs=0,  # redundant with `loadloss=0`
            )
        """
        # Windings
        whv, wlv = (c.lower() for c in conns)
        wye_names = ("wye", "ln")
        delta_names = ("delta", "ll")
        if whv in wye_names:
            whv = "Y"
        elif whv in delta_names:
            whv = "D"
        else:
            msg = f"Got unknown winding (1) connection {conns[0]!r}, expected one of ('wye', 'ln', 'delta', 'll')."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        if wlv in wye_names:
            wlv = "yn"
        elif wlv in delta_names:
            wlv = "d"
        else:
            msg = f"Got unknown winding (2) connection {conns[1]!r}, expected one of ('wye', 'ln', 'delta', 'll')."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)

        # Lead lag
        leadlag_l = leadlag.lower()
        if (whv == "D" and wlv[0] == "y") or (whv[0] == "Y" and wlv == "d"):
            if leadlag_l in ("lead", "euro"):
                clock = 11
            elif leadlag_l in ("lag", "ansi"):
                clock = 1
            else:
                msg = f"Got unknown leadlag value {leadlag!r}, expected one of ('lead', 'lag', 'ansi', 'euro')"
                logger.error(msg)
                raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
        else:
            clock = 0  # TODO is leadlag used with Dd or Yy transformers?

        # Vector Group: from winding and lead-lag parameters
        vg = f"{whv}{wlv}{clock}"

        # High and low rated voltages
        uhv, ulv = (u * 1000 for u in kvs)  # in Volts

        # Nominal power
        sn: float  # in Watts
        if np.isscalar(kvas):
            sn = kvas * 1000
        else:
            kvs_uniq = np.unique(kvas)
            if len(kvs_uniq) > 1:
                logger.warning(
                    f"Only one base kVA rating is expected, got {kvs_uniq!r}. Only the first one will be used"
                )
            sn = kvs_uniq[0] * 1000

        # Z2 and Ym
        rs_array = [rs, rs] if np.isscalar(rs) else rs
        if loadloss is None:
            if rs is None:
                raise TypeError("from_open_dss() missing 1 required keyword argument: 'loadloss' or 'rs'")
            else:
                r1, r2 = rs_array
                loadloss = r1 + r2
        elif not np.isscalar(loadloss):
            msg = f"%Loadloss must be a scalar, got {loadloss!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DSS_BAD_LOSS)
        elif rs is not None and not np.isclose(sum(rs_array), loadloss):
            msg = f"The values of rs={rs!r} are not equivalent to the value of loadloss={loadloss!r}"
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.DSS_BAD_LOSS)

        p0 = (noloadloss / 100) * sn
        i0 = imag / 100
        psc = (loadloss / 100) * sn
        vsc = xhl / 100
        z2, ym = cls._compute_zy(vg=vg, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc)

        instance = cls(
            id=id,
            vg=vg,
            uhv=uhv,
            ulv=ulv,
            sn=sn,
            z2=z2,
            ym=ym,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            cooling=cooling,
            insulation=insulation,
        )
        instance._p0 = p0
        instance._i0 = i0
        instance._psc = psc
        instance._vsc = vsc
        instance._has_test_results = True
        return instance

    #
    # Open and short circuit tests
    #
    @classmethod
    @ureg_wraps(None, (None, None, None, "V", "V", "VA", "W", "", "W", "", "Hz", None, None, None, None, None))
    def from_open_and_short_circuit_tests(
        cls,
        id: Id,
        *,
        vg: str,
        uhv: float | Q_[float],
        ulv: float | Q_[float],
        sn: float | Q_[float],
        p0: float | Q_[float],
        i0: float | Q_[float],
        psc: float | Q_[float],
        vsc: float | Q_[float],
        fn: float | Q_[float] | None = None,
        manufacturer: str | None = None,
        range: str | None = None,
        efficiency: str | None = None,
        cooling: str | TransformerCooling | None = None,
        insulation: str | TransformerInsulation | None = None,
    ) -> Self:
        """Create a TransformerParameters object using the results of open-circuit and short-circuit tests.

        Args:
            id:
                A unique ID of the transformer parameters, typically its canonical name.

            vg:
                The vector group of the transformer.

                For three-phase transformers, ``Dyn11`` denotes a delta-wye connection with -30° phase
                displacement. Allowed windings are ``D`` for delta, ``Y`` for wye, ``Z`` for zigzag.

                For single-phase transformers, ``Ii0`` denotes a normal in-phase connection and
                ``Ii6`` denotes an inverted connection.

                For center-tapped transformers, ``Iii0`` denotes a normal in-phase connection and
                ``Iii6`` denotes an inverted connection.

            uhv:
                Rated phase-to-phase voltage of the HV side (V).

            ulv:
                Rated no-load phase-to-phase voltage of the LV side (V).

            sn:
                The nominal power of the transformer (VA).

            p0:
                Losses during open-circuit test (W).

            i0:
                Current during open-circuit test (%).

            psc:
                Losses during short-circuit test (W).

            vsc:
                Voltages on LV side during short-circuit test (%).

            fn:
                The nominal frequency of the transformer (Hz). Default is None. The frequency is not
                currently used in the transformer model as the transformer parameters already in Ohm
                and Siemens. It is only used when converting the transformer parameters to other
                formats, like PowerFactory.

            manufacturer:
                The name of the manufacturer for the transformer. Informative only, it has no impact
                on the load flow. It is filled automatically when the parameters when imported from
                the catalogue.

            range:
                The product range for the transformer as defined by the manufacturer. Informative
                only, it has no impact on the load flow. It is filled automatically when the
                parameters when imported from the catalogue.

            efficiency:
                The efficiency class of the transformer. Informative only, it has no impact on the
                load flow. It is filled automatically when the parameters are imported from the
                catalogue. The efficiency class used in the catalogue follows the `Eco-Design`
                requirements as defined by the `EN 50629` standard.

            cooling:
                The cooling class of the transformer according to IEC 60076 (ONAN, ONAF, etc.).
                Informative only, it has no impact on the load flow. The cooling class is defined by
                IEC 60076 parts 2, 11 and 15.

            insulation:
                The transformer insulation technology (dry-type, liquid-immersed, gas-filled).
                Informative only, it has no impact on the load flow.
        """
        # Check
        if i0 > 1.0 or i0 < 0.0:
            msg = (
                f"Invalid open-circuit test current i0={i0} for transformer parameters {id!r}. "
                f"Expected a percentage between 0 and 1."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if vsc > 1.0 or vsc < 0.0:
            msg = (
                f"Invalid short-circuit test voltage vsc={vsc} for transformer parameters {id!r}. "
                f"Expected a percentage between 0 and 1."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if psc / sn > vsc:
            msg = (
                f"Invalid short-circuit results for transformer parameters {id!r}. The following "
                f"inequality must be respected: psc/sn <= vsc, got {psc/sn=:f} and {vsc=:f}."
            )
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_PARAMETERS)
        if i0 * sn < p0:
            logger.warning(
                f"Open-circuit results for transformer parameters {id!r} do not respect the inequality: "
                f"i0 * sn > p0. The magnetizing admittance imaginary part will be null."
            )

        z2, ym = cls._compute_zy(vg=vg, uhv=uhv, ulv=ulv, sn=sn, p0=p0, i0=i0, psc=psc, vsc=vsc)

        instance = cls(
            id=id,
            vg=vg,
            uhv=uhv,
            ulv=ulv,
            sn=sn,
            z2=z2,
            ym=ym,
            fn=fn,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            cooling=cooling,
            insulation=insulation,
        )
        instance._p0 = p0
        instance._i0 = i0
        instance._psc = psc
        instance._vsc = vsc
        instance._has_test_results = True
        return instance

    def _create_cy_transformer(self, tap: float = 1.0) -> CyTransformer:
        """Create a CyTransformer object from the transformer parameters."""
        if self.type == "three-phase":
            return CyThreePhaseTransformer(
                n1=self._n1,
                n2=self._n2,
                whv=self._whv[0],
                wlv=self._wlv[0],
                z2=self._z2,
                ym=self._ym,
                k=self._k * tap,
                clock=self._clock,
            )
        elif self.type == "single-phase":
            return CySingleTransformer(z2=self._z2, ym=self._ym, k=self._k * tap)
        else:
            return CyCenterTransformer(z2=self._z2, ym=self._ym, k=self._k * tap)

    def _compute_open_circuit_parameters(self) -> tuple[float, float]:
        """Compute the open-circuit test results of the transformer parameters.

        Returns:
            The values ``p0``, the losses (in W), and ``i0``, the current (in %) during open-circuit
            test.
        """
        return self._create_cy_transformer().compute_open_circuit_parameters(uhv=self._uhv, ulv=self._ulv, sn=self._sn)

    def _compute_short_circuit_parameters(self) -> tuple[float, float]:
        """Compute the short-circuit test results of the transformer parameters.

        Returns:
            The values ``psc``, the losses (in W), and ``vsc``, the voltages on LV side (in %) during
            short-circuit test.
        """
        cy_transformer = self._create_cy_transformer()
        # Ignore ym because it is ignored when computing z2 from the short-circuit test
        cy_transformer.update_transformer_parameters(z2=self._z2, ym=0j, k=self._k)
        return cy_transformer.compute_short_circuit_parameters(uhv=self._uhv, ulv=self._ulv, sn=self._sn)

    #
    # Json Mixin interface
    #
    @classmethod
    def from_dict(cls, data: JsonDict, *, include_results: bool = True) -> Self:
        if "p0" in data:
            # TODO should we validate z2 and ym if they exist?
            return cls.from_open_and_short_circuit_tests(
                id=data["id"],
                vg=data["vg"],  # Vector Group (e.g. Dyn11)
                uhv=data["uhv"],  # Rated phase-to-phase voltage of the HV side (V)
                ulv=data["ulv"],  # Rated no-load phase-to-phase voltage of the LV side (V)
                sn=data["sn"],  # Nominal power
                p0=data["p0"],  # Losses during open-circuit test (W)
                i0=data["i0"],  # Current during open-circuit test (%)
                psc=data["psc"],  # Losses during short-circuit test (W)
                vsc=data["vsc"],  # Voltages on LV side during short-circuit test (%)
                fn=data.get("fn"),  # Frequency (Hz)
                manufacturer=data.get("manufacturer"),  # The manufacturer of the transformer
                range=data.get("range"),  # The product range of the transformer
                efficiency=data.get("efficiency"),  # The efficiency class of the transformer
                cooling=data.get("cooling"),  # The cooling class of the transformer
                insulation=data.get("insulation"),  # The insulation technology of the transformer
            )
        else:
            z2 = complex(*data["z2"])
            ym = complex(*data["ym"])
            return cls(
                id=data["id"],
                vg=data["vg"],  # Vector Group (e.g. Dyn11)
                uhv=data["uhv"],  # Rated phase-to-phase voltages of the HV side (V)
                ulv=data["ulv"],  # Rated no-load phase-to-phase voltages of the LV side (V)
                sn=data["sn"],  # Nominal power
                z2=z2,  # Series impedance (ohm)
                ym=ym,  # Magnetizing admittance (S)
                fn=data.get("fn"),  # Frequency (Hz)
                manufacturer=data.get("manufacturer"),  # The manufacturer of the transformer
                range=data.get("range"),  # The product range of the transformer
                efficiency=data.get("efficiency"),  # The efficiency class of the transformer
                cooling=data.get("cooling"),  # The cooling class of the transformer
                insulation=data.get("insulation"),  # The insulation technology of the transformer
            )

    def _to_dict(self, include_results: bool) -> JsonDict:
        # Make sure z2 and ym are not numpy types (for JSON serialization)
        z2 = complex(self._z2)
        ym = complex(self._ym)
        data = {
            "id": self.id,
            "vg": self._vg,
            "sn": self._sn,
            "uhv": self._uhv,
            "ulv": self._ulv,
            "z2": [z2.real, z2.imag],
            "ym": [ym.real, ym.imag],
        }
        if self._fn is not None:
            data["fn"] = self._fn
        if self._has_test_results:
            data["i0"] = self._i0
            data["p0"] = self._p0
            data["psc"] = self._psc
            data["vsc"] = self._vsc
        if self._manufacturer is not None:
            data["manufacturer"] = self._manufacturer
        if self._range is not None:
            data["range"] = self._range
        if self._efficiency is not None:
            data["efficiency"] = self._efficiency
        if self._cooling is not None:
            data["cooling"] = self._cooling
        if self._insulation is not None:
            data["insulation"] = self._insulation
        return data

    def _results_to_dict(self, warning: bool, full: bool) -> NoReturn:
        msg = f"The {type(self).__name__} has no results to export."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.JSON_NO_RESULTS)

    #
    # Catalogue Mixin
    #
    @classmethod
    def catalogue_path(cls) -> Path:
        return Path(resources.files("roseau.load_flow") / "data" / "transformers").expanduser().absolute()

    @classmethod
    @lru_cache(maxsize=1)
    def _read_catalogue_data(cls) -> pd.DataFrame:
        file = cls.catalogue_path() / "Catalogue.csv"
        return pd.read_csv(
            file,
            parse_dates=False,
            dtype={
                "name": str,
                "sn": int,
                "uhv": int,
                "ulv": int,
                "fn": int,
                "vg": str,
                "vsc": float,
                "psc": float,
                "i0": float,
                "p0": float,
                "manufacturer": str,
                "range": str,
                "efficiency": str,
                "cooling": object,
                "insulation": object,
                "material": str,
                "oil": str,
                "type": str,
                "du1": float,
                "du0.8": float,
                "eff1 100%": float,
                "eff0.8 100%": float,
                "eff1 75%": float,
                "eff0.8 75%": float,
                "notes": str,
            },
        ).fillna(
            {
                "manufacturer": "",
                "efficiency": "",
                "range": "",
                "cooling": "",
                "insulation": "",
                "oil": "",
                "material": "",
                "notes": "",
            }
        )

    @classmethod
    def catalogue_data(cls, all: bool = False) -> pd.DataFrame:
        data = cls._read_catalogue_data()
        if all:
            return data.copy()
        else:
            return data[
                [
                    "name",
                    "sn",
                    "uhv",
                    "ulv",
                    "fn",
                    "vg",
                    "vsc",
                    "psc",
                    "i0",
                    "p0",
                    "manufacturer",
                    "range",
                    "efficiency",
                    "cooling",
                    "insulation",
                    "material",
                ]
            ].copy()

    @classmethod
    def _get_catalogue(
        cls,
        name: str | re.Pattern[str] | None,
        manufacturer: str | re.Pattern[str] | None,
        range: str | re.Pattern[str] | None,
        efficiency: str | re.Pattern[str] | None,
        cooling: str | None,
        insulation: str | None,
        vg: str | re.Pattern[str] | None,
        sn: float | None,
        uhv: float | None,
        ulv: float | None,
        fn: float | None,
        raise_if_not_found: bool,
    ) -> tuple[pd.DataFrame, str]:
        # Get the catalogue data
        catalogue_data = cls.catalogue_data()

        # Filter on string/regular expressions
        query_msg_list = []
        for value, column_name, display_name, display_name_plural in (
            (name, "name", "name", "names"),
            (manufacturer, "manufacturer", "manufacturer", "manufacturers"),
            (range, "range", "range", "ranges"),
            (efficiency, "efficiency", "efficiency", "efficiencies"),
            (vg, "vg", "vector group", "vector groups"),
        ):
            if pd.isna(value):
                continue

            mask = cls._filter_catalogue_str(value=value, strings=catalogue_data[column_name])
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=repr(value),
                    name=display_name,
                    name_plural=display_name_plural,
                    strings=catalogue_data[column_name],
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{column_name}={value!r}")

        # Filter on enumerated types
        for value, column_name, display_name, display_name_plural, enum_class in (
            (insulation, "insulation", "insulation", "insulations", TransformerInsulation),
            (cooling, "cooling", "cooling class", "cooling classes", TransformerCooling),
        ):
            if pd.isna(value):
                continue

            enum_series = pd.Series(
                data=[
                    None if isna else enum_class(x)
                    for isna, x in zip(
                        catalogue_data[column_name].isna(), catalogue_data[column_name].values, strict=True
                    )
                ],
                index=catalogue_data.index,
            )
            try:
                mask = enum_series == enum_class(value)
            except ValueError:
                mask = pd.Series(data=False, index=catalogue_data.index)
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=repr(value),
                    name=display_name,
                    name_plural=display_name_plural,
                    strings=enum_series,
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{display_name}={value!r}")

        # Filter on float
        for value, column_name, display_name, display_name_plural, display_unit in (
            (sn, "sn", "nominal power", "nominal powers", "kVA"),
            (uhv, "uhv", "high voltage", "high voltages", "kV"),
            (ulv, "ulv", "low voltage", "low voltages", "kV"),
            (fn, "fn", "frequency", "frequencies", "Hz"),
        ):
            if pd.isna(value):
                continue

            mask = np.isclose(catalogue_data[column_name], value)
            if raise_if_not_found and mask.sum() == 0:
                cls._raise_not_found_in_catalogue(
                    value=f"{value / 1000:.1f} {display_unit}",
                    name=display_name,
                    name_plural=display_name_plural,
                    strings=catalogue_data[column_name].apply(lambda x: f"{x / 1000:.1f} {display_unit}"),  # noqa: B023
                    query_msg_list=query_msg_list,
                )
            catalogue_data = catalogue_data.loc[mask, :]
            query_msg_list.append(f"{column_name}={value / 1000:.1f} {display_unit}")

        return catalogue_data, ", ".join(query_msg_list)

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, None, None, "VA", "V", "V", "Hz", None))
    def from_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        *,
        manufacturer: str | re.Pattern[str] | None = None,
        range: str | re.Pattern[str] | None = None,
        efficiency: str | re.Pattern[str] | None = None,
        cooling: str | TransformerCooling | None = None,
        insulation: str | TransformerInsulation | None = None,
        vg: str | re.Pattern[str] | None = None,
        sn: float | Q_[float] | None = None,
        uhv: float | Q_[float] | None = None,
        ulv: float | Q_[float] | None = None,
        fn: float | Q_[float] | None = None,
        id: Id | None = None,
    ) -> Self:
        """Build a transformer parameters from one in the catalogue.

        Args:
            name:
                The name of the transformer to get from the catalogue. It can be a regular expression.
                The name is subject to change when the catalogue is updated. Prefer using the other
                filters.

            manufacturer:
                The name of the manufacturer to get. It can be a regular expression.

            range:
                The name of the product range to get. It can be a regular expression.

            efficiency:
                The efficiency of the transformer get. It can be a regular expression.

            cooling:
                The cooling class of the transformer to get (ONAN, ONAF, etc.).  See also
                :class:`~roseau.load_flow.TransformerCooling`.

            insulation:
                The insulation technology of the transformer to get (dry-type, liquid-immersed,
                gas-filled). See also :class:`~roseau.load_flow.TransformerInsulation`.

            vg:
                The vector group of the transformer to get. It can be a regular expression.

            sn:
                The nominal power of the transformer to get.

            uhv:
                The rated phase-to-phase voltage of the HV side of the transformer to get.

            ulv:
                The rated no-load phase-to-phase voltage of the LV side of the transformer to get.

            fn:
                The nominal frequency of the transformer to get.

            id:
                A unique ID for the created transformer parameters object (optional). If ``None``
                (default), the id of the created object will be its name in the catalogue. Note that
                this parameter is not used in the data filtering.

        Returns:
            The selected transformer. If several or no transformers fitting the filters are found in
            the catalogue, an error is raised.
        """
        # Get the catalogue data
        catalogue_data, query_info = cls._get_catalogue(
            name=name,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            cooling=cooling,
            insulation=insulation,
            vg=vg,
            sn=sn,
            uhv=uhv,
            ulv=ulv,
            fn=fn,
            raise_if_not_found=True,
        )

        try:
            cls._assert_one_found(
                found_data=catalogue_data["name"].tolist(), display_name="transformers", query_info=query_info
            )
        except RoseauLoadFlowException as e:
            if name is None and id is not None:
                e.msg += " Did you mean to filter by name instead of id?"
            raise

        # A single one has been chosen
        idx = catalogue_data.index[0]
        if id is None:
            id = catalogue_data.at[idx, "name"]
        return cls.from_open_and_short_circuit_tests(
            id=id,
            vg=catalogue_data.at[idx, "vg"],
            uhv=catalogue_data.at[idx, "uhv"].item(),
            ulv=catalogue_data.at[idx, "ulv"].item(),
            sn=catalogue_data.at[idx, "sn"].item(),
            p0=catalogue_data.at[idx, "p0"].item(),
            i0=catalogue_data.at[idx, "i0"].item(),
            psc=catalogue_data.at[idx, "psc"].item(),
            vsc=catalogue_data.at[idx, "vsc"].item(),
            fn=catalogue_data.at[idx, "fn"].item(),
            manufacturer=catalogue_data.at[idx, "manufacturer"],
            range=catalogue_data.at[idx, "range"],
            efficiency=catalogue_data.at[idx, "efficiency"],
            cooling=catalogue_data.at[idx, "cooling"],
            insulation=catalogue_data.at[idx, "insulation"],
        )

    @classmethod
    @ureg_wraps(None, (None, None, None, None, None, None, None, None, "VA", "V", "V", "Hz"))
    def get_catalogue(
        cls,
        name: str | re.Pattern[str] | None = None,
        *,
        manufacturer: str | re.Pattern[str] | None = None,
        range: str | re.Pattern[str] | None = None,
        efficiency: str | re.Pattern[str] | None = None,
        cooling: str | TransformerCooling | None = None,
        insulation: str | TransformerInsulation | None = None,
        vg: str | re.Pattern[str] | None = None,
        sn: float | Q_[float] | None = None,
        uhv: float | Q_[float] | None = None,
        ulv: float | Q_[float] | None = None,
        fn: float | Q_[float] | None = None,
    ) -> pd.DataFrame:
        """Get the catalogue of available transformers.

        You can use the parameters below to filter the catalogue. If you do not specify any
        parameter, all the catalogue will be returned.

        Args:
            name:
                An optional name to filter the output. It can be a regular expression.

            manufacturer:
                An optional manufacturer to filter the output. It can be a regular expression.

            range:
                An optional product range to filter the output. It can be a regular expression.

            efficiency:
                An optional efficiency to filter the output. It can be a regular expression.

            cooling:
                An optional cooling class to filter the output (ONAN, ONAF, etc.). See also
                :class:`~roseau.load_flow.TransformerCooling`.

            insulation:
                An optional transformer insulation technology to filter the output (dry-type,
                liquid-immersed, gas-filled). See also :class:`~roseau.load_flow.TransformerInsulation`.

            vg:
                An optional vector group of the transformer. It can be a regular expression.

            sn:
                An optional nominal power of the transformer to filter the output.

            uhv:
                An optional rated high voltage to filter the output.

            ulv:
                An optional rated no-load low voltage to filter the output.

            fn:
                An optional nominal frequency to filter the output.

        Returns:
            The catalogue data as a dataframe.
        """
        catalogue_data, _ = cls._get_catalogue(
            name=name,
            manufacturer=manufacturer,
            range=range,
            efficiency=efficiency,
            cooling=cooling,
            insulation=insulation,
            vg=vg,
            sn=sn,
            uhv=uhv,
            ulv=ulv,
            fn=fn,
            raise_if_not_found=False,
        )
        catalogue_data["sn"] /= 1000  # kVA
        catalogue_data["uhv"] /= 1000  # kV
        catalogue_data["ulv"] /= 1000  # kV
        return (
            catalogue_data[["name", "manufacturer", "range", "efficiency", "cooling", "vg", "sn", "uhv", "ulv", "fn"]]
            .rename(
                columns={
                    "name": "Name",
                    "manufacturer": "Manufacturer",
                    "range": "Product range",
                    "efficiency": "Efficiency",
                    "cooling": "Cooling class",
                    "vg": "Vector group",
                    "sn": "Nominal power (kVA)",
                    "uhv": "High voltage (kV)",
                    "ulv": "Low voltage (kV)",
                    "fn": "Frequency (Hz)",
                    # # If we ever want to display these columns
                    # "insulation": "Insulation technology",
                    # "type": "Type",
                    # "oil": "Oil",
                    # "material": "Material",
                    # "i0": "No-load current (%)",
                    # "p0": "No-load losses (W)",
                    # "psc": "Load Losses at 75°C  (W)",
                    # "vsc": "Impedance voltage (%)",
                }
            )
            .set_index("Name")
        )

    #
    # Utils
    #
    @classmethod
    def extract_windings(cls, vg: str) -> tuple[str, str, int]:
        """Extract the windings and phase displacement from a given vector group

        Args:
            vg:
                The vector group of the transformer.

                For three-phase transformers, ``Dyn11`` denotes a delta-wye connection with -30° phase
                displacement. Allowed windings are ``D`` for delta, ``Y`` for wye, ``Z`` for zigzag.

                For single-phase transformers, ``Ii0`` denotes a normal in-phase connection and
                ``Ii6`` denotes an inverted connection.

                For center-tapped transformers, ``Iii0`` denotes a normal in-phase connection and
                ``Iii6`` denotes an inverted connection.

        Returns:
            The HV winding, the LV winding, and the phase displacement.
        """
        vg_norm = vg.capitalize().replace("Yn", "YN", 1).replace("Zn", "ZN", 1)
        if vg_norm in cls.allowed_vector_groups:
            whv = vg_norm[:2] if vg_norm[1] == "N" else vg_norm[0]
            vg_norm = vg_norm.removeprefix(whv)
            wlv = vg_norm[:2] if vg_norm[1] in "in" else vg_norm[0]
            vg_norm = vg_norm.removeprefix(wlv)
            clock = int(vg_norm)
            return whv, wlv, clock
        else:
            msg = f"Invalid vector group: {vg!r}. Expected one of {sorted(cls.allowed_vector_groups)}."
            logger.error(msg)
            raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_VECTOR_GROUP)
