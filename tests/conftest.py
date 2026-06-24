"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from fgbackup.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        forticloud_api_id="api-id",
        forticloud_api_password="api-pw",
        forticloud_region="global",
        staging_dir=str(tmp_path / "staging"),
        max_retries=2,
        http_timeout=5.0,
    )
