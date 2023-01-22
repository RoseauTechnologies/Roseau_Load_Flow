import numpy as np

from roseau.load_flow import Bus


def test_bus_potentials_of_phases():
    bus = Bus("bus", phases="abcn")
    bus._res_potentials = [1, 2, 3, 4]

    assert np.allclose(bus._get_potentials_of("abcn", warning=False), [1, 2, 3, 4])
    assert isinstance(bus._get_potentials_of("abcn", warning=False), np.ndarray)

    assert np.allclose(bus._get_potentials_of("abc", warning=False), [1, 2, 3])
    assert np.allclose(bus._get_potentials_of("ca", warning=False), [3, 1])
    assert np.allclose(bus._get_potentials_of("n", warning=False), [4])
    assert np.allclose(bus._get_potentials_of("", warning=False), [])
