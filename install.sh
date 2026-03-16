#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Fly VPN — desktop installer
#  Installs the app into macOS Applications or GNOME desktop.
#  Windows is not supported.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

APP_NAME="Fly VPN"
APP_ID="io.github.fly-vpn"
ICON_NAME="fly-vpn"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WATCHDOG_LABEL="${APP_ID}.watchdog"

# ── colours ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}${BOLD}▸${NC} $*"; }
ok()    { echo -e "${GREEN}${BOLD}✔${NC} $*"; }
err()   { echo -e "${RED}${BOLD}✖${NC} $*" >&2; }

# ── pre-checks ──────────────────────────────────────────────

if [[ "$(uname -s)" == *MINGW* || "$(uname -s)" == *CYGWIN* || "$(uname -s)" == *MSYS* ]]; then
    err "Windows is not supported."
    exit 1
fi

# ── install uv if missing ───────────────────────────────────

if ! command -v uv &>/dev/null; then
    info "'uv' not found — installing automatically…"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Ensure the freshly installed binary is on PATH for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        err "Failed to install uv. Install it manually: https://docs.astral.sh/uv/"
        exit 1
    fi
    ok "uv installed"
fi

# ── .env setup ──────────────────────────────────────────────

ENV_FILE="$REPO_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo ""
    info "No .env file found — let's set it up."
    echo ""
    echo -e "  Create a Tailscale auth key at:"
    echo -e "  ${CYAN}https://login.tailscale.com/admin/settings/keys${NC}"
    echo ""
    echo -e "  Required settings when generating the key:"
    echo -e "    ${BOLD}✓${NC} Reusable    — so one key works for many sessions"
    echo -e "    ${BOLD}✓${NC} Ephemeral   — device auto-removed when it goes offline"
    echo -e "    ${BOLD}✓${NC} Tags        — assign ${BOLD}tag:ephemeral-vpn${NC}"
    echo ""
    read -rp "  TAILSCALE_AUTHKEY: " ts_key

    if [[ -n "$ts_key" ]]; then
        echo "TAILSCALE_AUTHKEY=$ts_key" > "$ENV_FILE"
        ok ".env created with your auth key"
    else
        info "Skipped — you can create .env later manually."
    fi

    echo ""
    info "Optional: Tailscale API key for instant device cleanup."
    echo ""
    echo -e "  Without it, ephemeral nodes auto-remove in ~5–30 min."
    echo -e "  With it, the node is deleted from your tailnet immediately on Stop."
    echo ""
    echo -e "  Generate an API key at:"
    echo -e "  ${CYAN}https://login.tailscale.com/admin/settings/keys${NC}"
    echo -e "  (scroll to ${BOLD}API keys${NC} → ${BOLD}Generate API key${NC})"
    echo ""
    read -rp "  TAILSCALE_API_KEY (Enter to skip): " ts_api_key

    if [[ -n "$ts_api_key" ]]; then
        echo "TAILSCALE_API_KEY=$ts_api_key" >> "$ENV_FILE"
        ok "API key saved — nodes will be removed instantly on Stop"
    else
        info "Skipped — ephemeral nodes will auto-remove after a few minutes."
    fi
    echo ""
fi

# ── Tailscale ACL reminder ──────────────────────────────────

echo ""
info "Tailscale ACL setup required (one-time)."
echo ""
echo -e "  Add these blocks to your Tailscale ACL file:"
echo -e "  ${CYAN}https://login.tailscale.com/admin/acls/file${NC}"
echo ""
echo -e "  ${BOLD}1.${NC} In ${BOLD}\"tagOwners\"${NC} — allow your account to use the tag:"
echo ""
echo -e "     ${GREEN}\"tag:ephemeral-vpn\": [\"YOUR_EMAIL@gmail.com\"]${NC}"
echo ""
echo -e "  ${BOLD}2.${NC} In ${BOLD}\"nodeAttrs\"${NC} — allow tagged nodes to be exit nodes:"
echo ""
echo -e "     ${GREEN}{${NC}"
echo -e "     ${GREEN}  \"target\": [\"tag:ephemeral-vpn\"],${NC}"
echo -e "     ${GREEN}  \"attr\": [\"can-be-exit-node\"]${NC}"
echo -e "     ${GREEN}}${NC}"
echo ""
echo -e "  ${BOLD}3.${NC} In ${BOLD}\"autoApprovers\"${NC} — auto-approve exit nodes (no manual approval):"
echo ""
echo -e "     ${GREEN}\"autoApprovers\": {${NC}"
echo -e "     ${GREEN}  \"exitNode\": [\"tag:ephemeral-vpn\"]${NC}"
echo -e "     ${GREEN}}${NC}"
echo ""
read -rp "  Press Enter when done (or 's' to skip): " acl_ack
if [[ "$acl_ack" == "s" || "$acl_ack" == "S" ]]; then
    info "Skipped — remember to configure ACL before first launch."
else
    ok "ACL acknowledged"
fi
echo ""

# ── fly CLI check ────────────────────────────────────────────

export FLY_NO_UPDATE_CHECK=1
export HOMEBREW_NO_AUTO_UPDATE=1

if ! command -v fly &>/dev/null && ! command -v flyctl &>/dev/null; then
    info "'fly' CLI not found — installing…"
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
    if ! command -v fly &>/dev/null && ! command -v flyctl &>/dev/null; then
        err "Failed to install fly CLI. Install manually: https://fly.io/docs/flyctl/install/"
        exit 1
    fi
    ok "fly CLI installed"
fi

FLY_CMD="fly"
if ! command -v fly &>/dev/null && command -v flyctl &>/dev/null; then
    FLY_CMD="flyctl"
fi

# Check if fly is authenticated
if ! "$FLY_CMD" auth whoami &>/dev/null 2>&1; then
    echo ""
    info "Fly.io not authenticated — opening login…"
    "$FLY_CMD" auth login
    if ! "$FLY_CMD" auth whoami &>/dev/null 2>&1; then
        err "Fly.io login failed. Run '$FLY_CMD auth login' manually."
        exit 1
    fi
    ok "Fly.io authenticated"
else
    FLY_USER=$("$FLY_CMD" auth whoami 2>/dev/null)
    ok "Fly.io authenticated as $FLY_USER"
fi

# ── resolve python & venv ───────────────────────────────────

info "Syncing dependencies…"
(cd "$REPO_DIR" && uv sync --quiet)

# Resolve the fly-vpn entry-point that uv created
VENV_BIN="$REPO_DIR/.venv/bin"
FLY_VPN_BIN="$VENV_BIN/fly-vpn"

if [[ ! -x "$FLY_VPN_BIN" ]]; then
    err "Entry-point '$FLY_VPN_BIN' not found after uv sync."
    exit 1
fi

ok "Dependencies synced"

# ── OS dispatch ─────────────────────────────────────────────

install_macos() {
    local app_dir="/Applications/${APP_NAME}.app"
    local contents="$app_dir/Contents"
    local macos_dir="$contents/MacOS"

    info "Installing into $app_dir …"

    mkdir -p "$macos_dir" "$contents/Resources"

    # 1) Helper shell script that Terminal.app will source
    cat > "$macos_dir/run.sh" <<EOF
#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:\$HOME/.fly/bin:\$PATH"
export FLY_NO_UPDATE_CHECK=1
export HOMEBREW_NO_AUTO_UPDATE=1
cd "$REPO_DIR"
[ -f .env ] && { set -a; . .env; set +a; }
exec "$FLY_VPN_BIN"
EOF
    chmod +x "$macos_dir/run.sh"

    # 2) Main launcher — uses osascript to open Terminal with run.sh
    cat > "$macos_dir/fly-vpn-launcher" <<EOF
#!/usr/bin/env bash
open -a Terminal "$macos_dir/run.sh"
EOF
    chmod +x "$macos_dir/fly-vpn-launcher"

    # Info.plist
    cat > "$contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${APP_ID}</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleExecutable</key>
    <string>fly-vpn-launcher</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

    ok "Installed ${APP_NAME}.app → /Applications"
    echo ""
    info "Open it from Spotlight or Launchpad."
    info "It runs in Terminal (Textual TUI)."
}

install_linux() {
    local desktop_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    local desktop_file="$desktop_dir/${APP_ID}.desktop"

    info "Installing .desktop entry…"
    mkdir -p "$desktop_dir"

    cat > "$desktop_file" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Ephemeral Tailscale exit-node launcher on Fly.io
Exec=bash -c 'cd ${REPO_DIR} && if [ -f .env ]; then set -a; . .env; set +a; fi; exec ${FLY_VPN_BIN}'
Terminal=true
Categories=Network;VPN;Utility;
Keywords=vpn;tailscale;fly;exit-node;
StartupNotify=false
DESKTOP

    # Refresh GNOME desktop database if available
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$desktop_dir" 2>/dev/null || true
    fi

    ok "Installed desktop entry → $desktop_file"
    echo ""
    info "Find '${APP_NAME}' in your GNOME Activities / app menu."
}

# ── watchdog (daily orphan-app check) ───────────────────────

install_watchdog_macos() {
    local plist_dir="$HOME/Library/LaunchAgents"
    local plist="$plist_dir/${WATCHDOG_LABEL}.plist"

    mkdir -p "$plist_dir"

    cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${WATCHDOG_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${FLY_VPN_BIN}</string>
        <string>--watchdog</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:$HOME/.fly/bin:/usr/bin:/bin</string>
        <key>FLY_NO_UPDATE_CHECK</key>
        <string>1</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>12</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/fly-vpn-watchdog.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/fly-vpn-watchdog.log</string>
</dict>
</plist>
PLIST

    launchctl unload "$plist" 2>/dev/null || true
    launchctl load "$plist"
    ok "Watchdog scheduled (daily 12:00) via launchd"
}

install_watchdog_linux() {
    local cron_cmd="0 12 * * * cd $REPO_DIR && $FLY_VPN_BIN --watchdog >> /tmp/fly-vpn-watchdog.log 2>&1"
    local cron_marker="# fly-vpn-watchdog"

    # Remove old entry if present, then add
    ( crontab -l 2>/dev/null | grep -v "$cron_marker" ; echo "$cron_cmd $cron_marker" ) | crontab -
    ok "Watchdog scheduled (daily 12:00) via crontab"
}

uninstall_watchdog_macos() {
    local plist="$HOME/Library/LaunchAgents/${WATCHDOG_LABEL}.plist"
    if [[ -f "$plist" ]]; then
        launchctl unload "$plist" 2>/dev/null || true
        rm -f "$plist"
        ok "Watchdog launchd job removed"
    fi
}

uninstall_watchdog_linux() {
    local cron_marker="# fly-vpn-watchdog"
    if crontab -l 2>/dev/null | grep -q "$cron_marker"; then
        crontab -l 2>/dev/null | grep -v "$cron_marker" | crontab -
        ok "Watchdog cron entry removed"
    fi
}

prompt_watchdog() {
    echo ""
    info "Optional: daily watchdog to auto-destroy orphaned Fly apps."
    echo -e "  Runs at ${BOLD}12:00${NC} daily — checks if a fly-vpn-node app was left"
    echo -e "  running and destroys it to ${BOLD}prevent charges${NC}."
    echo ""
    read -rp "  Enable watchdog? [y/N]: " wd_answer
    if [[ "$wd_answer" == "y" || "$wd_answer" == "Y" ]]; then
        case "$(uname -s)" in
            Darwin)  install_watchdog_macos  ;;
            Linux)   install_watchdog_linux  ;;
        esac
    else
        info "Watchdog skipped — you can enable it later with: bash install.sh watchdog"
    fi
}

# ── uninstall ───────────────────────────────────────────────

uninstall_macos() {
    local app_dir="/Applications/${APP_NAME}.app"
    if [[ -d "$app_dir" ]]; then
        rm -rf "$app_dir"
        ok "Removed $app_dir"
    else
        info "Nothing to remove — $app_dir does not exist."
    fi
    uninstall_watchdog_macos
}

uninstall_linux() {
    local desktop_file="${XDG_DATA_HOME:-$HOME/.local/share}/applications/${APP_ID}.desktop"
    if [[ -f "$desktop_file" ]]; then
        rm -f "$desktop_file"
        if command -v update-desktop-database &>/dev/null; then
            update-desktop-database "$(dirname "$desktop_file")" 2>/dev/null || true
        fi
        ok "Removed $desktop_file"
    else
        info "Nothing to remove — desktop entry does not exist."
    fi
    uninstall_watchdog_linux
}

# ── main ────────────────────────────────────────────────────

usage() {
    echo "Usage: $0 [install|uninstall|watchdog]"
    echo ""
    echo "  install     Install Fly VPN as a desktop application (default)"
    echo "  uninstall   Remove Fly VPN from the desktop"
    echo "  watchdog    Enable/disable the daily orphan-app watchdog"
}

ACTION="${1:-install}"
OS="$(uname -s)"

case "$ACTION" in
    install)
        echo ""
        echo -e "${BOLD}🛡  Fly VPN — Desktop Installer${NC}"
        echo ""
        case "$OS" in
            Darwin)  install_macos  ;;
            Linux)   install_linux  ;;
            *)       err "Unsupported OS: $OS"; exit 1 ;;
        esac
        prompt_watchdog
        ;;
    uninstall)
        echo ""
        echo -e "${BOLD}🗑  Fly VPN — Uninstaller${NC}"
        echo ""
        case "$OS" in
            Darwin)  uninstall_macos  ;;
            Linux)   uninstall_linux  ;;
            *)       err "Unsupported OS: $OS"; exit 1 ;;
        esac
        ;;
    watchdog)
        echo ""
        echo -e "${BOLD}⏰  Fly VPN — Watchdog Setup${NC}"
        echo ""
        prompt_watchdog
        ;;
    -h|--help)
        usage
        ;;
    *)
        err "Unknown action: $ACTION"
        usage
        exit 1
        ;;
esac
