"""Root conftest for patching Cy classes."""

import importlib
import inspect
import os
from itertools import chain
from pathlib import Path

import pytest
import roseau.load_flow_engine.cy_engine as cy_engine


class PatchedCyObject:
    def __init__(self, *args, **kwargs):  # Accept all constructor parameters
        pass

    def __getattr__(self, attr: str):  # Accept all methods
        if attr.startswith("__array"):  # Leave the numpy interface
            return object.__getattr__(self, attr)
        return self.patched_cy_method

    def patched_cy_method(self, *args, **kwargs):
        pass


def patched_cy_activate_license(*args, **kwargs):  # pragma: no-cover
    pass


_CY_CLASSES_WITH_BASES = {
    "CyElement": (),
    "CyBus": ("CyElement",),
    "CyBranch": ("CyElement",),
    "CySimplifiedLine": ("CyBranch",),
    "CyShuntLine": ("CyBranch",),
    "CySwitch": ("CyBranch",),
    "CyOpenSwitch": ("CyBranch",),
    "CyTransformer": ("CyBranch",),
    "CyThreePhaseTransformer": ("CyTransformer",),
    "CySingleTransformer": ("CyTransformer",),
    "CyCenterTransformer": ("CyTransformer",),
    "CySingleVoltageRegulator": ("CyBranch",),
    "CyLoad": ("CyElement",),
    "CyPowerLoad": ("CyLoad",),
    "CyDeltaPowerLoad": ("CyLoad",),
    "CyAdmittanceLoad": ("CyLoad",),
    "CyDeltaAdmittanceLoad": ("CyLoad",),
    "CyCurrentLoad": ("CyLoad",),
    "CyDeltaCurrentLoad": ("CyLoad",),
    "CyLoadBalancer": ("CyLoad",),
    "CyControl": (),
    "CyProjection": (),
    "CyFlexibleParameter": (),
    "CyFlexibleLoad": ("CyLoad",),
    "CyDeltaFlexibleLoad": ("CyLoad",),
    "CyVoltageSource": ("CyElement",),
    "CyDeltaVoltageSource": ("CyElement",),
    "CyGround": ("CyElement",),
    "CyPotentialRef": ("CyElement",),
    "CyDeltaPotentialRef": ("CyElement",),
    "CyElectricalNetwork": (),
    "CyLicense": (),
    "CyAbstractSolver": (),
    "CyAbstractNewton": ("CyAbstractSolver",),
    "CyNewton": ("CyAbstractNewton",),
    "CyNewtonGoldstein": ("CyAbstractNewton",),
    "CyBackwardForward": ("CyAbstractSolver",),
}
_PATCHED_CY_CLASSES: dict[str, type[PatchedCyObject]] = {}
for _name, _bases in _CY_CLASSES_WITH_BASES.items():
    _resolved = tuple(_PATCHED_CY_CLASSES[b] for b in _bases) or (PatchedCyObject,)
    _PATCHED_CY_CLASSES[_name] = type(_name, _resolved, {})
# Backfill missing Cy classes in the cy_engine module with stubs, so that imports
# of model modules succeed even if the installed binary is older than the source.
for name, stub in _PATCHED_CY_CLASSES.items():
    if not hasattr(cy_engine, name):
        setattr(cy_engine, name, stub)


@pytest.fixture(autouse=True)
def patch_engine(request):
    """Monkeypatch all Cy classes in *extra_dirs* and the rlf package directory.

    Call with one or more extra directories to also patch Cy classes imported
    by modules in those directories (e.g. the ``roseau.load_flow_single`` tree).
    """
    from roseau.load_flow.utils.log import set_logging_config

    mpatch = pytest.MonkeyPatch()

    if "no_patch_engine" in request.keywords:
        # A real load flow must be solved in this test.
        if os.getenv("ROSEAU_LOAD_FLOW_LICENSE_KEY") is None:  # pragma: no-cover
            pytest.skip(
                reason="This test requires a license key. Please set ROSEAU_LOAD_FLOW_LICENSE_KEY in your environment."
            )
        set_logging_config("debug")
    else:
        import roseau.load_flow as rlf
        import roseau.load_flow_single as rlfs

        rlf_dir = Path(rlf.__file__).parent
        rlfs_dir = Path(rlfs.__file__).parent
        relative_to = rlf_dir.parents[1]  # …/roseau/ → Roseau_Load_Flow/
        dirs = [rlf_dir, rlfs_dir]
        for dirpath, _, filenames in chain.from_iterable(os.walk(d) for d in dirs):
            dirpath = Path(dirpath)
            for p in dirpath.parts:
                if p in {"tests", "__pycache__", "data"}:
                    break
            else:
                base_module = str(dirpath.relative_to(relative_to)).replace("/", ".")
                for f in filenames:
                    if not f.endswith(".py"):
                        continue
                    module = importlib.import_module(f"{base_module}.{f.removesuffix('.py')}")
                    for _, klass in inspect.getmembers(
                        module,
                        lambda member: (
                            inspect.isclass(member)
                            and "load_flow_engine." in member.__module__
                            and member.__name__.startswith("Cy")
                            and member.__name__ != "CyLicense"
                        ),  # CyLicense uses static methods tested directly
                    ):
                        mpatch.setattr(
                            f"{module.__name__}.{klass.__name__}",
                            _PATCHED_CY_CLASSES[klass.__name__],
                        )

        mpatch.setattr("roseau.load_flow.license.cy_activate_license", patched_cy_activate_license)

    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", autouse=True)
def patch_warn_external():
    import roseau.load_flow as rlf
    from roseau.load_flow.utils import helpers

    # Scan the whole roseau/ tree (covers both load_flow and load_flow_single).
    roseau_dir = Path(rlf.__file__).resolve().parent.parent
    paths = tuple(str(p) for p in roseau_dir.rglob("load_flow*/**/*.py") if "tests" not in p.parts)
    helpers._get_skip_file_prefixes = lambda: paths
