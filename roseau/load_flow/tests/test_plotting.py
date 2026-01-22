from unittest.mock import Mock

import numpy as np
import numpy.testing as npt
import pytest

import roseau.load_flow_single as rlfs
from roseau.load_flow.models import (
    Bus,
    Line,
    LineParameters,
    PowerLoad,
    Switch,
    Transformer,
    TransformerParameters,
    VoltageSource,
)
from roseau.load_flow.network import ElectricalNetwork
from roseau.load_flow.plotting import (
    plot_interactive_map,
    plot_results_interactive_map,
    plot_symmetrical_voltages,
    plot_voltage_phasors,
)
from roseau.load_flow.sym import PositiveSequence


@pytest.fixture
def mock_gca(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr("matplotlib.pyplot.gca", Mock)
        yield m


@pytest.fixture
def mock_subplots(monkeypatch):
    def subplots(nrows, ncols):
        return Mock(), np.array([Mock() for _ in range(nrows * ncols)]).reshape(nrows, ncols).squeeze()

    with monkeypatch.context() as m:
        m.setattr("matplotlib.pyplot.subplots", subplots)
        yield m


@pytest.fixture(scope="module")
def elements():
    bus = Bus(id="Bus", phases="abcn")
    source = VoltageSource(id="Source", bus=bus, phases="abcn", voltages=230)
    load = PowerLoad(id="Load", bus=bus, phases="abcn", powers=1e3)
    potentials = 230 * np.array([*PositiveSequence, 0.0j])
    currents = 1e3 / np.array([*potentials[:3], np.inf])
    bus._res_potentials = np.array(potentials, dtype=np.complex128)
    load._res_potentials = np.array(potentials, dtype=np.complex128)
    load._res_currents = np.array(currents, dtype=np.complex128)
    source._res_potentials = np.array(potentials, dtype=np.complex128)
    source._res_currents = np.array(-currents, dtype=np.complex128)
    bus_single = rlfs.Bus(id="Bus")
    bus_single._res_voltage = 400 + 0j
    return {"bus": bus, "load": load, "source": source, "bus_single": bus_single}


@pytest.mark.usefixtures("mock_gca")
@pytest.mark.parametrize(
    ("element_key", "voltage_type"),
    (
        pytest.param("bus", "auto", id="Bus"),
        pytest.param("bus", "pp", id="Bus-pp"),
        pytest.param("bus", "pn", id="Bus-pn"),
        pytest.param("load", "auto", id="Load"),
        pytest.param("source", "auto", id="Source"),
    ),
)
def test_plot_voltage_phasors(element_key, voltage_type, elements):
    element = elements[element_key]
    ax = plot_voltage_phasors(element, voltage_type=voltage_type)

    # The title is set to the element's id
    ax.set_title.assert_called_once_with(f"{element.id}")  # type: ignore
    ua, ub, uc, un = element._res_potentials

    if voltage_type == "pp":
        n = 3
        voltages = [(ua, ub), (ub, uc), (uc, ua)]
    else:
        n = 4
        voltages = [(ua, un), (ub, un), (uc, un)]

    # Draws three (3P) or four (3P+N) potential points
    assert ax.scatter.call_count == n  # type: ignore
    for u, phase, call in zip(element._res_potentials[:n], element.phases[:n], ax.scatter.call_args_list, strict=True):  # type: ignore
        assert call.args == (u.real, u.imag)
        assert call.kwargs["label"] == phase

    # Draws three voltage phasors
    assert ax.arrow.call_count == 3  # type: ignore
    for (u1, u2), call in zip(voltages, ax.arrow.call_args_list, strict=True):  # type: ignore
        npt.assert_allclose(call.args, (u2.real, u2.imag, u1.real - u2.real, u1.imag - u2.imag))
        assert "label" not in call.kwargs


@pytest.mark.usefixtures("mock_gca")
def test_plot_voltage_phasors_errors(elements):
    bus_abc = Bus(id="Bus", phases="abc")
    bus_an = Bus(id="Bus", phases="an")
    bus_abc._res_potentials = np.array(20e3 * PositiveSequence, dtype=np.complex128)
    bus_an._res_potentials = np.array([230, 0.0j], dtype=np.complex128)

    # By default both work
    ax = plot_voltage_phasors(bus_abc)
    assert ax.scatter.call_count == 3  # type: ignore
    ax = plot_voltage_phasors(bus_an)
    assert ax.scatter.call_count == 2  # type: ignore

    # 'pn' without neutral
    with pytest.raises(ValueError, match=r"The element must have a neutral to plot phase-to-neutral voltages"):
        plot_voltage_phasors(bus_abc, voltage_type="pn")

    # 'pp' with a single phase
    with pytest.raises(ValueError, match=r"The element must have more than one phase to plot phase-to-phase voltages"):
        plot_voltage_phasors(bus_an, voltage_type="pp")

    # Bad voltage type
    with pytest.raises(ValueError, match=r"Invalid voltage_type: 'bad'"):
        plot_voltage_phasors(bus_abc, voltage_type="bad")  # type: ignore

    # Not a multi-phase element
    bus_single = elements["bus_single"]
    with pytest.raises(TypeError, match=r"Only multi-phase elements can be plotted. Did you mean to use rlf.Bus\?"):
        plot_voltage_phasors(bus_single)  # type: ignore


@pytest.mark.usefixtures("mock_gca")
def test_plot_voltage_phasors_branches():
    b1 = Bus(id="B1", phases="abc")
    b2 = Bus(id="B2", phases="abc")
    sw = Switch(id="Sw", bus1=b1, bus2=b2)
    lp = LineParameters(id="LP", z_line=0.01 * np.eye(3))
    ln = Line(id="Ln", bus1=b1, bus2=b2, parameters=lp, length=1.0)
    tp = TransformerParameters(id="TP", vg="Dd0", uhv=20e3, ulv=20e3, sn=100e3, z2=0.01, ym=0.01j)
    tr = Transformer(id="Tr", bus_hv=b1, bus_lv=b2, parameters=tp)
    potentials = 20e3 * PositiveSequence
    b1._res_potentials = np.array(potentials, dtype=np.complex128)
    b2._res_potentials = np.array(potentials, dtype=np.complex128)
    sw.side1._res_potentials = np.array(potentials, dtype=np.complex128)
    sw.side2._res_potentials = np.array(potentials, dtype=np.complex128)
    ln.side1._res_potentials = np.array(potentials, dtype=np.complex128)
    ln.side2._res_potentials = np.array(potentials, dtype=np.complex128)
    tr.side_hv._res_potentials = np.array(potentials, dtype=np.complex128)
    tr.side_lv._res_potentials = np.array(potentials / 2, dtype=np.complex128)

    # Switches warnings
    ax = plot_voltage_phasors(sw.side1)
    ax.set_title.assert_called_once_with("Sw (1)")  # type: ignore
    ax = plot_voltage_phasors(sw.side2)
    ax.set_title.assert_called_once_with("Sw (2)")  # type: ignore

    # Lines
    ax = plot_voltage_phasors(ln.side1)
    ax.set_title.assert_called_once_with("Ln (1)")  # type: ignore
    ax = plot_voltage_phasors(ln.side2)
    ax.set_title.assert_called_once_with("Ln (2)")  # type: ignore

    # Transformers
    ax = plot_voltage_phasors(tr.side_hv)
    ax.set_title.assert_called_once_with("Tr (HV)")  # type: ignore
    npt.assert_allclose(abs(complex(*ax.scatter.call_args.args)), 20e3)  # type: ignore
    ax = plot_voltage_phasors(tr.side_lv)
    ax.set_title.assert_called_once_with("Tr (LV)")  # type: ignore
    npt.assert_allclose(abs(complex(*ax.scatter.call_args.args)), 10e3)  # type: ignore


@pytest.mark.usefixtures("mock_subplots")
def test_plot_symmetrical_voltages(elements):
    bus = elements["bus"]
    ax0, ax1, ax2 = plot_symmetrical_voltages(bus)

    # The title is set to the element's id
    ax0.set_title.assert_called_once_with(f"{bus.id}\nZero Sequence")  # type: ignore
    ax1.set_title.assert_called_once_with(f"{bus.id}\nPositive Sequence")  # type: ignore
    ax2.set_title.assert_called_once_with(f"{bus.id}\nNegative Sequence")  # type: ignore
    ua, ub, uc, un = bus._res_potentials  # type: ignore

    assert ax0.scatter.call_count == 2  # 1 "abc" + 1 "n"  # type: ignore
    assert ax0.arrow.call_count == 1  # type: ignore
    assert ax0.annotate.call_count == 1  # type: ignore

    for ax in (ax1, ax2):
        assert ax.scatter.call_count == 3  # 1 "a" + "b" + "c"  # type: ignore
        assert ax.arrow.call_count == 3  # type: ignore
        assert ax.annotate.call_count == 1  # type: ignore

    # Not a multi-phase element
    bus_single = elements["bus_single"]
    with pytest.raises(TypeError, match=r"Only multi-phase elements can be plotted. Did you mean to use rlf.Bus\?"):
        plot_symmetrical_voltages(bus_single)  # type: ignore


def test_plot_interactive_map(test_networks_path):
    en = ElectricalNetwork.from_json(path=test_networks_path / "all_element_network.json", include_results=True)
    en.crs = "EPSG:4326"
    plot_interactive_map(en)
    plot_results_interactive_map(en)
