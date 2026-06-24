# restic Storage

fgbackup pulls each FortiGate config into a staging directory; everything about
*how those files are stored* — encryption, deduplication, versioning, integrity
— is delegated to [restic](https://restic.net/). This page explains the layout
and how to restore a config.

## Why restic owns storage

The poller's only job is to land one clean `.conf` per device in `/staging`.
restic then snapshots that directory. This split means fgbackup carries no
crypto, diffing, or rotation logic of its own:

| Concern | Handled by |
|---------|-----------|
| Encryption at rest | restic (repo-wide, AES-256) |
| Deduplication | restic (content-defined chunking) |
| Versioning / history | restic snapshots |
| Retention | restic `forget` + `prune` |
| Integrity | restic `check` |
| Offsite | Wasabi S3 backend |

## Staging layout

The poller writes **one stable filename per device**:

```
/staging/<sanitized-name>_<serial>.conf
```

The filename never changes between runs, so when a device's config is unchanged,
restic deduplicates it to near-zero and the snapshot history *is* the rotation.
There are no timestamped files to clean up. Writes are atomic (temp file then
rename) so an overlapping snapshot never sees a half-written config.

## Snapshots

Each `fgbackup backup` creates one snapshot tagged `fgbackup`, host `fgbackup`:

```bash
docker compose -f release/compose.yaml run --rm fgbackup restic snapshots
```

```
ID        Time                 Host      Tags      Paths
--------------------------------------------------------------
a1b2c3d4  2026-06-24 01:00:03  fgbackup  fgbackup  /staging
...
```

## Restoring a config

List what's in the latest snapshot:

```bash
docker compose -f release/compose.yaml run --rm fgbackup \
  restic ls latest
```

Restore the whole staging tree to a host path:

```bash
docker compose -f release/compose.yaml run --rm \
  -v "$PWD/restore:/restore" fgbackup \
  restic restore latest --target /restore
```

Restore a single device's config by path:

```bash
docker compose -f release/compose.yaml run --rm \
  -v "$PWD/restore:/restore" fgbackup \
  restic restore latest --target /restore \
  --include /staging/Branch-FW_FGT60Fxxxxxxxxxx.conf
```

To pull an **older** version, swap `latest` for a snapshot ID from
`restic snapshots`. The restored `.conf` is a plain FortiOS config you can load
back onto the device via the GUI or `execute restore config`.

## Retention and pruning

`forget` applies the keep policy (see [Configuration](../getting-started/configuration.md)):

| Variable | Default |
|----------|---------|
| `FGB_KEEP_DAILY` | 14 |
| `FGB_KEEP_WEEKLY` | 8 |
| `FGB_KEEP_MONTHLY` | 12 |

`forget` only removes snapshot references and is cheap. `prune` is what actually
reclaims space, and is scheduled quarterly to respect Wasabi's 90-day minimum
storage charge — see [Scheduling](scheduling.md).

## Integrity checks

```bash
docker compose -f release/compose.yaml run --rm fgbackup restic check
```

`check` runs automatically after each quarterly `prune`. For a deeper,
data-reading verification, run `restic check --read-data` manually (it downloads
every pack, so it costs egress time but not Wasabi egress fees).
