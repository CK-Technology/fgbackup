# FortiCloud Setup

fgbackup authenticates to FortiCloud as a dedicated **IAM API user** and pulls
each device's config through the FortiGate Cloud device-proxy API. This guide
covers creating that API user and the per-device requirement.

## 1. Create an IAM API user

Use a dedicated API user rather than a human login.

1. Sign in to the [FortiCloud IAM portal](https://support.fortinet.com/) as a
   user with SysAdmin rights.
2. Create a **Permission Profile** that grants **FortiGate Cloud** portal access.
3. Attach the profile to a **user group**.
4. **Add an API user** under that group.
5. Download the credentials ZIP (password-protected). It contains:
   - `apiId` → `FGB_FORTICLOUD_API_ID`
   - `password` → `FGB_FORTICLOUD_API_PASSWORD`

> The permission profile must include FortiGate Cloud access, or the issued
> token will be rejected by the device-proxy API.

## 2. Set the region

Your FortiCloud account lives in a region; set `FGB_FORTICLOUD_REGION` to match:

| Region | Value | API host |
|--------|-------|----------|
| Global | `global` | `api.fortigate.forticloud.com` |
| US | `us` | `usapi.fortigate.forticloud.com` |
| Europe | `eu` | `euapi.fortigate.forticloud.com` |
| Japan | `jp` | `jpapi.fortigate.forticloud.com` |

## 3. Enable management per device

The config-backup call goes through FortiGate Cloud's device proxy, which
requires the **management** feature to be enabled on each FortiGate. Enable it
from the FortiGate Cloud portal for every device you want backed up.

fgbackup will **not** enable management automatically — if a device reports
`Please enable management feature`, it is logged and **skipped** so the tool
never mutates cloud state. Check the logs after the first run and enable
management on any skipped device.

## How authentication works

Behind the scenes the poller performs an OAuth password grant:

```
POST https://customerapiauth.fortinet.com/api/v1/oauth/token/
{
  "username":   "<apiId>",
  "password":   "<password>",
  "client_id":  "fortigatecloud",
  "grant_type": "password"
}
```

The returned `access_token` (valid ~4h) is cached and reused; it is refreshed
via the single-use refresh token, falling back to a fresh password grant if a
refresh fails. Devices are enumerated with `GET /forticloudapi/v1/devices`, and
each backup is pulled from:

```
GET /forticloudapi/v1/fgt/<SN>/api/v2/monitor/system/config/backup?scope=global
```

FortiOS 7.0+ returns the config gzip-compressed; fgbackup decompresses it before
staging.

## Verifying

Run a one-off backup and watch the JSON logs:

```bash
docker compose -f release/compose.yaml run --rm fgbackup fgbackup run
```

You should see one `backed up device` line per reachable FortiGate and a
`poll complete` summary with succeeded / skipped / failed counts.
