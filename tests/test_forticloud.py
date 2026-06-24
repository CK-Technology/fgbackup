"""Tests for the FortiCloud client: auth, listing, gzip decode, backoff, skip."""

from __future__ import annotations

import httpx
import pytest

from fgbackup.forticloud import (
    AuthError,
    BackupError,
    Device,
    FortiCloudClient,
    ManagementDisabledError,
    _decode_config,
    _parse_devices,
)
from helpers import SAMPLE_CONFIG, gzip_bytes, mock_client


def _token_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "access_token": "tok-123",
            "refresh_token": "refresh-123",
            "expires_in": 14400,
            "token_type": "Bearer",
        },
    )


def test_password_grant_and_list_devices(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token/"):
            return _token_response()
        if request.url.path.endswith("/devices"):
            assert request.headers["Authorization"] == "Bearer tok-123"
            return httpx.Response(200, json=[{"name": "fw1", "sn": "FGT001"}])
        return httpx.Response(404)

    client = FortiCloudClient(settings, client=mock_client(handler))
    devices = client.list_devices()
    assert devices == [Device(name="fw1", sn="FGT001")]


def test_backup_decodes_gzip(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token/"):
            return _token_response()
        if "config/backup" in request.url.path:
            return httpx.Response(200, content=gzip_bytes(SAMPLE_CONFIG))
        return httpx.Response(404)

    client = FortiCloudClient(settings, client=mock_client(handler))
    data = client.backup_device(Device(name="fw1", sn="FGT001"))
    assert data == SAMPLE_CONFIG


def test_backup_management_disabled_raises_skip(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token/"):
            return _token_response()
        return httpx.Response(
            403, json={"error_description": "Please enable management feature."}
        )

    client = FortiCloudClient(settings, client=mock_client(handler))
    with pytest.raises(ManagementDisabledError):
        client.backup_device(Device(name="fw1", sn="FGT001"))


def test_backup_other_error_raises_backuperror(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token/"):
            return _token_response()
        return httpx.Response(404, text="not found")

    client = FortiCloudClient(settings, client=mock_client(handler))
    with pytest.raises(BackupError):
        client.backup_device(Device(name="fw1", sn="FGT001"))


def test_bad_credentials_raise_autherror(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    client = FortiCloudClient(settings, client=mock_client(handler))
    with pytest.raises(AuthError):
        client.list_devices()


def test_retry_on_429_then_success(settings, monkeypatch):
    # Don't actually sleep during backoff.
    monkeypatch.setattr("fgbackup.forticloud.time.sleep", lambda *_: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token/"):
            return _token_response()
        if request.url.path.endswith("/devices"):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"}, text="slow down")
            return httpx.Response(200, json=[{"name": "fw1", "sn": "FGT001"}])
        return httpx.Response(404)

    client = FortiCloudClient(settings, client=mock_client(handler))
    devices = client.list_devices()
    assert calls["n"] == 2
    assert devices[0].sn == "FGT001"


def test_token_refresh_used_when_expired(settings, monkeypatch):
    token_posts = {"password": 0, "refresh": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/token/"):
            body = request.content.decode()
            if "refresh_token" in body and "grant_type" in body and "refresh-123" in body:
                token_posts["refresh"] += 1
            else:
                token_posts["password"] += 1
            return _token_response()
        return httpx.Response(200, json=[])

    client = FortiCloudClient(settings, client=mock_client(handler))
    client.list_devices()  # password grant
    # Force expiry so the next call must refresh.
    client._expires_at = 0.0
    client.list_devices()  # refresh grant
    assert token_posts["password"] == 1
    assert token_posts["refresh"] == 1


def test_parse_devices_wrapped_and_alt_keys():
    payload = {"devices": [{"hostname": "edge", "serial": "FGT9"}]}
    assert _parse_devices(payload) == [Device(name="edge", sn="FGT9")]


def test_decode_config_passthrough_plain():
    assert _decode_config(SAMPLE_CONFIG) == SAMPLE_CONFIG
