"""Orchestration: enumerate devices, pull/validate configs, write to staging.

Writes one stable file per device (``<name>_<sn>.conf``) so restic's dedup and
snapshot history provide rotation -- no per-run timestamped files to prune.
Partial failures never abort the run: each device is independent and the
outcome is collected into a :class:`RunSummary`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .forticloud import (
    BackupError,
    Device,
    FortiCloudClient,
    FortiCloudError,
    ManagementDisabledError,
)
from .logging import get_logger

log = get_logger("fgbackup.poller")

# A valid FortiOS backup starts with a config-version header and is non-trivial.
_MIN_CONFIG_BYTES = 128
_CONFIG_MARKERS = (b"config-version", b"config system")


class ValidationError(FortiCloudError):
    """A pulled config failed validation (empty / too small / not a config)."""


@dataclass
class RunSummary:
    """Outcome of a poll run."""

    total: int = 0
    succeeded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if no device hard-failed (skips are tolerated)."""
        return not self.failed


def sanitize(name: str) -> str:
    """Make a device name safe for use in a filename."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "device"


def validate_config(data: bytes) -> None:
    """Reject empty, truncated, or non-config payloads."""
    if len(data) < _MIN_CONFIG_BYTES:
        raise ValidationError(f"config too small ({len(data)} bytes)")
    head = data[:512].lower()
    if not any(marker in head for marker in _CONFIG_MARKERS):
        raise ValidationError("payload does not look like a FortiOS config")


def _staging_path(settings: Settings, device: Device) -> Path:
    fname = f"{sanitize(device.name)}_{sanitize(device.sn)}.conf"
    return Path(settings.staging_dir) / fname


def poll(settings: Settings, client: FortiCloudClient) -> RunSummary:
    """Back up every device into the staging directory; return a summary."""
    staging = Path(settings.staging_dir)
    staging.mkdir(parents=True, exist_ok=True)

    devices = client.list_devices()
    summary = RunSummary(total=len(devices))
    log.info("listed devices", extra={"fields": {"count": len(devices)}})

    for device in devices:
        label = f"{device.name} ({device.sn})"
        try:
            data = client.backup_device(device)
            validate_config(data)
        except ManagementDisabledError:
            log.warning("skipping device: management disabled", extra={"fields": {"device": label}})
            summary.skipped.append(label)
            continue
        except (BackupError, ValidationError, FortiCloudError) as e:
            log.error("device backup failed", extra={"fields": {"device": label, "error": str(e)}})
            summary.failed.append(label)
            continue

        # Atomic write: temp file then replace, so a snapshot never sees a
        # half-written config if poll and backup overlap.
        dest = _staging_path(settings, device)
        tmp = dest.with_suffix(".conf.tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        log.info("backed up device", extra={"fields": {"device": label, "bytes": len(data)}})
        summary.succeeded.append(label)

    log.info(
        "poll complete",
        extra={
            "fields": {
                "total": summary.total,
                "succeeded": len(summary.succeeded),
                "skipped": len(summary.skipped),
                "failed": len(summary.failed),
            }
        },
    )
    return summary
