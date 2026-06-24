"""Configuration loaded from environment variables.

All settings are prefixed ``FGB_`` except the ``RESTIC_*`` / ``AWS_*`` variables,
which keep their canonical names so restic and its S3 backend pick them up
directly from the process environment.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# FortiCloud regional API hosts for the device-proxy API.
REGION_HOSTS: dict[str, str] = {
    "global": "api.fortigate.forticloud.com",
    "us": "usapi.fortigate.forticloud.com",
    "eu": "euapi.fortigate.forticloud.com",
    "jp": "jpapi.fortigate.forticloud.com",
}

# Fortinet IAM OAuth token endpoint (same for every region).
OAUTH_TOKEN_URL = "https://customerapiauth.fortinet.com/api/v1/oauth/token/"

# client_id used for the FortiGate Cloud device-proxy token.
OAUTH_CLIENT_ID = "fortigatecloud"


class Settings(BaseSettings):
    """Runtime configuration for fgbackup."""

    model_config = SettingsConfigDict(
        env_prefix="FGB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # FortiCloud IAM API user credentials (apiId / password from the IAM ZIP).
    forticloud_api_id: str = Field(..., description="FortiCloud IAM API user id")
    forticloud_api_password: str = Field(..., description="FortiCloud IAM API user password")
    forticloud_region: str = Field("global", description="global|us|eu|jp")

    # Where pulled .conf files are written before restic snapshots them.
    staging_dir: str = Field("/staging", description="Staging directory for configs")

    # HTTP behaviour.
    http_timeout: float = Field(60.0, description="Per-request timeout (seconds)")
    max_retries: int = Field(5, description="Max retries on 429/5xx before giving up")

    # restic retention policy (used by the `forget` command).
    keep_daily: int = Field(14)
    keep_weekly: int = Field(8)
    keep_monthly: int = Field(12)

    @property
    def api_host(self) -> str:
        """Resolve the regional FortiCloud API host, defaulting to global."""
        return REGION_HOSTS.get(self.forticloud_region.lower(), REGION_HOSTS["global"])

    @property
    def api_base(self) -> str:
        """Base URL for the FortiCloud device-proxy API."""
        return f"https://{self.api_host}/forticloudapi/v1"
