import datetime as dt
import logging
import os
import re

import certifi
from platformdirs import user_cache_dir

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow_engine.cy_engine import (
    PUBLIC_LICENSE_KEY,
    CyLicense,
    cy_activate_license,
    cy_deactivate_license,
    cy_get_license,
)

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
        """The anonymized machine fingerprint for license validation. It is empty for an offline license."""
        return self.cy_license.machine_fingerprint

    @property
    def offline(self) -> bool:
        """Is the license verified offline, without contacting the license server? This is the case of the free
        trial license used when no license key is provided."""
        return self.cy_license.offline

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
            variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` is used. If this variable is not set either, the
            free trial license is used: it is limited to networks of up to 50 buses and a warning is
            logged.
    """
    global _license
    trial = False
    if key is None:
        key = os.getenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", "")
        if not key:
            key = PUBLIC_LICENSE_KEY
            trial = True
    try:
        cy_activate_license(key=key, cacert_filepath=certifi.where(), cache_folderpath=user_cache_dir())
        _license = None
    except RuntimeError as e:
        err_msg = e.args[0]
        if re.search(r"^[0-2] ", err_msg):
            err_msg = err_msg[2:]
        msg = f"The license cannot be activated. The detailed error message is {err_msg!r}."
        logger.error(msg)
        raise RoseauLoadFlowException(msg=msg, code=RoseauLoadFlowExceptionCode.LICENSE_ERROR) from e
    if trial:
        lic = get_license()
        max_nb_buses = lic.max_nb_buses if lic is not None else None
        limit = "no bus limit" if max_nb_buses is None else f"networks of up to {max_nb_buses} buses"
        logger.warning(
            f"No license key has been provided: the free trial license is used ({limit}). Please use "
            f"`activate_license(key)` or set the `ROSEAU_LOAD_FLOW_LICENSE_KEY` environment variable to use "
            f"your own license."
        )


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
