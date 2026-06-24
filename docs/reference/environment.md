# Environment Variables

Full reference for every variable fgbackup reads. `FGB_*` variables configure the
poller (via `pydantic-settings`); `RESTIC_*` and `AWS_*` are consumed directly by
restic and its S3 backend. All are supplied through `release/.env`
(`env_file` in Compose). A template lives at
[`release/.env.example`](../../release/.env.example).

## FortiCloud

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FGB_FORTICLOUD_API_ID` | yes | — | IAM API user id (`apiId` from the credentials ZIP) |
| `FGB_FORTICLOUD_API_PASSWORD` | yes | — | IAM API user password |
| `FGB_FORTICLOUD_REGION` | no | `global` | Account API region: `global`, `us`, `eu`, `jp` |

`FGB_FORTICLOUD_REGION` resolves to the device-proxy API host:

| Region | Host |
|--------|------|
| `global` | `api.fortigate.forticloud.com` |
| `us` | `usapi.fortigate.forticloud.com` |
| `eu` | `euapi.fortigate.forticloud.com` |
| `jp` | `jpapi.fortigate.forticloud.com` |

An unrecognised region falls back to the `global` host. See
[FortiCloud Setup](../guides/forticloud-setup.md).

## restic / Wasabi

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RESTIC_REPOSITORY` | yes | — | `s3:https://s3.<region>.wasabisys.com/<bucket>` |
| `RESTIC_PASSWORD` | yes | — | Repository encryption passphrase — **losing it loses the backups** |
| `AWS_ACCESS_KEY_ID` | yes | — | Wasabi access key |
| `AWS_SECRET_ACCESS_KEY` | yes | — | Wasabi secret key |

See [Wasabi Setup](../guides/wasabi-setup.md) and
[restic Storage](../guides/restic-storage.md).

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
| `FGB_STAGING_DIR` | `/staging` | Where pulled configs are written before restic snapshots them |
| `TZ` | `UTC` | Container timezone; affects the supercronic schedule |

## Notes

- The `FGB_` prefix is applied automatically — set `FGB_FORTICLOUD_REGION`, not
  `FORTICLOUD_REGION`.
- `RESTIC_*` and `AWS_*` keep their canonical names so restic and its S3 backend
  read them straight from the process environment; the poller does not rename
  them.
- Unknown variables are ignored, so unrelated entries in `.env` are harmless.
- `.env` and `*.env` are gitignored (only `*.env.example` is tracked). See
  [Secrets handling](../getting-started/configuration.md#secrets-handling) and
  [SECURITY.md](../../SECURITY.md).
