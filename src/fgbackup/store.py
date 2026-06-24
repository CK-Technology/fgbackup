"""restic wrapper.

restic reads its repository, password and S3 credentials from the process
environment (``RESTIC_REPOSITORY``, ``RESTIC_PASSWORD``,
``AWS_ACCESS_KEY_ID``/``AWS_SECRET_ACCESS_KEY``), so this module only builds
argument lists and shells out. Argument construction is kept in pure functions
so it can be unit-tested without invoking restic.

Retention split (Wasabi 90-day minimum-storage aware):
  - ``backup`` + ``forget`` run often; ``forget`` only drops snapshot
    references and costs nothing in storage.
  - ``prune`` actually deletes/repacks pack files and is scheduled rarely
    (quarterly) so deleted packs have aged past Wasabi's 90-day minimum.
"""

from __future__ import annotations

import os
import subprocess

from .config import Settings
from .logging import get_logger

log = get_logger("fgbackup.store")

RESTIC_BIN = "restic"
BACKUP_TAG = "fgbackup"


class StoreError(Exception):
    """A restic invocation exited non-zero."""


def backup_args(staging_dir: str) -> list[str]:
    return ["backup", staging_dir, "--tag", BACKUP_TAG, "--host", "fgbackup"]


def forget_args(settings: Settings) -> list[str]:
    return [
        "forget",
        "--tag",
        BACKUP_TAG,
        "--keep-daily",
        str(settings.keep_daily),
        "--keep-weekly",
        str(settings.keep_weekly),
        "--keep-monthly",
        str(settings.keep_monthly),
    ]


def prune_args() -> list[str]:
    return ["prune"]


def check_args() -> list[str]:
    return ["check"]


class ResticStore:
    """High-level restic operations over the configured repository."""

    def __init__(self, settings: Settings, env: dict[str, str] | None = None) -> None:
        self._s = settings
        self._env = env if env is not None else dict(os.environ)

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        cmd = [RESTIC_BIN, *args]
        log.info("running restic", extra={"fields": {"args": args}})
        try:
            return subprocess.run(cmd, env=self._env, check=True)
        except subprocess.CalledProcessError as e:
            raise StoreError(f"restic {args[0]} exited {e.returncode}") from e

    def ensure_repo(self) -> None:
        """Initialise the repository if it does not already exist."""
        probe = subprocess.run(
            [RESTIC_BIN, "cat", "config"],
            env=self._env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if probe.returncode != 0:
            log.info("initialising restic repository")
            self._run(["init"])

    def backup(self) -> None:
        self.ensure_repo()
        self._run(backup_args(self._s.staging_dir))

    def forget(self) -> None:
        self._run(forget_args(self._s))

    def prune(self) -> None:
        self._run(prune_args())

    def check(self) -> None:
        self._run(check_args())
