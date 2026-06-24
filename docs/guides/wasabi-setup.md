# Wasabi Setup

fgbackup ships configs to a [Wasabi](https://wasabi.com/) bucket via restic's S3
backend. Wasabi is S3-compatible, flat-rate, and has no egress fees, which suits
small, frequently-written backup repositories. This guide covers creating the
bucket and access keys, and the one storage policy that shapes the schedule.

## 1. Create a bucket

1. Sign in to the [Wasabi console](https://console.wasabisys.com/).
2. Create a **bucket** in the region closest to you. Note the region — it sets
   the S3 endpoint.
3. Leave bucket versioning **off**; restic does its own versioning via snapshots.

| Wasabi region | S3 endpoint |
|---------------|-------------|
| us-east-1 | `s3.us-east-1.wasabisys.com` |
| us-east-2 | `s3.us-east-2.wasabisys.com` |
| us-west-1 | `s3.us-west-1.wasabisys.com` |
| us-central-1 | `s3.us-central-1.wasabisys.com` |
| eu-central-1 | `s3.eu-central-1.wasabisys.com` |
| eu-west-1 | `s3.eu-west-1.wasabisys.com` |
| ap-northeast-1 | `s3.ap-northeast-1.wasabisys.com` |

The full endpoint list is in the
[Wasabi docs](https://docs.wasabi.com/docs/what-are-the-service-urls-for-wasabis-different-storage-regions).

## 2. Create access keys

1. In the console, go to **Access Keys** and **Create New Access Key**.
2. A root key works, but a dedicated sub-user limited to this one bucket is
   safer.
3. Record both values:
   - access key → `AWS_ACCESS_KEY_ID`
   - secret key → `AWS_SECRET_ACCESS_KEY`

## 3. Point restic at the bucket

Set `RESTIC_REPOSITORY` to the `s3:` URL built from the endpoint and bucket:

```
RESTIC_REPOSITORY=s3:https://s3.<region>.wasabisys.com/<bucket-name>
```

Example for a `us-east-1` bucket named `ckt-fortigate-backups`:

```
RESTIC_REPOSITORY=s3:https://s3.us-east-1.wasabisys.com/ckt-fortigate-backups
```

You do **not** need to run `restic init` by hand — fgbackup initialises the
repository on the first `backup` if it doesn't exist yet.

## The 90-day minimum storage charge

Wasabi bills any stored object for a **minimum of 90 days**, even if you delete
it sooner. restic's `prune` is what actually deletes pack files, so pruning
aggressively would delete data Wasabi still charges you for.

fgbackup handles this by **splitting retention from deletion**:

- `forget` runs daily and only drops snapshot *references* (free).
- `prune` runs **quarterly** so the pack files it deletes have already aged past
  the 90-day window.

See [Scheduling](scheduling.md) for the exact cadence and
[restic Storage](restic-storage.md) for how snapshots and pruning interact.

## Verifying

After your first backup, confirm the repository is reachable:

```bash
docker compose -f release/compose.yaml run --rm fgbackup restic snapshots
docker compose -f release/compose.yaml run --rm fgbackup restic check
```
