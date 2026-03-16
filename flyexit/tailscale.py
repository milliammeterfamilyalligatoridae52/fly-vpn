"""Tailscale exit-node management helpers."""

from __future__ import annotations

import contextlib
import json
import subprocess
from urllib.request import Request, urlopen

from flyexit.constants import TS_CONNECT_TIMEOUT, TS_EXIT_HOSTNAME, TS_POLL_INTERVAL


def disconnect_exit_node() -> None:
    """Tell local Tailscale to stop using the remote exit node."""
    with contextlib.suppress(Exception):
        subprocess.run(
            ["tailscale", "set", "--exit-node="],
            capture_output=True,
            timeout=10,
        )


def connect_exit_node(hostname: str = TS_EXIT_HOSTNAME) -> bool:
    """Tell local Tailscale to route traffic through the exit node."""
    result = subprocess.run(
        ["tailscale", "set", f"--exit-node={hostname}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def is_exit_node_online(hostname: str = TS_EXIT_HOSTNAME) -> bool:
    """Check if the exit node is visible in the local tailnet."""
    result = subprocess.run(
        ["tailscale", "status"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == hostname:
            return "offline" not in line
    return False


def wait_for_exit_node(
    hostname: str = TS_EXIT_HOSTNAME,
    timeout: int = TS_CONNECT_TIMEOUT,
    poll_interval: int = TS_POLL_INTERVAL,
) -> bool:
    """Block until the exit node appears in tailnet. Returns True if found."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_exit_node_online(hostname):
            return True
        time.sleep(poll_interval)
    return False


def _get_device_id(hostname: str = TS_EXIT_HOSTNAME) -> str | None:
    """Find the Tailscale device ID by hostname via ``tailscale status --json``."""
    result = subprocess.run(
        ["tailscale", "status", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):  # fmt: skip
        return None
    for peer in (data.get("Peer") or {}).values():
        if peer.get("HostName") == hostname:
            return peer.get("ID") or peer.get("PublicKey")
    return None


def delete_device(
    api_key: str,
    hostname: str = TS_EXIT_HOSTNAME,
) -> bool:
    """Remove the exit-node device from the tailnet via Admin API.

    Requires a Tailscale API key (not the auth key).
    Returns True on success.
    """
    device_id = _get_device_id(hostname)
    if not device_id:
        return False

    url = f"https://api.tailscale.com/api/v2/device/{device_id}"
    req = Request(url, method="DELETE")
    req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False
