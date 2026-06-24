# CLI Reference

The `fgbackup` command is the single entry point. Each subcommand maps onto one
step of the backup lifecycle; the scheduler ([Scheduling](../guides/scheduling.md))
just invokes them on a timer.

```
fgbackup <command>
```

Configuration comes entirely from the environment (see
[Environment Variables](environment.md)); there are no other flags.

## Commands

| Command | Action |
|---------|--------|
| `poll` | Authenticate, list every device, pull/validate each config into the staging dir |
| `backup` | restic snapshot of the staging dir (initialises the repo if needed) |
| `forget` | Apply the restic retention policy (cheap, reference-only) |
| `prune` | Delete/repack unreferenced data in the repo |
| `check` | Verify repository integrity |
| `run` | Convenience: `poll` then `backup` |

### `poll`

Pulls a config for every device in the FortiCloud account into
`FGB_STAGING_DIR`. Each device is independent:

- **Success** — a validated `.conf` is written as `<name>_<serial>.conf`.
- **Management disabled** — the device is logged and **skipped** (fgbackup never
  enables management itself).
- **Other failure** (HTTP error, invalid/empty body) — logged and counted as a
  failure, but the run continues.

Exit code is `0` even with per-device skips/failures; it's only non-zero if
authentication or device enumeration fails fatally. A `poll complete` summary
line reports `total / succeeded / skipped / failed`.

### `backup`

Runs `restic backup` on the staging dir, tagged `fgbackup`. Calls
`ensure_repo()` first, which probes the repository and runs `restic init` if it
doesn't exist — so the very first backup bootstraps the repo automatically.

### `forget`

Runs `restic forget` with `--keep-daily/--keep-weekly/--keep-monthly` from the
`FGB_KEEP_*` settings, scoped to the `fgbackup` tag. Only removes snapshot
references; reclaims no storage on its own.

### `prune`

Runs `restic prune` to delete and repack data no longer referenced by any
snapshot. This is the step that actually frees space, so it's scheduled
quarterly to respect Wasabi's 90-day minimum storage (see
[Wasabi Setup](../guides/wasabi-setup.md)).

### `check`

Runs `restic check` to verify repository structure and metadata. Scheduled right
after the quarterly `prune`.

### `run`

`poll` followed by `backup`. If `poll` fails fatally, `backup` is skipped. This
is the hourly scheduled command.

## Running in the container

The image's default command is the scheduler, but any subcommand can be invoked
directly:

```bash
# One-off poll + snapshot of all devices
docker compose -f release/compose.yaml run --rm fgbackup fgbackup run

# Individual steps
docker compose -f release/compose.yaml run --rm fgbackup fgbackup poll
docker compose -f release/compose.yaml run --rm fgbackup fgbackup forget
```

restic itself is on the image's PATH, so ad-hoc repository operations work too:

```bash
docker compose -f release/compose.yaml run --rm fgbackup restic snapshots
docker compose -f release/compose.yaml run --rm fgbackup restic check
```
