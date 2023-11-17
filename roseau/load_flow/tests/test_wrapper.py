import operator

import pytest
from pint import DimensionalityError

from roseau.load_flow import ureg
from roseau.load_flow.units import ureg_wraps


def test_wraps():
    def func(x):
        return x

    with pytest.raises(TypeError):
        ureg_wraps((3 * ureg.meter, [None]))
    with pytest.raises(TypeError):
        ureg_wraps((None, [3 * ureg.meter]))

    f0 = ureg_wraps(None, [None])(func)
    assert f0(3.0) == 3.0

    f0 = ureg_wraps(None, None)(func)
    assert f0(3.0) == 3.0

    f1 = ureg_wraps(None, ["meter"])(func)
    assert f1(3.0 * ureg.centimeter) == 0.03
    assert f1(3.0 * ureg.meter) == 3.0
    with pytest.raises(DimensionalityError):
        f1(3 * ureg.second)

    f1b = ureg_wraps(None, [ureg.meter])(func)
    assert f1b(3.0 * ureg.centimeter) == 0.03
    assert f1b(3.0 * ureg.meter) == 3.0
    with pytest.raises(DimensionalityError):
        f1b(3 * ureg.second)

    f1c = ureg_wraps("meter", [ureg.meter])(func)
    assert f1c(3.0 * ureg.centimeter) == 0.03 * ureg.meter
    assert f1c(3.0 * ureg.meter) == 3.0 * ureg.meter
    with pytest.raises(DimensionalityError):
        f1c(3 * ureg.second)

    f1d = ureg_wraps(ureg.meter, [ureg.meter])(func)
    assert f1d(3.0 * ureg.centimeter) == 0.03 * ureg.meter
    assert f1d(3.0 * ureg.meter) == 3.0 * ureg.meter
    with pytest.raises(DimensionalityError):
        f1d(3 * ureg.second)

    f1 = ureg_wraps(None, "meter")(func)
    assert f1(3.0 * ureg.centimeter) == 0.03
    assert f1(3.0 * ureg.meter) == 3.0
    with pytest.raises(DimensionalityError):
        f1(3 * ureg.second)

    f2 = ureg_wraps("centimeter", ["meter"])(func)
    assert f2(3.0 * ureg.centimeter) == 0.03 * ureg.centimeter
    assert f2(3.0 * ureg.meter) == 3 * ureg.centimeter
    assert f2(3) == 3 * ureg.centimeter

    gfunc = operator.add

    g0 = ureg_wraps(None, [None, None])(gfunc)
    assert g0(3, 1) == 4

    g1 = ureg_wraps(None, ["meter", "centimeter"])(gfunc)
    assert g1(3 * ureg.meter, 1 * ureg.centimeter) == 4
    assert g1(3 * ureg.meter, 1 * ureg.meter) == 3 + 100

    def hfunc(x, y):
        return x, y

    h0 = ureg_wraps(None, [None, None])(hfunc)
    assert h0(3, 1) == (3, 1)

    h1 = ureg_wraps(["meter", "centimeter"], [None, None])(hfunc)
    assert h1(3, 1) == [3 * ureg.meter, 1 * ureg.cm]

    h2 = ureg_wraps(("meter", "centimeter"), [None, None])(hfunc)
    assert h2(3, 1) == (3 * ureg.meter, 1 * ureg.cm)

    h3 = ureg_wraps((None,), (None, None))(hfunc)
    assert h3(3, 1) == (3, 1)

    def kfunc(a, /, b, c=5, *, d=6):
        return a, b, c, d

    k1 = ureg_wraps((None,), (None, None, None, None))(kfunc)
    assert k1(1, 2, 3, d=4) == (1, 2, 3, 4)
    assert k1(1, 2, c=3, d=4) == (1, 2, 3, 4)
    assert k1(1, b=2, c=3, d=4) == (1, 2, 3, 4)
    assert k1(1, d=4, b=2, c=3) == (1, 2, 3, 4)
    assert k1(1, 2, c=3) == (1, 2, 3, 6)
    assert k1(1, 2, d=4) == (1, 2, 5, 4)
    assert k1(1, 2) == (1, 2, 5, 6)

    k2 = ureg_wraps((None,), ("meter", "centimeter", "meter", "centimeter"))(kfunc)
    assert k2(1 * ureg.meter, 2 * ureg.centimeter, 3 * ureg.meter, d=4 * ureg.centimeter) == (1, 2, 3, 4)

    def lfunc(a):
        return a[0]

    l1 = ureg_wraps("centimeter", ("meter",))(lfunc)
    assert l1([1, 2]) == 1 * ureg.centimeter
    assert l1([1, 2] * ureg.meter) == 1 * ureg.centimeter
    assert l1([1 * ureg.meter, 2 * ureg.meter]) == 1 * ureg.centimeter
