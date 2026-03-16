"""Fly.io region catalogue and application defaults."""

from __future__ import annotations

import os
from typing import Final

DEFAULT_REGION: Final = "ams"
DEFAULT_APP_NAME: Final = "fly-vpn-node"
DEFAULT_ORG: Final = "personal"

# Fly CLI environment — suppress update prompts.
FLY_ENV: Final[dict[str, str]] = {**os.environ, "FLY_NO_UPDATE_CHECK": "1"}

# Tailscale exit-node settings.
TS_EXIT_HOSTNAME: Final = "fly-vpn-exit"
TS_CONNECT_TIMEOUT: Final = 30  # seconds to wait for node in tailnet
TS_POLL_INTERVAL: Final = 2  # seconds between status polls

# (code, flag + city) - used to populate the region selector.
FLY_REGIONS: Final[list[tuple[str, str]]] = [
    ("ams", "🇳🇱 Amsterdam"),
    ("cdg", "🇫🇷 Paris"),
    ("fra", "🇩🇪 Frankfurt"),
    ("lhr", "🇬🇧 London"),
    ("mad", "🇪🇸 Madrid"),
    ("waw", "🇵🇱 Warsaw"),
    ("otp", "🇷🇴 Bucharest"),
    ("iad", "🇺🇸 Washington DC"),
    ("ewr", "🇺🇸 New Jersey"),
    ("ord", "🇺🇸 Chicago"),
    ("dfw", "🇺🇸 Dallas"),
    ("den", "🇺🇸 Denver"),
    ("lax", "🇺🇸 Los Angeles"),
    ("sea", "🇺🇸 Seattle"),
    ("sjc", "🇺🇸 San Jose"),
    ("mia", "🇺🇸 Miami"),
    ("yul", "🇨🇦 Montreal"),
    ("yyz", "🇨🇦 Toronto"),
    ("gru", "🇧🇷 São Paulo"),
    ("scl", "🇨🇱 Santiago"),
    ("qro", "🇲🇽 Querétaro"),
    ("nrt", "🇯🇵 Tokyo"),
    ("hkg", "🇭🇰 Hong Kong"),
    ("sin", "🇸🇬 Singapore"),
    ("syd", "🇦🇺 Sydney"),
    ("jnb", "🇿🇦 Johannesburg"),
]
