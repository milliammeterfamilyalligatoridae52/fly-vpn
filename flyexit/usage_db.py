"""Session usage log — SQLite cost tracker.

Every VPN session is recorded with start / end timestamps and region.
Cost is derived from Fly.io per-second pricing for the default
shared-cpu-1x + 256 MB machine spec.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Final

# Fly.io shared-cpu-1x + 256 MB RAM — per-second cost (USD).
# $1.94/mo CPU + $0.59/mo RAM = $2.53/mo ÷ 2 592 000 s ≈ $9.76e-7/s
# Source: https://fly.io/docs/about/pricing/
COST_PER_SEC: Final[float] = 2.53 / (30 * 24 * 3600)

DB_PATH: Final[Path] = Path.home() / ".fly_vpn_usage.db"


@dataclass(slots=True)
class UsageStats:
    """Aggregated usage across all recorded sessions."""

    total_sessions: int
    total_seconds: int
    total_cost: float


@dataclass(slots=True)
class SessionRecord:
    """One completed VPN session."""

    id: int
    started_at: float
    ended_at: float
    region: str
    duration_s: int
    cost_usd: float


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  REAL    NOT NULL,
            ended_at    REAL,
            region      TEXT    NOT NULL,
            duration_s  INTEGER,
            cost_usd    REAL
        )
        """,
    )
    conn.commit()
    return conn


def log_start(region: str) -> int:
    """Record session start.  Returns the session row ID."""
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO sessions (started_at, region) VALUES (?, ?)",
        (time.time(), region),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id  # type: ignore[return-value]


def log_end(session_id: int) -> tuple[int, float]:
    """Record session end.  Returns ``(duration_s, cost_usd)``."""
    now = time.time()
    conn = _connect()
    row = conn.execute(
        "SELECT started_at FROM sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        conn.close()
        return 0, 0.0
    duration = int(now - row[0])
    cost = duration * COST_PER_SEC
    conn.execute(
        "UPDATE sessions SET ended_at=?, duration_s=?, cost_usd=? WHERE id=?",
        (now, duration, cost, session_id),
    )
    conn.commit()
    conn.close()
    return duration, cost


def get_stats() -> UsageStats:
    """Aggregated stats across all completed sessions."""
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(duration_s), 0),"
        " COALESCE(SUM(cost_usd), 0)"
        " FROM sessions WHERE ended_at IS NOT NULL",
    ).fetchone()
    conn.close()
    return UsageStats(
        total_sessions=row[0],
        total_seconds=int(row[1]),
        total_cost=row[2],
    )


def get_recent(limit: int = 20) -> list[SessionRecord]:
    """Most recent completed sessions, newest first."""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, started_at, ended_at, region, duration_s, cost_usd"
        " FROM sessions WHERE ended_at IS NOT NULL"
        " ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [SessionRecord(*r) for r in rows]


def get_daily_costs(days: int = 30) -> list[float]:
    """Per-day cost for the last *days* days (oldest → newest).

    Returns exactly *days* floats, zero-filled for days with no usage.
    Used as data source for the Sparkline widget.
    """
    from datetime import datetime, timedelta

    conn = _connect()
    today = datetime.now(tz=UTC).date()
    start = today - timedelta(days=days - 1)

    rows = conn.execute(
        "SELECT DATE(started_at, 'unixepoch') AS d,"
        " SUM(cost_usd)"
        " FROM sessions"
        " WHERE ended_at IS NOT NULL AND d >= ?"
        " GROUP BY d",
        (start.isoformat(),),
    ).fetchall()
    conn.close()

    by_day: dict[str, float] = {r[0]: r[1] for r in rows}
    return [
        by_day.get((start + timedelta(days=i)).isoformat(), 0.0) for i in range(days)
    ]


def get_live_cost(session_id: int) -> tuple[int, float]:
    """Current duration and cost of a *running* session (not yet ended)."""
    conn = _connect()
    row = conn.execute(
        "SELECT started_at FROM sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    conn.close()
    if not row:
        return 0, 0.0
    duration = int(time.time() - row[0])
    return duration, duration * COST_PER_SEC


def format_duration(seconds: int) -> str:
    """Human-readable duration: ``2h 15m`` or ``45m 30s``."""
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def format_cost(usd: float) -> str:
    """Full-precision cost — never round."""
    if usd < 0.001:
        return f"${usd:.6f}"
    if usd < 1:
        return f"${usd:.4f}"
    return f"${usd:.2f}"


def print_stats() -> None:
    """Print a usage summary table to stdout (``--stats`` CLI)."""
    from datetime import datetime

    stats = get_stats()
    recent = get_recent(10)

    print("\n  ╭─────────────────────────────────────╮")
    print("  │   🛡  Fly VPN — Usage Summary       │")
    print("  ╰─────────────────────────────────────╯\n")

    if stats.total_sessions == 0:
        print("  No sessions recorded yet.\n")
        return

    print(f"  Sessions:  {stats.total_sessions}")
    print(f"  Uptime:    {format_duration(stats.total_seconds)}")
    print(f"  Cost:      {format_cost(stats.total_cost)}")
    print()
    fmt = "  {:<18s}  {:<6s}  {:>8s}  {:>10s}"
    sep = "  " + "─" * 48
    print(sep)
    print(fmt.format("Date", "Region", "Duration", "Cost"))
    print(sep)
    for s in recent:
        dt = datetime.fromtimestamp(
            s.started_at,
            tz=UTC,
        ).astimezone()
        print(
            fmt.format(
                dt.strftime("%Y-%m-%d %H:%M"),
                s.region,
                format_duration(s.duration_s),
                format_cost(s.cost_usd),
            ),
        )
    print()
