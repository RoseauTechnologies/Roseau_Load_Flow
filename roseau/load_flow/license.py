import datetime as dt
import logging
import os

import certifi
from platformdirs import user_cache_dir

from roseau.load_flow import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_engine.cy_engine import CyLicense, cy_activate_license, cy_deactivate_license, cy_get_license

logger = logging.getLogger(__name__)

__all__ = ["activate_license", "deactivate_license", "get_license", "License"]

_license = None
"""str|None: The Python copy of the activated license."""


#
# License class accessor
#
class License:
    """A class to access the main data of the License."""

    def __init__(self, cy_license: CyLicense) -> None:
        """Constructor for a License

        Args:
            cy_license:
                The Cython license object
        """
        self.cy_license = cy_license

    @property
    def key(self) -> str:
        """The key of the license"""
        return self.cy_license.key

    @property
    def expiry_datetime(self) -> dt.datetime | None:
        """The expiry date of the license."""
        exp_dt = self.cy_license.expiry_datetime
        if exp_dt is None:
            return None
        try:
            return dt.datetime.fromisoformat(exp_dt)
        except ValueError:
            return None

    @property
    def valid(self) -> bool:
        """Is the license valid?"""
        return self.cy_license.valid

    @property
    def max_nb_buses(self) -> int | None:
        """The maximum allowed number of buses for a network. If `None`, the license has no limitation."""
        return self.cy_license.max_nb_buses

    @staticmethod
    def get_machine_fingerprint() -> str:
        """This method retrieves your machine fingerprint for license validation."""
        return CyLicense.get_machine_fingerprint()

    @staticmethod
    def get_hostname() -> str:
        """This method retrieves the hostname of your computer."""
        return CyLicense.get_hostname()

    @staticmethod
    def get_username() -> str:
        """This method retrieves your username."""
        return CyLicense.get_username()


def activate_license(key: str | None = None) -> None:
    """Activate the license with the given key in the current process.

    Args:
        key:
            The key of the license to activate. If `None` is provided, the environment variable
            `ROSEAU_LOAD_FLOW_LICENSE_KEY` is read.
    """
    if key is None:
        key = os.getenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", "")
    try:
        cy_activate_license(key=key, cacert_filepath=certifi.where(), cache_folderpath=user_cache_dir())
    except RuntimeError as e:
        msg = f"The license can not be activated. The detailed error message is {e.args[0]!r}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LICENSE_ERROR) from e


def deactivate_license() -> None:
    """Deactivate the license in the current process."""
    global _license
    cy_deactivate_license()
    _license = None


def get_license() -> License | None:
    """A function to retrieve the currently active license."""
    global _license
    if _license is None:
        cy_license = cy_get_license()
        if cy_license is None:
            return None
        else:
            _license = License(cy_license=cy_license)
    return _license
