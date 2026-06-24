"""CLI entry point.

Subcommands map onto the scheduled steps:
  poll    pull every device config into the staging dir
  backup  restic snapshot of the staging dir (inits repo if needed)
  forget  apply restic retention policy (cheap, reference-only)
  prune   delete/repack unreferenced data, then verify
  check   verify repository integrity
  run     convenience: poll then backup
"""

from __future__ import annotations

import argparse
import sys

from .config import Settings
from .forticloud import FortiCloudClient, FortiCloudError
from .logging import configure, get_logger
from .poller import poll
from .store import ResticStore, StoreError

log = get_logger("fgbackup.cli")


def _cmd_poll(settings: Settings) -> int:
    """Pull configs. Returns 0 unless authentication/enumeration fails fatally."""
    try:
        with FortiCloudClient(settings) as client:
            summary = poll(settings, client)
    except FortiCloudError as e:
        log.error("poll aborted", extra={"fields": {"error": str(e)}})
        return 1
    # Partial device failures are logged but must not block backing up the
    # devices that did succeed, so this is non-fatal.
    if summary.failed:
        log.warning("poll finished with device failures", extra={"fields": {
            "failed": len(summary.failed)}})
    return 0


def _cmd_backup(settings: Settings) -> int:
    ResticStore(settings).backup()
    return 0


def _cmd_forget(settings: Settings) -> int:
    ResticStore(settings).forget()
    return 0


def _cmd_prune(settings: Settings) -> int:
    ResticStore(settings).prune()
    return 0


def _cmd_check(settings: Settings) -> int:
    ResticStore(settings).check()
    return 0


def _cmd_run(settings: Settings) -> int:
    rc = _cmd_poll(settings)
    if rc != 0:
        return rc
    return _cmd_backup(settings)


COMMANDS = {
    "poll": _cmd_poll,
    "backup": _cmd_backup,
    "forget": _cmd_forget,
    "prune": _cmd_prune,
    "check": _cmd_check,
    "run": _cmd_run,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fgbackup", description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS), help="action to perform")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure()
    args = build_parser().parse_args(argv)
    settings = Settings()  # validates required env up front
    try:
        return COMMANDS[args.command](settings)
    except StoreError as e:
        log.error("restic command failed", extra={"fields": {"error": str(e)}})
        return 1


if __name__ == "__main__":
    sys.exit(main())
