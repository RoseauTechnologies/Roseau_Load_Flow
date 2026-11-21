import datetime as dt

import certifi
import pytest
from platformdirs import user_cache_dir

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode
from roseau.load_flow.license import PUBLIC_LICENSE_KEY, License, activate_license, deactivate_license


class FakeCyLicense:
    def __init__(
        self,
        key: str,
        expiry_datetime: dt.datetime | None,
        valid: bool,
        max_nb_buses: int | None,
        machine_fingerprint: str,
        offline: bool = False,
    ):
        self.key = key
        self.expiry_datetime = expiry_datetime
        self.valid = valid
        self.max_nb_buses = max_nb_buses
        self.machine_fingerprint = machine_fingerprint
        self.offline = offline


def test_license():
    key = "My Wonderful Key"
    expiry_datetime = dt.datetime.now(tz=dt.UTC)
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
    assert lic.offline is False

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


def test_activate_license_trial(monkeypatch, recwarn):
    activated_keys = []

    def _fake_cy_activate_license(key: str, cacert_filepath: str, cache_folderpath: str):
        activated_keys.append(key)

    assert PUBLIC_LICENSE_KEY.startswith("key/")
    with monkeypatch.context() as m:
        m.setattr("roseau.load_flow.license.cy_activate_license", _fake_cy_activate_license)

        # Without any key: the trial license is used, silently
        m.delenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", raising=False)
        activate_license()
        assert activated_keys == [PUBLIC_LICENSE_KEY]

        # An empty environment variable is ignored as well
        m.setenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", "")
        activate_license()
        assert activated_keys[-1] == PUBLIC_LICENSE_KEY

        # With the environment variable: no trial license
        m.setenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", "my-key")
        activate_license()
        assert activated_keys[-1] == "my-key"

        # With an explicit key: no trial license
        activate_license("other-key")
        assert activated_keys[-1] == "other-key"
        assert not recwarn.list

        # The former public key, explicit or in the environment variable, is replaced by the trial license
        old_key = "A8C6DA-9405FB-E74FB9-C71C3C-207661-V3"
        with pytest.warns(FutureWarning, match=r"The public license key used is no longer valid"):
            activate_license(old_key)
        assert activated_keys[-1] == PUBLIC_LICENSE_KEY
        m.setenv("ROSEAU_LOAD_FLOW_LICENSE_KEY", old_key)
        with pytest.warns(FutureWarning, match=r"The public license key used is no longer valid"):
            activate_license()
        assert activated_keys[-1] == PUBLIC_LICENSE_KEY
    deactivate_license()
