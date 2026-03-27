"""Persistent JSON configuration helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flyexit.constants import (
    DEFAULT_APP_NAME,
    DEFAULT_ORG,
    DEFAULT_REGION,
    DEFAULT_VM_MEMORY,
)

CONFIG_PATH: Path = Path.home() / ".fly_vpn_config.json"

_DEFAULTS: dict[str, Any] = {
    "region": DEFAULT_REGION,
    "app_name": DEFAULT_APP_NAME,
    "org": DEFAULT_ORG,
    "vm_memory": DEFAULT_VM_MEMORY,
}


def load() -> dict[str, Any]:
    """Read config from disk, falling back to built-in defaults."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return dict(_DEFAULTS)


def save(config: dict[str, Any]) -> None:
    """Atomically write *config* to disk."""
    CONFIG_PATH.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")
