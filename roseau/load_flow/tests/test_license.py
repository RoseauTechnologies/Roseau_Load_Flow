import datetime as dt

import certifi
import pytest
from platformdirs import user_cache_dir

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.license import License, activate_license, deactivate_license


class FakeCyLicense:
    def __init__(
        self,
        key: str,
        expiry_datetime: dt.datetime | None,
        valid: bool,
        max_nb_buses: int | None,
        machine_fingerprint: str,
    ):
        self.key = key
        self.expiry_datetime = expiry_datetime
        self.valid = valid
        self.max_nb_buses = max_nb_buses
        self.machine_fingerprint = machine_fingerprint


def test_license():
    key = "My Wonderful Key"
    expiry_datetime = dt.datetime.now(tz=dt.timezone.utc)
    valid = True
    max_nb_buses = 150
    machine_fingerprint = "hashed-fingerprint"
    lic = License(
        cy_license=FakeCyLicense(
            key=key,
            expiry_datetime=expiry_datetime.isoformat(),
            valid=valid,
            max_nb_buses=max_nb_buses,
            machine_fingerprint=machine_fingerprint,
        )
    )
    assert lic.key == key
    assert lic.expiry_datetime == expiry_datetime
    assert lic.valid == valid
    assert lic.max_nb_buses == max_nb_buses
    assert lic.machine_fingerprint == machine_fingerprint

    # No expiry datetime
    lic = License(
        cy_license=FakeCyLicense(
            key=key,
            expiry_datetime=None,
            valid=valid,
            max_nb_buses=max_nb_buses,
            machine_fingerprint=machine_fingerprint,
        )
    )
    assert lic.expiry_datetime is None

    # Error expiry datetime
    lic = License(
        cy_license=FakeCyLicense(
            key=key,
            expiry_datetime="toto",
            valid=valid,
            max_nb_buses=max_nb_buses,
            machine_fingerprint=machine_fingerprint,
        )
    )
    assert lic.expiry_datetime is None

    # Static methods
    assert isinstance(License.get_hostname(), str)
    assert isinstance(License.get_username(), str)


def test_activate_license(monkeypatch):
    def _fake_cy_activate_license(key: str, cacert_filepath: str, cache_folderpath: str):
        assert key == "toto"
        assert cacert_filepath == certifi.where()
        assert cache_folderpath == user_cache_dir()
        raise RuntimeError("0 Fake Error")

    with monkeypatch.context() as m:
        m.setattr("roseau.load_flow.license.cy_activate_license", _fake_cy_activate_license)
        with pytest.raises(RoseauLoadFlowException) as e:
            activate_license(key="toto")
        assert e.value.msg == "The license cannot be activated. The detailed error message is 'Fake Error'."
        assert e.value.code == RoseauLoadFlowExceptionCode.LICENSE_ERROR


def test_deactivate_license(monkeypatch):
    called = False

    def _fake_cy_deactivate_license():
        nonlocal called
        called = True

    with monkeypatch.context() as m:
        m.setattr("roseau.load_flow.license.cy_deactivate_license", _fake_cy_deactivate_license)
        deactivate_license()

    assert called
