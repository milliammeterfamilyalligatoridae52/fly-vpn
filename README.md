# 🛡️ Fly VPN — disposable global VPN in seconds

**Launch a private exit node in any of 35+ regions with one keypress. Pay only for the minutes you use.**

Fly VPN spins up an **ephemeral Tailscale exit node** on [Fly.io](https://fly.io), waits for it to come online, auto-routes your traffic through it, and **destroys everything** — app, machine, route — the moment you press Stop.

No always-on VM. No manual cleanup. No billing anxiety. No shared IPs.

Under the hood: WireGuard-powered [Tailscale](https://tailscale.com) mesh + [Fly Machines](https://fly.io/docs/machines/) that cold-start in ~3 seconds and bill per-second. A typical session costs **a fraction of a cent**.

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

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.14 |
| TUI framework | [Textual](https://github.com/Textualize/textual) |
| Cloud runtime | [Fly.io](https://fly.io) (ephemeral machines) |
| VPN mesh | [Tailscale](https://tailscale.com) (WireGuard-based) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Build backend | [Hatchling](https://hatch.pypa.io/) |
| Linter | [Ruff](https://docs.astral.sh/ruff/) |

---

## Requirements

- macOS or Linux (Windows is **not** supported)
- Python 3.14+
- [Fly.io](https://fly.io) account with a payment method on file
- [Fly.io CLI](https://fly.io/docs/flyctl/install/) (`fly`) — auto-installed by `install.sh`
- [Tailscale](https://tailscale.com) account + auth key — **or** a self-hosted [Headscale](https://github.com/juanfont/headscale) server
- *(Optional)* [Tailscale API key](https://login.tailscale.com/admin/settings/keys) for instant device cleanup (SaaS only)

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
3. Optionally prompts for **TAILSCALE_API_KEY** (enables instant device cleanup on Stop)
4. Asks if you use **self-hosted Tailscale (Headscale)** — prompts for `TS_LOGIN_SERVER`
5. Shows required **ACL** config for exit-node auto-approval
6. Installs dependencies
7. Checks Fly.io auth (opens `fly auth login` if needed)
8. Registers desktop entry (macOS Applications / GNOME menu)

---

## Why Fly.io?

| Criteria | Fly.io | AWS EC2 / Lightsail | DigitalOcean | Hetzner |
|----------|--------|---------------------|--------------|----------|
| Cold start | **~3 s** (Machines API) | 30–60 s | 30–55 s | 10–30 s |
| Per-second billing | ✅ | ❌ (per-hour) | ❌ (per-hour) | ❌ (per-hour) |
| Regions | 35+ worldwide | 30+ | 15 | 5 |
| Destroy on stop | native (Machines) | manual / API | manual / API | manual / API |
| Free tier | 3 shared VMs, 160 GB out | 750 h/mo (t2.micro) | — | — |

**Bottom line:** Fly Machines are **pay-per-second**, start in seconds, and auto-destroy — ideal for ephemeral workloads. No idle costs when the VPN is off.

### Cost estimate

| Usage | Fly.io cost |
|-------|-------------|
| 1 h/day, 30 days (shared-cpu-1x, 256 MB) | **~$0.50–1.00/mo** |
| 4 h/day, 30 days | ~$2–4/mo |
| Always-on equivalent (730 h) | ~$3.50/mo |

> Compare: a \$5/mo DigitalOcean droplet runs 24/7 whether you need it or not. Fly VPN runs **only when you click Launch**.

---

## Why Tailscale?

| Criteria | Tailscale | OpenVPN | WireGuard (raw) | Cloudflare WARP |
|----------|-----------|---------|-----------------|------------------|
| Setup complexity | Zero-config mesh | Certs + config files | Key exchange + routing | Managed (no self-host) |
| NAT traversal | ✅ built-in (DERP) | Manual / STUN | Manual | N/A |
| Exit node support | ✅ native | Manual iptables | Manual iptables | ❌ |
| Auto-approve nodes | ✅ via ACL tags | ❌ | ❌ | N/A |
| Ephemeral nodes | ✅ (auto-expire keys) | ❌ | ❌ | N/A |
| Protocol | WireGuard underneath | TLS / UDP | WireGuard | WireGuard (modified) |

**Bottom line:** Tailscale gives us **WireGuard performance** with zero manual key management. Ephemeral auth keys + ACL auto-approval = nodes that appear, serve traffic, and vanish — no cleanup.

---

## Approaches compared

| Approach | Spin-up | Monthly cost (casual) | Cleanup | Multi-region |
|----------|---------|----------------------|---------|-------------|
| **Fly VPN (this project)** | ~5 s | **<$1** | automatic | ✅ 35+ regions |
| Commercial VPN (Mullvad, PIA…) | instant | $5–10 | N/A | ✅ but shared IPs |
| Self-hosted WireGuard on VPS | 30–60 s | $5+ (always-on) | manual | one region per VPS |
| SSH SOCKS proxy | instant | $5+ (always-on VPS) | manual | one region per VPS |
| Outline VPN (Jigsaw) | 30–60 s | $5+ (always-on) | manual | one region per VPS |
| Cloud Functions + proxy | varies | pay-per-request | automatic | ✅ but complex |

**Fly VPN wins when you need:** your own IP (not shared), multi-region on demand, zero idle cost, and fully automated lifecycle.

---

## Fly VPN vs fly-tailscale-exit

[patte/fly-tailscale-exit](https://github.com/patte/fly-tailscale-exit) (1.6k ⭐) pioneered the idea of running Tailscale exit nodes on Fly.io. Fly VPN builds on the same concept but wraps it into a **ready-to-use product** instead of a DevOps guide.

| | fly-tailscale-exit | Fly VPN |
|---|---|---|
| Steps to start | **13** manual steps | **1** (`bash install.sh`) |
| GitHub org required | ✅ | ❌ |
| Fly org setup | Manual (`fly orgs create`) | Automatic |
| Deployment model | `fly deploy` (Dockerfile + fly.toml) | `fly m run` (no deploy, no repo) |
| Exit node approval | Manual in Tailscale admin | ACL auto-approve out of the box |
| Connect to exit node | `tailscale up --use-exit-node=…` | Automatic on launch |
| Switch region | `fly scale count` + manual cleanup | Pick from dropdown → Launch |
| Cleanup on stop | ❌ Machine keeps running (💸) | ✅ App + machine destroyed |
| UI | None (CLI only) | Textual TUI with hotkeys |
| Cost safety net | None | Watchdog (cron/launchd) |
| Headscale support | ❌ | ✅ (`TS_LOGIN_SERVER` env) |
| Instant device cleanup | ❌ | ✅ (Tailscale API key) |
| Desktop integration | None | macOS .app / GNOME menu |

> **Credit where due** — fly-tailscale-exit proved the idea works. Fly VPN just makes it one-click.

---

## Tailscale setup (required once)

### Auth key (required)

Create an auth key that is:
- **Reusable**
- **Ephemeral**
- Tagged with: `tag:ephemeral-vpn`

### API key (optional — instant cleanup)

By default, ephemeral Tailscale nodes auto-remove after ~5–30 minutes.
With a **TAILSCALE_API_KEY**, the node is deleted immediately on Stop.

Generate one at [Tailscale Admin → Keys → API keys](https://login.tailscale.com/admin/settings/keys).
Then add it to `.env`:

```env
TAILSCALE_API_KEY=tskey-api-…
```

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

## Self-hosted Tailscale (Headscale)

[Headscale](https://github.com/juanfont/headscale) is an open-source, self-hosted implementation of the Tailscale coordination server.
Fly VPN works with Headscale out of the box — just set the right env vars.

### 1. Set `TS_LOGIN_SERVER` in `.env`

The installer will ask if you use a self-hosted coordination server.
If you skipped it, add the variable manually:

```env
TS_LOGIN_SERVER=https://hs.example.com
```

The Fly exit node will register with your Headscale instance instead of `login.tailscale.com`.

### 2. Make sure your local client is on the same Headscale server

```bash
tailscale login --login-server=https://hs.example.com
```

Both the local machine and the Fly exit node must be on the **same** Headscale tailnet.

### 3. Create an auth key via Headscale

```bash
# Headscale CLI
headscale preauthkeys create --user your-user --reusable --ephemeral

# or via Headscale API
curl -X POST https://hs.example.com/api/v1/preauthkey \
  -H "Authorization: Bearer $HS_API_KEY" \
  -d '{"user":"your-user","reusable":true,"ephemeral":true}'
```

Put the key in `.env` as usual:

```env
TAILSCALE_AUTHKEY=your-headscale-preauth-key
```

### 4. ACL policy

Headscale ACLs live in the config file (typically `/etc/headscale/acl.yaml` or `acl.json`).
The same policy applies — allow the ephemeral tag and auto-approve exit nodes:

```yaml
# acl.yaml
tagOwners:
  tag:ephemeral-vpn:
    - your-user

autoApprovers:
  exitNode:
    - tag:ephemeral-vpn
```

### 5. Minimal `.env` for Headscale

```env
TAILSCALE_AUTHKEY=your-headscale-preauth-key
TS_LOGIN_SERVER=https://hs.example.com
```

> No `TAILSCALE_API_KEY` needed — Headscale removes ephemeral nodes immediately on disconnect.

### 6. Comparison

| Feature | Tailscale SaaS | Headscale |
|---------|---------------|-----------|
| Auth keys | Admin console | `headscale preauthkeys create` |
| ACL config | Web UI | Config file on server |
| Instant device cleanup (`TAILSCALE_API_KEY`) | ✅ Supported | ❌ Not compatible — not needed |
| Ephemeral node auto-remove | ~5–30 min | Immediate (on disconnect) |

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
- Tailscale device is removed instantly when API key is set (otherwise auto-removes in ~5–30 min)
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

## Uninstall

```bash
bash install.sh uninstall
```

---

## License

MIT
