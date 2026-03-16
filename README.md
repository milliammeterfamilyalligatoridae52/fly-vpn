# 🛡️ Fly VPN — disposable global VPN in seconds

**Launch a private exit node anywhere in the world with one keypress.**

Fly VPN spins up an **ephemeral Tailscale exit node** on [Fly.io](https://fly.io), connects you automatically, and destroys cloud resources when you stop.

No always-on VM. No manual cleanup. No billing anxiety.

---

## Use cases

- 🔒 **Test geo-restricted APIs** — hit endpoints as if you're in Frankfurt, Tokyo, or São Paulo
- 🛡️ **Secure browsing on public Wi-Fi** — route traffic through your own ephemeral node
- 🧪 **QA regional content** — verify localization, pricing, or CDN behavior per region
- 🏗️ **Dev/staging access** — reach region-locked services without a permanent VPN
- 🎯 **Ad & SEO audits** — see what users in different markets actually see
- 🚀 **Demo day** — show your product from a client's region in real time
- 🎮 **Gaming** — connect to region-locked servers or get a fresh IP in seconds

---

## Why teams love it

- 🌍 **Choose region instantly** (EU/US/APAC and more)
- ⚡ **One-click launch** from a polished terminal UI
- 🔗 **Auto-connect** to the exit node when it comes online
- 🧹 **Safe teardown** on Stop / Quit / Signal
- 💸 **Cost-aware by design** — ephemeral infra only
- 🛟 **Watchdog mode** to remove orphaned Fly apps

---

## 30-second flow

1. Choose a region (`ams`, `fra`, `iad`, ...)
2. Press **Launch**
3. App creates/starts temporary exit node
4. Local Tailscale auto-routes traffic through that node
5. Press **Stop** → app, machine, and route are cleaned up

---

## Quick start

```bash
git clone https://github.com/invilso/fly-vpn.git
cd fly-vpn
bash install.sh
```

Installer flow:
1. Installs **uv** and **Fly CLI** (if missing)
2. Prompts for **TAILSCALE_AUTHKEY** and writes `.env`
3. Shows required **ACL** config for exit-node auto-approval
4. Installs dependencies
5. Checks Fly.io auth (opens `fly auth login` if needed)
6. Registers desktop entry (macOS Applications / GNOME menu)

---

## Tailscale setup (required once)

Create an auth key that is:
- **Reusable**
- **Ephemeral**
- Tagged with: `tag:ephemeral-vpn`

Add ACL policy in Tailscale admin:

```jsonc
{
  "tagOwners": {
    "tag:ephemeral-vpn": ["autogroup:owner"]
  },
  "nodeAttrs": [
    {
      "target": ["tag:ephemeral-vpn"],
      "attr": ["can-be-exit-node"]
    }
  ],
  "autoApprovers": {
    "exitNode": ["tag:ephemeral-vpn"]
  }
}
```

---

## Run

```bash
# Preferred
fly-vpn

# Alternatives
uv run fly-vpn
python main.py
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `l` | Launch exit node |
| `s` | Stop and cleanup |
| `t` | Toggle dark/light theme |
| `q` | Quit |

---

## Safety model

- Exit-node usage is explicit (manual Launch)
- Exit route is removed during teardown
- Fly app/machines are destroyed on cleanup paths
- Watchdog can be run from cron/CI to enforce cleanup

> Fly VPN does **not** replace your identity/privacy model. It automates infra lifecycle and routing ergonomics.

---

## Watchdog mode

Cleanup helper for CI/cron/manual recovery:

```bash
python main.py --watchdog
```

It checks for orphaned app resources and destroys them to prevent charges.

Tip: great as a daily cron safety net. The installer will offer to set this up automatically.

---

## Requirements

- macOS or Linux (Windows is **not** supported)
- Python 3.14+
- [Fly.io](https://fly.io) account with a payment method on file
- [Fly.io CLI](https://fly.io/docs/flyctl/install/) (`fly`) — auto-installed by `install.sh`
- [Tailscale](https://tailscale.com) account + auth key

---

## Troubleshooting quick hits

- **"Fly.io not authenticated"** → run `fly auth login`
- **Region timeout / no capacity** → switch region in UI and retry
- **Node appears but no auto-connect** → run `tailscale set --exit-node=fly-vpn-exit`
- **Want hard cleanup now** → run watchdog: `python main.py --watchdog`

---

## Architecture (clean layered design)

```
flyexit/
├── app.py         # UI layer (Textual only)
├── session.py     # business orchestration (preflight/launch/connect/teardown)
├── fly_ops.py     # Fly.io adapter (CLI operations)
├── tailscale.py   # Tailscale adapter
├── diagnosis.py   # friendly failure hints
├── config.py      # persisted user config
├── constants.py   # defaults, regions, timeouts
├── styles.py      # UI styling
└── watchdog.py    # headless safety cleanup

main.py            # entry-point (app / watchdog)
install.sh         # installer/uninstaller
```

Design principle: **UI-only app layer + enum-based session orchestration + thin infrastructure adapters**.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14 |
| TUI framework | [Textual](https://github.com/Textualize/textual) |
| Cloud runtime | [Fly.io](https://fly.io) (ephemeral machines) |
| VPN mesh | [Tailscale](https://tailscale.com) (WireGuard-based) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Build backend | [Hatchling](https://hatch.pypa.io/) |
| Linter | [Ruff](https://docs.astral.sh/ruff/) |

---

## Uninstall

```bash
bash install.sh uninstall
```

---

## License

MIT
