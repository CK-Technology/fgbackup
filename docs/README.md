# fgbackup Documentation

Automated FortiGate config backups from FortiCloud to Wasabi, encrypted and
versioned with restic.

```
FortiCloud API  ──poll──▶  /staging/*.conf  ──restic──▶  Wasabi bucket
   (OAuth)                 (one file/device)             (encrypted, versioned)
```

## Getting Started

- [Quickstart](getting-started/quickstart.md) - Get backups running
- [Docker Deployment](getting-started/docker.md) - Image, Compose stack, and the scheduler
- [Configuration](getting-started/configuration.md) - All settings and environment variables

## Guides

- [FortiCloud Setup](guides/forticloud-setup.md) - IAM API user and enabling device management
- [Wasabi Setup](guides/wasabi-setup.md) - Bucket, access keys, and the 90-day minimum storage
- [restic Storage](guides/restic-storage.md) - How configs are stored, snapshots, and restoring
- [Scheduling](guides/scheduling.md) - The supercronic schedule and retention cadence

## Reference

- [CLI Reference](reference/cli.md) - `fgbackup` commands
- [Environment Variables](reference/environment.md) - Full configuration reference

## Internals

- [Architecture](internals/architecture.md) - How the poller and storage fit together

## Quick Links

| Item | Value |
|------|-------|
| OAuth endpoint | `https://customerapiauth.fortinet.com/api/v1/oauth/token/` |
| API host (global) | `api.fortigate.forticloud.com` |
| Staging dir (in container) | `/staging` |
| Image | `ghcr.io/ck-technology/fgbackup:latest` |

Credentials are supplied via environment variables (`release/.env`); see
[Configuration](getting-started/configuration.md).
