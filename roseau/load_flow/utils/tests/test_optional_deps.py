import pytest

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.utils import _optional_deps


def test_optional_deps(monkeypatch):
    # Working deps
    plt = _optional_deps.pyplot
    assert plt.__class__.__name__ == "module"
    networkx = _optional_deps.networkx
    assert networkx.__class__.__name__ == "module"

    # Fail
    with pytest.raises(AttributeError) as e:
        _optional_deps.toto  # noqa: B018
    assert e.value.args[0] == "module roseau.load_flow.utils._optional_deps has no attribute 'toto'"

    # Module not installed
    def fake_import(name, *args, **kwargs):
        raise ImportError(name, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr("builtins.__import__", fake_import)

        with pytest.raises(RoseauLoadFlowException) as e:
            _optional_deps.pyplot  # noqa: B018
        assert (
            e.value.msg == 'matplotlib is required for plotting. Install it with the "plot" extra using '
            '`pip install -U "roseau-load-flow[plot]"`'
        )
        assert e.value.code == RoseauLoadFlowExceptionCode.IMPORT_ERROR

        with pytest.raises(RoseauLoadFlowException) as e:
            _optional_deps.networkx  # noqa: B018
        assert (
            e.value.msg == 'networkx is not installed. Install it with the "graph" extra using `pip install -U '
            '"roseau-load-flow[graph]"`'
        )
        assert e.value.code == RoseauLoadFlowExceptionCode.IMPORT_ERROR
