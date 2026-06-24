# Architecture

fgbackup is a thin Python poller wrapped around restic. The poller's only
responsibility is to land one clean config file per FortiGate in a staging
directory; restic handles everything about durable storage.

```
FortiCloud API  ──poll──▶  /staging/*.conf  ──restic──▶  Wasabi bucket
   (OAuth)                 (one file/device)             (encrypted, versioned)
```

## Components

The package lives under [`src/fgbackup/`](../../src/fgbackup):

| Module | Responsibility |
|--------|----------------|
| `config.py` | `Settings` loaded from env via `pydantic-settings`; region→host resolution |
| `logging.py` | Structured JSON logging and a per-run summary |
| `forticloud.py` | OAuth token cache/refresh, device enumeration, gzipped config pull, backoff |
| `poller.py` | Orchestrates enumerate → pull → validate → atomic write; builds a `RunSummary` |
| `store.py` | restic subprocess wrapper (`backup`/`forget`/`prune`/`check`), repo bootstrap |
| `__main__.py` | argparse CLI dispatch (`poll`/`backup`/`forget`/`prune`/`check`/`run`) |

## Data flow

### 1. Authentication (`forticloud.py`)

An OAuth **password grant** against
`https://customerapiauth.fortinet.com/api/v1/oauth/token/` with
`client_id=fortigatecloud` and the IAM API user's credentials. The
`access_token` (~4h lifetime) is cached in memory. A single-use refresh token is
tried first on expiry, falling back to a fresh password grant if the refresh
fails.

### 2. Enumeration

`GET /forticloudapi/v1/devices` on the regional host returns the device list,
parsed into `Device(name, sn)` records.

### 3. Per-device pull (`forticloud.py`)

```
GET /forticloudapi/v1/fgt/<SN>/api/v2/monitor/system/config/backup?scope=global
```

- FortiOS 7.0+ returns the config **gzipped** (detected via the `\x1f\x8b`
  magic) and decompressed before returning.
- A `Please enable management feature` response raises `ManagementDisabledError`.
- `429`/`5xx` responses are retried with exponential backoff + jitter, honouring
  `Retry-After`, up to `FGB_MAX_RETRIES`.

### 4. Validate + stage (`poller.py`)

Each payload is validated (minimum size, FortiOS config markers) to reject empty
or error bodies — the bug that plagued the original PowerShell script, which
could zip up an error response. Valid configs are written atomically (temp file
then rename) to `<name>_<serial>.conf`. Per-device outcomes are collected into a
`RunSummary` (succeeded / skipped / failed); skips and failures never abort the
run.

### 5. Snapshot (`store.py`)

`fgbackup backup` shells out to `restic backup /staging`, tagged `fgbackup`,
initialising the repository first if it doesn't exist. restic provides
encryption, deduplication, snapshot history and integrity.

## Design decisions

**Stable filenames over timestamped ones.** Writing the same
`<name>_<serial>.conf` each run lets restic's content-defined chunking
deduplicate unchanged configs to near-zero, and snapshot history becomes the
rotation. There is nothing to prune in the staging dir.

**Log-and-skip, never mutate.** A device with management disabled is skipped and
recorded, never auto-enabled. fgbackup only ever *reads* cloud state.

**Partial failure is non-fatal.** Each device is independent. `poll` exits `0`
even with skips/failures so the devices that succeeded still get snapshotted;
only a fatal auth/enumeration error returns non-zero.

**restic owns storage.** The poller carries no crypto, diffing, or retention
logic. This keeps the Python surface small and leans on a mature, well-audited
backup engine. See [restic Storage](../guides/restic-storage.md).

**Retention split for Wasabi.** `forget` (reference-only, free) runs daily while
`prune` (actual deletion) runs quarterly, so deleted packs have aged past
Wasabi's 90-day minimum-storage charge. See [Scheduling](../guides/scheduling.md).

## Deployment shape

A single image bundles the Python poller, the `restic` binary, and the
`supercronic` scheduler, with `tini` as PID 1 for signal handling and zombie
reaping. One container does both the scheduled polling and the restic shipping;
the staging dir and restic cache are named volumes, while the repository itself
lives in Wasabi. See [Docker Deployment](../getting-started/docker.md).
