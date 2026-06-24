"""Tests for CLI dispatch wiring."""

from __future__ import annotations

import pytest

import fgbackup.__main__ as cli
from fgbackup.forticloud import FortiCloudError
from fgbackup.poller import RunSummary


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("FGB_FORTICLOUD_API_ID", "id")
    monkeypatch.setenv("FGB_FORTICLOUD_API_PASSWORD", "pw")
    monkeypatch.setenv("FGB_STAGING_DIR", str(tmp_path))


def test_run_polls_then_backs_up(monkeypatch):
    order = []

    class FakeClient:
        def __init__(self, settings):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(cli, "FortiCloudClient", FakeClient)
    monkeypatch.setattr(cli, "poll", lambda s, c: (order.append("poll"), RunSummary(total=0))[1])

    class FakeStore:
        def __init__(self, settings):
            pass

        def backup(self):
            order.append("backup")

    monkeypatch.setattr(cli, "ResticStore", FakeStore)

    assert cli.main(["run"]) == 0
    assert order == ["poll", "backup"]


def test_run_aborts_backup_when_poll_fails(monkeypatch):
    order = []

    class FakeClient:
        def __init__(self, settings):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def boom(s, c):
        raise FortiCloudError("auth failed")

    monkeypatch.setattr(cli, "FortiCloudClient", FakeClient)
    monkeypatch.setattr(cli, "poll", boom)

    class FakeStore:
        def __init__(self, settings):
            pass

        def backup(self):
            order.append("backup")

    monkeypatch.setattr(cli, "ResticStore", FakeStore)

    assert cli.main(["run"]) == 1
    assert order == []  # backup never ran


def test_forget_dispatches_to_store(monkeypatch):
    called = []

    class FakeStore:
        def __init__(self, settings):
            pass

        def forget(self):
            called.append("forget")

    monkeypatch.setattr(cli, "ResticStore", FakeStore)
    assert cli.main(["forget"]) == 0
    assert called == ["forget"]


def test_unknown_command_errors():
    with pytest.raises(SystemExit):
        cli.main(["nope"])
