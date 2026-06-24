"""FortiCloud API client: OAuth, device enumeration, config backup pull.

Flow (see plan / research):
  1. POST password grant to the Fortinet IAM OAuth endpoint -> access_token.
  2. GET /devices to enumerate FortiGates by serial number.
  3. GET /fgt/<SN>/api/v2/monitor/system/config/backup?scope=global per device.
     FortiOS 7.0+ returns the config gzipped, so responses are gunzipped here.

Resilience: token expiry is tracked and refreshed proactively; refresh tokens
are single-use, so any refresh failure falls back to a fresh password grant.
Transient 429/5xx responses are retried with exponential backoff + jitter,
honouring a ``Retry-After`` header when present.
"""

from __future__ import annotations

import gzip
import random
import time
from dataclasses import dataclass

import httpx

from .config import OAUTH_CLIENT_ID, OAUTH_TOKEN_URL, Settings
from .logging import get_logger

log = get_logger("fgbackup.forticloud")

# Gzip magic bytes; FortiOS 7.0+ returns the backup gzip-compressed.
_GZIP_MAGIC = b"\x1f\x8b"


class FortiCloudError(Exception):
    """Base error for FortiCloud operations."""


class AuthError(FortiCloudError):
    """Authentication / token acquisition failed."""


class ManagementDisabledError(FortiCloudError):
    """Device backup needs the FortiCloud 'management' feature enabled.

    Raised so the poller can log-and-skip the device without mutating cloud
    state (per the locked design decision).
    """


class BackupError(FortiCloudError):
    """A device backup failed for a non-recoverable reason."""


@dataclass(frozen=True)
class Device:
    """A FortiGate as reported by the FortiCloud /devices endpoint."""

    name: str
    sn: str


class FortiCloudClient:
    """Thin client over the FortiCloud device-proxy API."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._s = settings
        self._http = client or httpx.Client(timeout=settings.http_timeout)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0

    # -- context manager -------------------------------------------------
    def __enter__(self) -> FortiCloudClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # -- auth ------------------------------------------------------------
    def _token_valid(self) -> bool:
        # 60s safety margin so a token never expires mid-request.
        return self._access_token is not None and time.time() < (self._expires_at - 60)

    def _password_grant(self) -> None:
        body = {
            "username": self._s.forticloud_api_id,
            "password": self._s.forticloud_api_password,
            "client_id": OAUTH_CLIENT_ID,
            "grant_type": "password",
        }
        self._store_token(self._post_token(body, "password"))

    def _refresh_grant(self) -> bool:
        if not self._refresh_token:
            return False
        body = {
            "client_id": OAUTH_CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        try:
            self._store_token(self._post_token(body, "refresh_token"))
            return True
        except AuthError:
            # Refresh tokens are single-use; on any failure re-auth from scratch.
            log.warning("token refresh failed; falling back to password grant")
            return False

    def _post_token(self, body: dict[str, str], kind: str) -> dict:
        try:
            resp = self._http.post(
                OAUTH_TOKEN_URL,
                json=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        except httpx.HTTPError as e:  # network-level failure
            raise AuthError(f"token request ({kind}) failed: {e}") from e
        # The IAM endpoint returns 400 (not 401) on bad credentials/grant.
        if resp.status_code != 200:
            raise AuthError(f"token request ({kind}) returned {resp.status_code}: {resp.text}")
        return resp.json()

    def _store_token(self, data: dict) -> None:
        token = data.get("access_token")
        if not token:
            raise AuthError(f"token response missing access_token: {data}")
        self._access_token = token
        self._refresh_token = data.get("refresh_token")
        # Trust the server's expires_in; default to 1h if absent.
        self._expires_at = time.time() + float(data.get("expires_in", 3600))

    def _ensure_token(self) -> None:
        if self._token_valid():
            return
        if self._refresh_token and self._refresh_grant():
            return
        self._password_grant()

    def _auth_headers(self) -> dict[str, str]:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    # -- request with retry/backoff -------------------------------------
    def _get(self, url: str) -> httpx.Response:
        """GET with retry on 429/5xx; raises on exhausted retries."""
        last_exc: Exception | None = None
        for attempt in range(self._s.max_retries + 1):
            try:
                resp = self._http.get(url, headers=self._auth_headers())
            except httpx.HTTPError as e:
                last_exc = e
                self._sleep_backoff(attempt, None)
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = FortiCloudError(f"{resp.status_code} from {url}")
                if attempt < self._s.max_retries:
                    self._sleep_backoff(attempt, resp.headers.get("Retry-After"))
                    continue
            return resp
        raise FortiCloudError(f"GET {url} failed after retries: {last_exc}")

    @staticmethod
    def _sleep_backoff(attempt: int, retry_after: str | None) -> None:
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 60.0))
                return
            except ValueError:
                pass
        # Exponential backoff with full jitter, capped at 30s.
        delay = min(2.0**attempt, 30.0)
        time.sleep(random.uniform(0, delay))

    # -- API methods -----------------------------------------------------
    def list_devices(self) -> list[Device]:
        """Enumerate FortiGates registered in the FortiCloud account."""
        resp = self._get(f"{self._s.api_base}/devices")
        if resp.status_code != 200:
            raise FortiCloudError(f"/devices returned {resp.status_code}: {resp.text}")
        return _parse_devices(resp.json())

    def backup_device(self, device: Device) -> bytes:
        """Pull a device's global config, returning decompressed bytes.

        Raises ``ManagementDisabledError`` if the device needs management
        enabled, or ``BackupError`` for other failures.
        """
        url = (
            f"{self._s.api_base}/fgt/{device.sn}"
            "/api/v2/monitor/system/config/backup?scope=global"
        )
        resp = self._get(url)
        if resp.status_code != 200:
            self._raise_for_backup(device, resp)
        return _decode_config(resp.content)

    @staticmethod
    def _raise_for_backup(device: Device, resp: httpx.Response) -> None:
        text = resp.text
        if "enable management feature" in text.lower():
            raise ManagementDisabledError(
                f"{device.name} ({device.sn}): management feature disabled"
            )
        raise BackupError(
            f"{device.name} ({device.sn}): backup returned {resp.status_code}: {text}"
        )


def _parse_devices(payload: object) -> list[Device]:
    """Normalise the /devices response into Device objects.

    The endpoint may return a bare list or an object wrapping one; handle both.
    """
    items: list
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in ("devices", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                items = value
                break
        else:
            items = []
    else:
        items = []

    devices: list[Device] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sn = item.get("sn") or item.get("serial") or item.get("serialNumber")
        if not sn:
            continue
        name = item.get("name") or item.get("hostname") or sn
        devices.append(Device(name=str(name).strip(), sn=str(sn).strip()))
    return devices


def _decode_config(content: bytes) -> bytes:
    """Gunzip the backup body if gzip-compressed, else return as-is."""
    if content[:2] == _GZIP_MAGIC:
        return gzip.decompress(content)
    return content
