"""Tailscale ACL auto-configuration (business logic).

Reads the current policy, merges required entries for exit-node
auto-approval, and writes back — idempotent and ETag-safe.

The HTTP transport is delegated to
:class:`flyexit.tailscale_api.TailscaleAPIClient`.
"""

from __future__ import annotations

import logging
import os
import sys

import httpx

from flyexit.tailscale_api import TAG, TAG_OWNER, TailscaleAPIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [fly-vpn-acl] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _ensure_tag_owners(acl: dict) -> bool:
    """Add ``tag:ephemeral-vpn`` to ``tagOwners`` if missing."""
    tag_owners = acl.setdefault("tagOwners", {})
    if TAG in tag_owners:
        return False
    tag_owners[TAG] = [TAG_OWNER]
    return True


def _ensure_node_attrs(acl: dict) -> bool:
    """Add exit-node attribute for the tag if missing."""
    node_attrs: list[dict] = acl.setdefault("nodeAttrs", [])
    for entry in node_attrs:
        targets = entry.get("target", [])
        attrs = entry.get("attr", [])
        if TAG in targets and "can-be-exit-node" in attrs:
            return False
    node_attrs.append({"target": [TAG], "attr": ["can-be-exit-node"]})
    return True


def _ensure_auto_approvers(acl: dict) -> bool:
    """Add exit-node auto-approval for the tag if missing."""
    auto = acl.setdefault("autoApprovers", {})
    exit_nodes: list[str] = auto.setdefault("exitNode", [])
    if TAG in exit_nodes:
        return False
    exit_nodes.append(TAG)
    return True


def setup_acl(client: TailscaleAPIClient) -> bool:
    """Read → merge → write the Tailscale ACL.

    Returns True on success.  Skips the write when the policy already
    contains every required entry (idempotent).
    """
    log.info("Reading current Tailscale ACL policy…")
    try:
        acl, etag = client.get_acl()
    except httpx.HTTPStatusError as exc:
        log.error(
            "Failed to read ACL (HTTP %d): %s",
            exc.response.status_code,
            exc.response.text,
        )
        return False
    except httpx.HTTPError as exc:
        log.error("Failed to reach Tailscale API: %s", exc)
        return False

    changed = _ensure_tag_owners(acl)
    changed |= _ensure_node_attrs(acl)
    changed |= _ensure_auto_approvers(acl)

    if not changed:
        log.info("ACL already configured — nothing to do. ✅")
        return True

    log.info("Updating ACL with Fly VPN entries…")
    if client.set_acl(acl, etag):
        log.info("ACL updated successfully. ✅")
        log.info("  ✓ tagOwners: %s → [%s]", TAG, TAG_OWNER)
        log.info("  ✓ nodeAttrs: %s can-be-exit-node", TAG)
        log.info("  ✓ autoApprovers: exitNode → %s", TAG)
        return True

    return False


def run_setup_acl() -> None:
    """CLI handler for ``--setup-acl``."""
    api_key = os.environ.get("TAILSCALE_API_KEY", "")
    if not api_key:
        log.error(
            "TAILSCALE_API_KEY not set. "
            "Add it to .env or export it before running --setup-acl."
        )
        sys.exit(1)

    client = TailscaleAPIClient(api_key)
    ok = setup_acl(client)
    sys.exit(0 if ok else 1)
