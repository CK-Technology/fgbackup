"""Importable test helpers (kept out of conftest so tests can import them)."""

from __future__ import annotations

import gzip

import httpx

SAMPLE_CONFIG = b"#config-version=FGT60F-7.4.5\nconfig system global\nend\n"


def gzip_bytes(data: bytes) -> bytes:
    return gzip.compress(data)


def mock_client(handler) -> httpx.Client:
    """Build an httpx.Client backed by a MockTransport handler."""
    return httpx.Client(transport=httpx.MockTransport(handler))
