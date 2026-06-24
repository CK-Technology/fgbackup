# Quickstart

Get fgbackup pulling FortiGate configs into Wasabi.

## Prerequisites

- Docker and Docker Compose on the host.
- A **FortiCloud IAM API user** with FortiGate Cloud access
  (see [FortiCloud Setup](../guides/forticloud-setup.md)).
- A **Wasabi bucket** and access keys
  (see [Wasabi Setup](../guides/wasabi-setup.md)).
- The FortiCloud *management* feature enabled on each FortiGate, or that device
  is logged and skipped.

## 1. Clone and configure

```bash
git clone https://github.com/CK-Technology/fgbackup.git
cd fgbackup/release
cp .env.example .env
```

Edit `.env` and fill in:

- `FGB_FORTICLOUD_API_ID` / `FGB_FORTICLOUD_API_PASSWORD` — IAM API user
- `FGB_FORTICLOUD_REGION` — `global` / `us` / `eu` / `jp`
- `RESTIC_REPOSITORY` — `s3:https://s3.<region>.wasabisys.com/<bucket>`
- `RESTIC_PASSWORD` — a strong passphrase (**losing it loses the backups**)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — Wasabi keys

## 2. Test with a single backup

Before scheduling, run one backup of every device immediately:

```bash
docker compose -f compose.yaml run --rm fgbackup fgbackup run
```

This authenticates, lists every device in the account, pulls what it can, and
snapshots to Wasabi. Per-device failures are logged and skipped; the run still
backs up everything that succeeded.

Inspect what landed:

```bash
docker compose -f compose.yaml run --rm fgbackup restic snapshots
docker compose -f compose.yaml run --rm fgbackup restic check
```

## 3. Start the scheduled stack

```bash
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml logs -f
```

The container now runs on the built-in schedule (see
[Scheduling](../guides/scheduling.md)).

## Next steps

- [Configuration](configuration.md) — every setting
- [restic Storage](../guides/restic-storage.md) — how to restore a config
- [Docker Deployment](docker.md) — image details and the Compose stack
