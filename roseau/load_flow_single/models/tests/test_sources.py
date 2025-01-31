import numpy as np
import pytest
from pint.errors import DimensionalityError

from roseau.load_flow import Q_
from roseau.load_flow.testing import assert_json_close
from roseau.load_flow_single.models import Bus, VoltageSource


def test_sources_to_dict():
    bus = Bus(id="bus")
    value = 1 + 2j

    # Power source
    assert_json_close(
        VoltageSource(id="vs1", bus=bus, voltage=value).to_dict(include_results=False),
        {"id": "vs1", "bus": "bus", "type": "voltage", "voltage": [1.0, 2.0]},
    )
    assert_json_close(
        VoltageSource(id="vs2", bus=bus, voltage=value).to_dict(include_results=False),
        {"id": "vs2", "bus": "bus", "type": "voltage", "voltage": [1.0, 2.0]},
    )


def test_sources_units():
    bus = Bus(id="bus")

    # Good unit constructor
    source = VoltageSource(id="vs1", bus=bus, voltage=Q_(1, "kV"))
    assert np.allclose(source._voltage, 1000)

    # Good unit setter
    source = VoltageSource(id="vs2", bus=bus, voltage=100)
    assert np.allclose(source._voltage, 100)
    source.voltage = Q_(1, "kV")
    assert np.allclose(source._voltage, 1000)

    # Bad unit constructor
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'V'"):
        VoltageSource(id="vs3", bus=bus, voltage=Q_(100, "A"))

    # Bad unit setter
    source = VoltageSource(id="vs4", bus=bus, voltage=100)
    with pytest.raises(DimensionalityError, match=r"Cannot convert from 'ampere' \(\[current\]\) to 'V'"):
        source.voltage = Q_(100, "A")
