import importlib
import inspect
import os
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

import roseau.load_flow
from roseau.load_flow.utils.log import set_logging_config

HERE = Path(__file__).parent.expanduser().absolute()
TEST_ALL_NETWORKS_DATA_FOLDER = HERE / "tests" / "data" / "networks"

TEST_DGS_NETWORKS = list((HERE / "tests" / "data" / "dgs").rglob("*.json"))
TEST_DGS_NETWORKS_IDS = [x.stem for x in TEST_DGS_NETWORKS]
TEST_DGS_SPECIAL_NETWORKS_DIR = HERE / "tests" / "data" / "dgs" / "special"


# Patch the engine
class PatchedCyObject:
    def __init__(self, *args, **kwargs):  # Accept all constructor parameters
        pass

    def __getattr__(self, attr: str):  # Accept all methods
        if attr.startswith("__array"):  # Leave the numpy interface
            return object.__getattr__(self, attr)
        else:
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
    "CyTransformer": ("CyBranch",),
    "CyThreePhaseTransformer": ("CyTransformer",),
    "CySingleTransformer": ("CyTransformer",),
    "CyCenterTransformer": ("CyTransformer",),
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
for class_name, bases in _CY_CLASSES_WITH_BASES.items():
    bases = tuple(_PATCHED_CY_CLASSES[base] for base in bases) or (PatchedCyObject,)
    _PATCHED_CY_CLASSES[class_name] = type(class_name, bases, {})


@pytest.fixture(autouse=True)
def patch_engine(request):
    mpatch = MonkeyPatch()

    if "no_patch_engine" in request.keywords:
        # A load flow must be solved in the test
        # Skip if no license key in the environment
        if os.getenv("ROSEAU_LOAD_FLOW_LICENSE_KEY") is None:  # pragma: no-cover
            pytest.skip(
                reason="This test requires a license key. Please set ROSEAU_LOAD_FLOW_LICENSE_KEY in your environment."
            )

        # Activate logging
        set_logging_config("debug")
    else:
        # Get all roseau.load_flow submodules
        rlf_directory_path = Path(roseau.load_flow.__file__).parent
        relative_to = Path(roseau.load_flow.__file__).parents[2]
        for dirpath, _, filenames in os.walk(rlf_directory_path):  # TODO In Python 3.12 use rlf_directory_path.walk()
            dirpath = Path(dirpath)  # TODO Useless in Python 3.12
            for p in dirpath.parts:
                if p in {"tests", "__pycache__", "data"}:
                    break
            else:
                base_module = str(dirpath.relative_to(relative_to)).replace("/", ".")
                for f in filenames:
                    if not f.endswith(".py"):
                        continue
                    if f in ("constants.py", "types.py") and base_module == "roseau.load_flow.utils":
                        continue  # TODO: Remove when deprecated modules are removed
                    module = importlib.import_module(f"{base_module}.{f.removesuffix('.py')}")
                    for _, klass in inspect.getmembers(
                        module,
                        lambda member: inspect.isclass(member)
                        and "load_flow_engine." in member.__module__
                        and member.__name__.startswith("Cy")
                        and member.__name__ != "CyLicense",  # Test of the static methods of this class
                    ):
                        mpatch.setattr(f"{module.__name__}.{klass.__name__}", _PATCHED_CY_CLASSES[klass.__name__])

        # Also patch the activate license function of the _solvers module
        mpatch.setattr("roseau.load_flow.license.cy_activate_license", patched_cy_activate_license)

    yield mpatch
    mpatch.undo()


@pytest.fixture(params=["impedance", "power"], ids=["impedance", "power"])
def network_load_data_name(request) -> str:
    return request.param


@pytest.fixture(params=TEST_DGS_NETWORKS, ids=TEST_DGS_NETWORKS_IDS)
def dgs_network_path(request) -> Path:
    return request.param


@pytest.fixture
def dgs_special_network_dir() -> Path:
    return TEST_DGS_SPECIAL_NETWORKS_DIR


@pytest.fixture
def test_networks_path() -> Path:
    return TEST_ALL_NETWORKS_DATA_FOLDER
