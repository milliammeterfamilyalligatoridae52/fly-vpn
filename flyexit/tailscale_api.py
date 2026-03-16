"""Tailscale Admin API client.

Wraps the Tailscale v2 REST API with typed methods for ACL management,
auth-key creation, and device lifecycle.

Used only with Tailscale SaaS — Headscale has its own API surface.
"""

from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

API_BASE = "https://api.tailscale.com/api/v2"
TAG = "tag:ephemeral-vpn"
TAG_OWNER = "autogroup:owner"
_TIMEOUT = 15


class TailscaleAPIClient:
    """Thin wrapper around the Tailscale Admin API."""

    def __init__(self, api_key: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

    def get_acl(self) -> tuple[dict, str]:
        """Fetch the current ACL policy and its ETag.

        Raises :class:`httpx.HTTPStatusError` on non-200 responses.
        """
        resp = httpx.get(
            f"{API_BASE}/tailnet/-/acl",
            headers=self._headers,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json(), resp.headers.get("etag", "")

    def set_acl(self, acl: dict, etag: str = "") -> bool:
        """Write the ACL policy back (ETag for optimistic concurrency)."""
        headers = {**self._headers}
        if etag:
            headers["If-Match"] = etag
        resp = httpx.post(
            f"{API_BASE}/tailnet/-/acl",
            headers=headers,
            json=acl,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            log.error(
                "Failed to update ACL (HTTP %d): %s",
                resp.status_code,
                resp.text,
            )
            return False
        return True

    def create_auth_key(
        self,
        *,
        tag: str = TAG,
        expiry_seconds: int = 2_592_000,
    ) -> str:
        """Generate a single-use, ephemeral, pre-authorized auth key.

        The key is tagged with *tag* and expires after *expiry_seconds*
        (default 30 days).  The key is single-use, so the long expiry
        carries no security risk — it is consumed on first registration.

        Returns the key string (``tskey-auth-…``).
        Raises :class:`httpx.HTTPStatusError` on API failure.
        """
        resp = httpx.post(
            f"{API_BASE}/tailnet/-/keys",
            headers=self._headers,
            json={
                "capabilities": {
                    "devices": {
                        "create": {
                            "reusable": False,
                            "ephemeral": True,
                            "preauthorized": True,
                            "tags": [tag],
                        },
                    },
                },
                "expirySeconds": expiry_seconds,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        key: str = resp.json()["key"]
        return key

    def delete_device(self, device_id: str) -> bool:
        """Remove a device from the tailnet by its node ID."""
        try:
            resp = httpx.delete(
                f"{API_BASE}/device/{device_id}",
                headers=self._headers,
                timeout=_TIMEOUT,
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
