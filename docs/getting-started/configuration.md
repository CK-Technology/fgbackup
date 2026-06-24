# Configuration

All configuration is via environment variables, loaded from `release/.env` by
Docker Compose. A template lives at
[`release/.env.example`](../../release/.env.example).

`FGB_*` variables configure the poller; the `RESTIC_*` and `AWS_*` variables are
read directly by restic and its S3 backend.

## FortiCloud

| Variable | Default | Description |
|----------|---------|-------------|
| `FGB_FORTICLOUD_API_ID` | — | IAM API user id (`apiId` from the credentials ZIP) |
| `FGB_FORTICLOUD_API_PASSWORD` | — | IAM API user password |
| `FGB_FORTICLOUD_REGION` | `global` | Account API region: `global`, `us`, `eu`, `jp` |

The region selects the API host:

| Region | Host |
|--------|------|
| `global` | `api.fortigate.forticloud.com` |
| `us` | `usapi.fortigate.forticloud.com` |
| `eu` | `euapi.fortigate.forticloud.com` |
| `jp` | `jpapi.fortigate.forticloud.com` |

## restic / Wasabi

| Variable | Default | Description |
|----------|---------|-------------|
| `RESTIC_REPOSITORY` | — | `s3:https://s3.<region>.wasabisys.com/<bucket>` |
| `RESTIC_PASSWORD` | — | Repository encryption passphrase (**keep it safe**) |
| `AWS_ACCESS_KEY_ID` | — | Wasabi access key |
| `AWS_SECRET_ACCESS_KEY` | — | Wasabi secret key |

## Retention

Applied by `fgbackup forget` (see [Scheduling](../guides/scheduling.md)).

| Variable | Default | Description |
|----------|---------|-------------|
| `FGB_KEEP_DAILY` | `14` | Daily snapshots to keep |
| `FGB_KEEP_WEEKLY` | `8` | Weekly snapshots to keep |
| `FGB_KEEP_MONTHLY` | `12` | Monthly snapshots to keep |

## HTTP behaviour

| Variable | Default | Description |
|----------|---------|-------------|
| `FGB_HTTP_TIMEOUT` | `60.0` | Per-request timeout (seconds) |
| `FGB_MAX_RETRIES` | `5` | Retries on 429/5xx before giving up |

## Misc

| Variable | Default | Description |
|----------|---------|-------------|
| `FGB_STAGING_DIR` | `/staging` | Where pulled configs are written |
| `TZ` | `UTC` | Container timezone (affects the schedule) |

## Secrets handling

`.env` and `*.env` are gitignored (only `*.env.example` is tracked). Keep the
file root-readable only. Losing `RESTIC_PASSWORD` makes the repository
unrecoverable — store it in a password manager separate from the backups. See
[SECURITY.md](../../SECURITY.md).
