<h1 align="center">fgbackup</h1>

<p align="center">
  <strong>Automated FortiGate config backups from FortiCloud to Wasabi, encrypted and versioned with restic</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
  <a href="https://www.fortinet.com/products/fortigate"><img src="https://img.shields.io/badge/FortiGate-EE3124?style=for-the-badge&logo=fortinet&logoColor=white" alt="FortiGate"/></a>
  <a href="https://wasabi.com/"><img src="https://img.shields.io/badge/Wasabi-01CD3E?style=for-the-badge&logo=wasabi&logoColor=white" alt="Wasabi"/></a>
  <a href="https://restic.net/"><img src="https://img.shields.io/badge/restic-0B7FAB?style=for-the-badge&logo=restic&logoColor=white" alt="restic"/></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Backups-Automated-success?style=flat-square" alt="Automated"/>
  <img src="https://img.shields.io/badge/✓_FortiCloud_API-purple?style=flat-square" alt="FortiCloud API"/>
  <img src="https://img.shields.io/badge/✓_Encrypted-purple?style=flat-square" alt="Encrypted"/>
  <img src="https://img.shields.io/badge/✓_Deduplicated-purple?style=flat-square" alt="Deduplicated"/>
  <img src="https://img.shields.io/badge/✓_Versioned-purple?style=flat-square" alt="Versioned"/>
  <img src="https://img.shields.io/badge/✓_Scheduled-purple?style=flat-square" alt="Scheduled"/>
</p>

---

> ⚠️ **Early development.** The poller, restic storage layer, and containerized
> scheduler are implemented and tested. Validate against your own FortiCloud
> account and a scratch Wasabi bucket before relying on it.

---

## Overview

**fgbackup** backs up the configuration of every FortiGate registered in a
FortiCloud account into a [Wasabi](https://wasabi.com/) S3 bucket. It runs as a
single Docker container on a schedule, pulling configs through the FortiGate
Cloud API and storing them with [restic](https://restic.net/) for encrypted,
deduplicated, versioned backups.

```
FortiCloud API  ──poll──▶  /staging/*.conf  ──restic──▶  Wasabi bucket
   (OAuth)                 (one file/device)             (encrypted, versioned)
```

The only custom code is the poller; restic owns encryption, dedup, versioning,
retention, and integrity verification.

## Features

- **FortiCloud-native** — enumerates and backs up every FortiGate in the account
  via the FortiGate Cloud API; no per-device config, no inbound firewall access.
- **Encrypted & deduplicated** — restic encrypts client-side and dedupes the
  highly-repetitive `.conf` files down to almost nothing.
- **Versioned** — every run is a snapshot; restic retention provides rotation.
- **Wasabi-aware** — prune is scheduled to respect Wasabi's 90-day minimum
  storage duration, avoiding "Timed Deleted Storage" charges.
- **Resilient** — token refresh, 429/5xx backoff with jitter, and per-device
  partial-failure handling (one bad device never aborts the run).
- **Validated** — pulled configs are checked before they count as a backup,
  fixing the classic "archived an error body" failure mode.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.13 |
| **HTTP client** | httpx |
| **Config / validation** | pydantic, pydantic-settings |
| **Source** | FortiCloud API (FortiGate Cloud) |
| **Storage** | restic → Wasabi S3 |
| **Scheduler** | supercronic |
| **Containerization** | Docker & Docker Compose |
| **Tests / Lint** | pytest, ruff |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/CK-Technology/fgbackup.git
cd fgbackup/release

# Copy environment template and fill in credentials
cp .env.example .env
# edit .env: FortiCloud API user, RESTIC_REPOSITORY, RESTIC_PASSWORD, Wasabi keys

# Build and start the scheduled stack
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml logs -f
```

Run a one-off backup of every device immediately:

```bash
docker compose -f release/compose.yaml run --rm fgbackup fgbackup run
```

See [`docs/`](docs/README.md) for the full setup walkthrough.

## Project Structure

```
fgbackup/
├── src/fgbackup/
│   ├── config.py        # env-driven settings
│   ├── logging.py       # JSON-line structured logs
│   ├── forticloud.py    # OAuth, device list, gzipped config pull
│   ├── poller.py        # orchestration: pull → validate → stage
│   ├── store.py         # restic wrapper (backup/forget/prune/check)
│   └── __main__.py      # CLI dispatch
├── tests/               # pytest suite
├── release/
│   ├── Dockerfile       # python:3.13-slim + restic + supercronic
│   ├── compose.yaml     # single service, env_file, named volumes
│   ├── crontab          # supercronic schedule
│   └── .env.example     # documented configuration
└── docs/                # documentation
```

## Configuration

All configuration is via environment variables (see
[`release/.env.example`](release/.env.example) and
[docs/reference/environment.md](docs/reference/environment.md)).

| Variable | Description | Default |
|----------|-------------|---------|
| `FGB_FORTICLOUD_API_ID` | FortiCloud IAM API user id | - |
| `FGB_FORTICLOUD_API_PASSWORD` | FortiCloud IAM API user password | - |
| `FGB_FORTICLOUD_REGION` | `global` / `us` / `eu` / `jp` | `global` |
| `RESTIC_REPOSITORY` | `s3:https://s3.<region>.wasabisys.com/<bucket>` | - |
| `RESTIC_PASSWORD` | Repository encryption passphrase | - |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Wasabi access keys | - |
| `FGB_KEEP_DAILY` / `FGB_KEEP_WEEKLY` / `FGB_KEEP_MONTHLY` | Retention policy | 14 / 8 / 12 |

## Documentation

Full documentation lives in [`docs/`](docs/README.md), including FortiCloud and
Wasabi setup, the restic storage model, scheduling, the CLI reference, and
internals.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, test/lint steps, and
code conventions.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and secrets handling.

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built for MSPs who'd rather not lose a firewall config
</p>
