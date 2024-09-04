import datetime as dt
import logging
import os

import certifi
from platformdirs import user_cache_dir

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_engine.cy_engine import CyLicense, cy_activate_license, cy_deactivate_license, cy_get_license

logger = logging.getLogger(__name__)

__all__ = ["activate_license", "deactivate_license", "get_license", "License"]

# Cache the license object. Cache cleared when the license is deactivated
_license: "License | None" = None


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
        """The key of the license. Please do not share this key."""
        return self.cy_license.key

    @property
    def expiry_datetime(self) -> dt.datetime | None:
        """The expiry date of the license or ``None`` if the license has no expiry date."""
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

    @property
    def machine_fingerprint(self) -> str:
        """The anonymized machine fingerprint for license validation."""
        return self.cy_license.machine_fingerprint

    @staticmethod
    def get_hostname() -> str:
        """This method retrieves the hostname of your computer."""
        return CyLicense.get_hostname()

    @staticmethod
    def get_username() -> str:
        """This method retrieves your username."""
        return CyLicense.get_username()


def activate_license(key: str | None = None) -> None:
    """Activate a license in the current process.

    Args:
        key:
            The key of the license to activate. If ``None`` is provided (default), the environment
            variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` is used. If this variable is not set, an error
            is raised.
    """
    global _license
    if key is None:
        key = os.getenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", "")
    try:
        cy_activate_license(key=key, cacert_filepath=certifi.where(), cache_folderpath=user_cache_dir())
        _license = None
    except RuntimeError as e:
        msg = f"The license cannot be activated. The detailed error message is {e.args[0][2:]!r}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LICENSE_ERROR) from e


def deactivate_license() -> None:
    """Deactivate the currently active license."""
    global _license
    cy_deactivate_license()
    _license = None


def get_license() -> License | None:
    """Get the currently active license or ``None`` if no license is activated."""
    global _license
    if _license is None:
        cy_license = cy_get_license()
        if cy_license is None:
            return None
        else:
            _license = License(cy_license=cy_license)
    return _license
