"""Textual TUI application for Fly VPN.

This module is a **pure UI shell**.  All business logic (auth checks,
subprocess management, Tailscale connection) lives in
:mod:`flyexit.session`.  The app only reads structured results and
formats them for display.
"""

from __future__ import annotations

import atexit
import contextlib
import os
import signal
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, RichLog, Select, Static

from flyexit import config
from flyexit.constants import (
    DEFAULT_APP_NAME,
    DEFAULT_ORG,
    FLY_REGIONS,
    TS_EXIT_HOSTNAME,
)
from flyexit.session import (
    AppStatus,
    ConnectStatus,
    LaunchResult,
    LaunchStatus,
    PreflightStatus,
    VPNSession,
)
from flyexit.styles import APP_CSS


class FlyVPNApp(App[None]):
    """Ephemeral Tailscale exit-node launcher on Fly.io."""

    TITLE = "Fly VPN"
    SUB_TITLE = "Tailscale Exit Node on Fly.io"
    CSS = APP_CSS

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("l", "launch", "Launch", priority=True),
        Binding("s", "stop", "Stop", priority=True),
        Binding("t", "toggle_dark", "Theme", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._cfg = config.load()
        self._auth_key: str = os.environ.get("TAILSCALE_AUTHKEY", "")
        self._session = VPNSession()

        atexit.register(self._session.emergency_cleanup)

    def _on_signal(self, signum: int, _frame: object) -> None:
        """Handle SIGINT / SIGTERM — clean up and exit."""
        self._session.emergency_cleanup()
        raise SystemExit(128 + signum)

    def on_mount(self) -> None:
        signal.signal(signal.SIGINT, self._on_signal)
        signal.signal(signal.SIGTERM, self._on_signal)

        log = self._rich_log
        log.write("[bold green]🛡  Fly VPN[/] initialized")
        log.write("")
        if not self._auth_key:
            log.write("[bold red]⚠  TAILSCALE_AUTHKEY not set![/]")
            log.write("Create a [bold].env[/] file with:")
            log.write("  TAILSCALE_AUTHKEY=tskey-auth-...")
            self.query_one("#btn-launch", Button).disabled = True

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main"):
            with Container(id="controls"):
                with Horizontal(id="region-row"):
                    yield Label("Region:")
                    yield Select(
                        [(f"{flag}  {code}", code) for code, flag in FLY_REGIONS],
                        value=self._cfg.get("region", "ams"),
                        id="region-select",
                    )
                with Horizontal(id="button-row"):
                    yield Button("🚀 Launch", variant="success", id="btn-launch")
                    yield Button(
                        "🛑 Stop", variant="error", id="btn-stop", disabled=True
                    )
            yield Static("Ready", id="status-bar")
            with Container(id="log-box"):
                yield RichLog(highlight=True, markup=True, id="log")
        yield Footer()

    @property
    def _rich_log(self) -> RichLog:
        return self.query_one("#log", RichLog)

    def _log(self, msg: str) -> None:
        self._rich_log.write(msg)

    def _set_status(self, text: str) -> None:
        self.query_one("#status-bar", Static).update(text)

    def _set_buttons(self, *, launching: bool) -> None:
        self.query_one("#btn-launch", Button).disabled = launching
        self.query_one("#btn-stop", Button).disabled = not launching

    def action_launch(self) -> None:
        self._do_launch()

    def action_stop(self) -> None:
        self._do_stop()

    def action_quit(self) -> None:
        self._teardown_with_log()
        super().action_quit()

    @on(Button.Pressed, "#btn-launch")
    def _handle_launch(self) -> None:
        self._do_launch()

    @on(Button.Pressed, "#btn-stop")
    def _handle_stop(self) -> None:
        self._do_stop()

    def _do_launch(self) -> None:
        if self._session.is_active:
            self._log("[dim]Already running[/]")
            return
        self._run_launch()

    @work(thread=True)
    def _run_launch(self) -> None:
        """Single worker: preflight → launch → connect."""
        app_name = self._cfg.get("app_name", DEFAULT_APP_NAME)
        org = self._cfg.get("org", DEFAULT_ORG)

        pf = self._session.preflight(app_name, org)
        if pf.username:
            self.call_from_thread(self._log, f"[dim]Authenticated as {pf.username}[/]")
        if pf.status is not PreflightStatus.OK:
            self.call_from_thread(self._log, f"[bold red]⚠  {pf.error}[/]")
            return

        verb = "found" if pf.app_status is AppStatus.FOUND else "created ✅"
        self.call_from_thread(self._log, f"[dim]App [bold]{app_name}[/bold] {verb}[/]")

        region = self.query_one("#region-select", Select).value
        if region is Select.BLANK:
            region = self._cfg.get("region", "ams")
        region = str(region)
        self._cfg["region"] = region
        config.save(self._cfg)

        self.call_from_thread(self._set_buttons, launching=True)
        self.call_from_thread(self._set_status, f"🔄 Launching in {region}…")
        self.call_from_thread(
            self._log,
            f"\n[bold cyan]>>> Launching exit node in [yellow]{region}[/yellow]…[/]",
        )

        result = self._session.launch(
            app_name,
            region,
            self._auth_key,
            on_output=lambda line: self.call_from_thread(self._log, line),
        )

        if result.status is LaunchStatus.OK:
            self.call_from_thread(
                self._log,
                "[bold green]✅ Node launched successfully![/]",
            )
            self.call_from_thread(self._set_status, f"✅ Running in {region}")
            self._show_connect_result(region)
            return

        self._log_launch_error(result)

        self.call_from_thread(self._log, "[dim]🧹 Cleaning up remote resources…[/]")
        app_d, ok = self._session.teardown()
        self._log_teardown(app_d, ok, from_thread=True)
        self.call_from_thread(self._set_buttons, launching=False)
        self.call_from_thread(self._set_status, "Ready")

    def _show_connect_result(self, region: str) -> None:
        """Wait for Tailscale exit node and display the outcome."""
        self.call_from_thread(
            self._log,
            f"[dim]⏳ Waiting for [bold]{TS_EXIT_HOSTNAME}[/bold]"
            " to appear in tailnet…[/]",
        )
        self.call_from_thread(
            self._set_status,
            f"⏳ Waiting for exit node in {region}…",
        )

        status = self._session.wait_and_connect()

        if status is ConnectStatus.CONNECTED:
            self.call_from_thread(
                self._log,
                f"[bold green]🔗 Connected![/] Traffic routed"
                f" through [bold]{TS_EXIT_HOSTNAME}[/]"
                f" ({region})\n"
                "[dim]  Press [bold]Stop[/bold] (or [bold]s[/bold])"
                " to disconnect and clean up.[/]",
            )
            self.call_from_thread(
                self._set_status,
                f"🟢 VPN active via {region} — press Stop to end",
            )
        elif status is ConnectStatus.TIMEOUT:
            self.call_from_thread(
                self._log,
                "[yellow]⚠  Exit node didn't appear in time. "
                "Connect manually via Tailscale.[/]\n"
                "[dim]  Press [bold]Stop[/bold] (or [bold]s[/bold])"
                " to terminate and clean up.[/]",
            )
            self.call_from_thread(
                self._set_status,
                f"🟡 Running in {region} — manual connect needed",
            )
        else:  # ConnectStatus.FAILED
            self.call_from_thread(
                self._log,
                "[yellow]⚠  Node is online but auto-connect"
                " failed.\n  Try manually: tailscale set"
                f" --exit-node={TS_EXIT_HOSTNAME}[/]",
            )
            self.call_from_thread(
                self._set_status,
                f"🟡 Running in {region} — manual connect needed",
            )

    def _do_stop(self) -> None:
        if self._session.is_active:
            self._log("[bold yellow]⏹  Stopping node…[/]")
            self._run_stop()
        else:
            self._log("[dim]Nothing to stop[/]")

    @work(thread=True)
    def _run_stop(self) -> None:
        """Teardown session in a background thread."""
        app_name, ok = self._session.teardown()
        self.call_from_thread(self._log, "[dim]🔌 Disconnected from exit node[/]")
        self._log_teardown(app_name, ok, from_thread=True)
        self.call_from_thread(self._set_buttons, launching=False)
        self.call_from_thread(self._set_status, "Ready")

    def _teardown_with_log(self) -> None:
        """Synchronous teardown used by action_quit."""
        app_name, ok = self._session.teardown()
        self._log_teardown(app_name, ok, from_thread=False)

    def _log_launch_error(self, result: LaunchResult) -> None:
        """Format and log a failed LaunchResult."""
        if result.status is LaunchStatus.CLI_MISSING:
            self.call_from_thread(
                self._log,
                "[bold red]❌ 'fly' CLI not found.[/]  "
                "Install → curl -L https://fly.io/install.sh | sh",
            )
        elif result.status is LaunchStatus.ERROR:
            self.call_from_thread(self._log, f"[bold red]❌ Error: {result.error}[/]")
        else:  # LaunchStatus.PROCESS_FAILED
            self.call_from_thread(
                self._log,
                f"[bold red]❌ Exited with code {result.return_code}[/]",
            )
            if result.hint:
                self.call_from_thread(self._log, result.hint)

    def _log_teardown(
        self, app_name: str | None, ok: bool, *, from_thread: bool
    ) -> None:
        """Log the outcome of a session teardown."""
        if not app_name:
            return
        msg = (
            f"[bold green]🗑  App [bold]{app_name}[/bold] deleted (no charges)[/]"
            if ok
            else f"[yellow]⚠  Could not delete app {app_name}[/]"
        )
        if from_thread:
            self.call_from_thread(self._log, msg)
        else:
            with contextlib.suppress(Exception):
                self._log(msg)
