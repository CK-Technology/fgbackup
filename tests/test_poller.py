"""Tests for poller orchestration: validation, filenames, partial failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from fgbackup.forticloud import BackupError, Device, ManagementDisabledError
from fgbackup.poller import RunSummary, ValidationError, poll, sanitize, validate_config
from helpers import SAMPLE_CONFIG


class FakeClient:
    """Stand-in FortiCloudClient driven by canned device behaviours."""

    def __init__(self, devices, behaviours):
        self._devices = devices
        self._behaviours = behaviours  # sn -> bytes | Exception

    def list_devices(self):
        return self._devices

    def backup_device(self, device: Device) -> bytes:
        result = self._behaviours[device.sn]
        if isinstance(result, Exception):
            raise result
        return result


def test_validate_config_accepts_real_config():
    validate_config(SAMPLE_CONFIG + b"x" * 200)


def test_validate_config_rejects_empty():
    with pytest.raises(ValidationError):
        validate_config(b"")


def test_validate_config_rejects_non_config():
    with pytest.raises(ValidationError):
        validate_config(b"<html>error</html>" * 20)


def test_sanitize_strips_unsafe_chars():
    assert sanitize("HQ Edge/01") == "HQ_Edge_01"
    assert sanitize("///") == "device"


def test_poll_writes_files_and_summarizes(settings):
    devices = [
        Device("fw1", "FGT001"),
        Device("fw2", "FGT002"),
        Device("fw3", "FGT003"),
    ]
    body = SAMPLE_CONFIG + b"y" * 200
    behaviours = {
        "FGT001": body,
        "FGT002": ManagementDisabledError("disabled"),
        "FGT003": BackupError("boom"),
    }
    summary = poll(settings, FakeClient(devices, behaviours))

    assert isinstance(summary, RunSummary)
    assert summary.total == 3
    assert summary.succeeded == ["fw1 (FGT001)"]
    assert summary.skipped == ["fw2 (FGT002)"]
    assert summary.failed == ["fw3 (FGT003)"]
    assert summary.ok is False  # a hard failure occurred

    staged = Path(settings.staging_dir) / "fw1_FGT001.conf"
    assert staged.read_bytes() == body
    # No temp files left behind.
    assert list(Path(settings.staging_dir).glob("*.tmp")) == []


def test_poll_all_success_is_ok(settings):
    devices = [Device("fw1", "FGT001")]
    behaviours = {"FGT001": SAMPLE_CONFIG + b"z" * 200}
    summary = poll(settings, FakeClient(devices, behaviours))
    assert summary.ok is True
    assert summary.failed == []


def test_poll_invalid_config_counts_as_failure(settings):
    devices = [Device("fw1", "FGT001")]
    behaviours = {"FGT001": b"tiny"}
    summary = poll(settings, FakeClient(devices, behaviours))
    assert summary.failed == ["fw1 (FGT001)"]
    assert not (Path(settings.staging_dir) / "fw1_FGT001.conf").exists()
