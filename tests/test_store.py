"""Tests for restic argument construction and run wiring."""

from __future__ import annotations

import subprocess

import pytest

from fgbackup.store import (
    BACKUP_TAG,
    RESTIC_BIN,
    ResticStore,
    StoreError,
    backup_args,
    check_args,
    forget_args,
    prune_args,
)


def test_backup_args_includes_staging_and_tag():
    args = backup_args("/staging")
    assert args[:2] == ["backup", "/staging"]
    assert "--tag" in args and BACKUP_TAG in args


def test_forget_args_uses_retention_settings(settings):
    args = forget_args(settings)
    assert "--keep-daily" in args
    i = args.index("--keep-daily")
    assert args[i + 1] == str(settings.keep_daily)
    assert "--keep-weekly" in args
    assert "--keep-monthly" in args


def test_prune_and_check_args():
    assert prune_args() == ["prune"]
    assert check_args() == ["check"]


def test_run_invokes_restic_with_env(settings, monkeypatch):
    captured = {}

    def fake_run(cmd, env=None, check=False, **kw):
        captured["cmd"] = cmd
        captured["env"] = env
        captured["check"] = check
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    store = ResticStore(settings, env={"RESTIC_REPOSITORY": "s3:test"})
    store.forget()

    assert captured["cmd"][0] == RESTIC_BIN
    assert captured["cmd"][1] == "forget"
    assert captured["check"] is True
    assert captured["env"] == {"RESTIC_REPOSITORY": "s3:test"}


def test_backup_inits_repo_when_missing(settings, monkeypatch):
    calls = []

    def fake_run(cmd, env=None, check=False, **kw):
        calls.append(cmd)
        # Simulate "repo does not exist" for the `cat config` probe.
        if cmd[1:] == ["cat", "config"]:
            return subprocess.CompletedProcess(cmd, 1)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    store = ResticStore(settings, env={})
    store.backup()

    assert ["cat", "config"] == calls[0][1:]
    assert ["init"] == calls[1][1:]
    assert calls[2][1] == "backup"


def test_run_raises_store_error_on_failure(settings, monkeypatch):
    def fake_run(cmd, env=None, check=False, **kw):
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    store = ResticStore(settings, env={})
    with pytest.raises(StoreError, match="exited 2"):
        store.forget()


def test_backup_skips_init_when_repo_exists(settings, monkeypatch):
    calls = []

    def fake_run(cmd, env=None, check=False, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)  # probe succeeds

    monkeypatch.setattr(subprocess, "run", fake_run)
    store = ResticStore(settings, env={})
    store.backup()

    assert ["cat", "config"] == calls[0][1:]
    assert calls[1][1] == "backup"
    assert not any(c[1:] == ["init"] for c in calls)
