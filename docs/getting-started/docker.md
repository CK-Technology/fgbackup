# Docker Deployment

fgbackup ships as a single image containing the Python poller, the `restic`
binary, and the [supercronic](https://github.com/aptible/supercronic) scheduler.
One container does everything: pull configs on a schedule and ship them to
Wasabi.

## Image layout

The [`release/Dockerfile`](../../release/Dockerfile) builds from
`python:3.13-slim` and adds two pinned, checksum-verified binaries:

| Component | Version | Verified by |
|-----------|---------|-------------|
| restic | 0.19.0 | SHA-256 |
| supercronic | v0.2.46 | SHA-1 |

The Python package is installed with `pip install .`. `tini` is the entrypoint
so signals reach supercronic and zombie processes are reaped.

The build context is the **repo root** (the Dockerfile copies `src/`,
`pyproject.toml`, and `release/crontab`), so the Compose file sets
`context: ..`.

## Compose stack

[`release/compose.yaml`](../../release/compose.yaml) defines one service:

```yaml
services:
  fgbackup:
    build:
      context: ..
      dockerfile: release/Dockerfile
    image: ghcr.io/ck-technology/fgbackup:latest
    container_name: fgbackup
    restart: unless-stopped
    env_file:
      - .env
    environment:
      TZ: ${TZ:-UTC}
    volumes:
      - staging:/staging
      - restic-cache:/root/.cache/restic

volumes:
  staging:
  restic-cache:
```

| Volume | Purpose |
|--------|---------|
| `staging` | Pulled `.conf` files between poll and restic backup |
| `restic-cache` | restic's local cache (speeds up repeated operations) |

The restic repository itself lives in Wasabi, not in a volume.

## Build and run

```bash
cd release
cp .env.example .env   # fill in credentials

# Build
docker compose -f compose.yaml build

# Start scheduled
docker compose -f compose.yaml up -d
docker compose -f compose.yaml logs -f
```

## Running individual commands

The image's default command runs the scheduler, but you can invoke any
subcommand directly:

```bash
# One-off backup of all devices
docker compose -f compose.yaml run --rm fgbackup fgbackup run

# restic operations against the configured repo
docker compose -f compose.yaml run --rm fgbackup restic snapshots
docker compose -f compose.yaml run --rm fgbackup restic check
```

See the [CLI Reference](../reference/cli.md) for all subcommands.

## Timezone

The schedule honours the container `TZ` (default `UTC`). Set `TZ` in `.env`
(e.g. `TZ=America/Chicago`) so the cron times match local time.

## Notes

- Only amd64 binaries are pinned in the image today.
- The container runs as root; the restic cache lives under `/root/.cache/restic`.
