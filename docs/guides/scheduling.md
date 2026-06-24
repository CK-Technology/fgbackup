# Scheduling

The container runs [supercronic](https://github.com/aptible/supercronic) as its
default command, executing the `fgbackup` subcommands on a fixed schedule. The
schedule lives in [`release/crontab`](../../release/crontab).

## The default schedule

```cron
# m h dom mon dow  command
0 * * * *     fgbackup run                       # hourly: pull + snapshot
30 2 * * *    fgbackup forget                    # daily: trim snapshot refs
0 3 1 */3 *   fgbackup prune && fgbackup check   # quarterly: delete + verify
```

| Cadence | Command | What it does | Cost |
|---------|---------|--------------|------|
| Hourly | `fgbackup run` | Poll every device, snapshot to Wasabi | Cheap (dedup) |
| Daily 02:30 | `fgbackup forget` | Apply keep policy, drop old references | Free |
| Quarterly 03:00 | `fgbackup prune && fgbackup check` | Delete/repack packs, verify | Egress |

## Why this cadence

The three tiers exist because restic operations have very different costs and
Wasabi charges a **90-day minimum storage** on every object:

- **`run` hourly** — pulling configs and snapshotting is cheap because restic
  deduplicates unchanged configs to near-zero. Frequent snapshots give you fine
  recovery points without bloating the repo.
- **`forget` daily** — applies the retention policy but only removes snapshot
  *references*. It frees nothing in object storage, so it's effectively free to
  run often.
- **`prune` quarterly** — the only step that actually deletes pack files. Spaced
  to once a quarter so the data it removes has already aged past Wasabi's 90-day
  minimum-storage window; pruning sooner would delete data you're still billed
  for. `check` runs right after to verify the repo is consistent.

## Timezone

supercronic evaluates the schedule in the container's timezone. Set `TZ` in
`release/.env` so cron times match local time:

```bash
TZ=America/Chicago
```

With the default `TZ=UTC`, the times above are UTC.

## Changing the schedule

Edit `release/crontab` and rebuild the image (the crontab is copied in at build
time):

```bash
docker compose -f release/compose.yaml up -d --build
```

Validate the crontab syntax without starting the scheduler:

```bash
docker compose -f release/compose.yaml run --rm fgbackup \
  supercronic -test /app/crontab
```

## Running steps manually

Every scheduled step is just a CLI subcommand you can run on demand — see the
[CLI Reference](../reference/cli.md):

```bash
docker compose -f release/compose.yaml run --rm fgbackup fgbackup run
docker compose -f release/compose.yaml run --rm fgbackup fgbackup forget
docker compose -f release/compose.yaml run --rm fgbackup fgbackup prune
```
