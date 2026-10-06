# Clash Verge CLI 🖥️

[![CI](https://github.com/Kerry1020/clash-verge-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Kerry1020/clash-verge-cli/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

English | [简体中文](README.zh-CN.md)

Command-line interface for the Clash Verge (Rev) / mihomo VPN client on macOS, Linux and Windows: control proxies, profiles, system proxy / TUN, ports, backups and logs from the terminal.

One code base for all platforms – the OS and the Clash Verge config directory are detected automatically.

## Features

### 📋 Profile Management
- List, add, delete and activate profiles
- URL-based subscription profiles
- Switch profiles by name or UID

### 🌐 Proxy Management
- List all proxies and proxy groups (optionally filtered by group)
- Test latency of a group's nodes through the running Clash core
- Select a proxy for any group (applied live and remembered in `profiles.yaml`)

### 🔌 System Proxy Control
- Enable / disable / toggle the system proxy
- Enable / disable / toggle TUN mode
- View proxy guard status

### 📊 Traffic
- Upload / download / total usage of the active subscription profile, in GB

### 🛡️ Guardian Mode
- Runs an external `minimax_guardian.py` script that monitors API connectivity and switches nodes on timeout
- Configurable interval and latency threshold

### 💾 Backup & Restore
- One-command backup of the config files, optionally named
- List and restore previous backups

### 📝 Logs & Diagnostics
- Show the latest log lines and search logs by keyword
- Quick health check (Clash controller + an HTTPS request through the local proxy)

### ⚙️ Advanced Configuration
- Port configuration (HTTP / SOCKS / Mixed / Redir)
- DNS settings and routing rules display
- Set `verge.yaml` keys directly (experimental)

## Quick start

Requirements: Python 3.8+ (dependencies: `click>=8`, `pyyaml>=6`, `requests>=2.28`, installed automatically).

### Install as CLI (recommended, all platforms)

```bash
git clone https://github.com/Kerry1020/clash-verge-cli.git
cd clash-verge-cli
pip install .            # or: pipx install .

clash-verge --help
python -m clash_verge_cli --help   # equivalent
```

`pip install .` provides the `clash-verge` console script (entry point `clash_verge_cli.commands:main`).

### Run without installing

The legacy scripts are kept as thin launchers for the same package (`src/clash_verge_cli`), so existing commands and symlinks keep working:

```bash
pip install -r requirements.txt

# macOS / Linux
./clash_verge_cli.py --help

# Windows (both launchers are identical; platform is auto-detected)
python clash_verge_cli_windows.py --help
python clash_verge_cli.py --help
```

Symlinks keep working too:

```bash
sudo ln -s $(pwd)/clash_verge_cli.py /usr/local/bin/clash-verge
```

### First steps

```bash
# Show status
clash-verge status

# List profiles
clash-verge profiles

# Activate profile
clash-verge activate "my-profile"

# Test proxy latency (names with spaces / emoji / CJK are fine)
clash-verge test "🚀 节点选择"
```

## Usage

### Global options

Global options go **before** the command, e.g. `clash-verge --timeout 10 test GLOBAL`.

| Option | Env variable | Description |
|--------|--------------|-------------|
| `--config-dir PATH` | `CLASH_VERGE_DIR` | Clash Verge config directory (auto-detected) |
| `--controller ADDR` | `CLASH_API_URL` | External controller, e.g. `127.0.0.1:9097` (default: `external-controller` from `clash-verge.yaml`) |
| `--secret TEXT` | `CLASH_API_SECRET` | Controller secret (default: `secret` from `clash-verge.yaml`) |
| `--timeout SEC` | | Network timeout in seconds, default `5` (minimum `0.1`) |
| `-V, --version` | | Show version |
| `-h, --help` | | Show help |

### Command reference

| Command | Options | Description |
|---------|---------|-------------|
| `status` | `--json` | Show comprehensive status |
| `profiles` | `--json` | List all profiles |
| `activate <name>` | | Switch to profile (name or UID) |
| `add <url>` | `--name TEXT` | Add profile from URL |
| `delete <name>` | | Delete profile |
| `proxies` | `--json`, `--group TEXT` | List all proxies |
| `test <group>` | `--limit N` (5), `--url URL`, `--json` | Test latency for group |
| `select <group> <proxy>` | | Select proxy |
| `sysproxy` | `--json` | Show system proxy status |
| `sysproxy-set on/off/toggle` | | Control system proxy (`sysproxy_set` also works) |
| `tun on/off/toggle` | | Control TUN mode |
| `ports` | `--json` | Show port configuration |
| `port-set <http/socks/mixed/redir> <port>` | `--enable/--disable` | Set port (`port_set` also works) |
| `dns` | `--json` | Show DNS configuration |
| `rules` | `--json`, `--type TEXT`, `--limit N` (20) | Show routing rules |
| `traffic` | `--json` | Show traffic stats |
| `backup [name]` | | Create backup |
| `backups` | `--json` | List backups |
| `restore <name>` | | Restore backup |
| `logs` | `--lines N` (50), `--json` | Show logs |
| `loggrep <keyword>` | `--lines N` (100) | Search logs |
| `guardian` | `--once`, `--interval SEC` (120), `--max-latency MS` (3000) | Auto-heal mode |
| `health` | | Quick health check |
| `restart` | | Restart Clash Verge |
| `open-dir` / `open-logs` | | Open config / logs folder (`open_dir` / `open_logs` also work) |
| `config` | `--json` | Show Clash config |
| `vergecfg` | `--json` | Show Verge config |
| `webui` | `--json` | Show Web UI list |
| `core` | | Show Clash core |
| `path` | | Show detected config directory |
| `set <key> <value>` | | Set a `verge.yaml` key (experimental) |
| `refresh` | | Touch `profiles.yaml` to trigger a reload |

> `test`, `select` and `health` talk to the running Clash core through its external controller (REST API), so Clash Verge must be running. The secret is read from `clash-verge.yaml` and sent as `Authorization: Bearer <secret>`. `test` uses `default_latency_test` from `verge.yaml` as the test URL, falling back to `https://www.gstatic.com/generate_204`.
>
> `sysproxy-set`, `tun`, `port-set`, `activate` and `set` edit Clash Verge's config files; changes are picked up when Clash Verge reloads (use `restart` if needed).
>
> `health` checks the controller, then sends an HTTPS request to `https://api.minimax.io/anthropic` through the local mixed port (default `7897`) and exits with `1` if either fails.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (not found, controller unreachable, health check failed, ...) – message on stderr |
| `2` | Invalid usage / arguments |

### JSON output

Commands marked `--json` above print machine-readable output:

```bash
clash-verge status --json
clash-verge proxies --json
clash-verge traffic --json
```

### Guardian mode

Auto-monitor and heal when the API fails. Requires the external `minimax_guardian.py` script (not included), placed next to the CLI, in the current directory, or pointed to by `CLASH_VERGE_GUARDIAN`:

```bash
# Run once
clash-verge guardian --once

# Run continuously (default 120s interval)
clash-verge guardian

# Custom interval and latency threshold
clash-verge guardian --interval 60 --max-latency 2000
```

## Configuration

### Environment variables

| Name | Required | Secret | Default | Description |
|---|---|---|---|---|
| `CLASH_VERGE_DIR` | no | no | auto-detected | Config directory (same as `--config-dir`) |
| `CLASH_API_URL` | no | no | `external-controller` in `clash-verge.yaml`, else `127.0.0.1:9097` | Controller address (same as `--controller`) |
| `CLASH_API_SECRET` | no | yes | `secret` in `clash-verge.yaml` | Controller secret (same as `--secret`) |
| `CLASH_VERGE_GUARDIAN` | no | no | — | Path to `minimax_guardian.py` for `guardian` |

### Config directory

Resolution order: `--config-dir` > `CLASH_VERGE_DIR` > first existing known location > platform default.

```
macOS:   ~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/
Linux:   ~/.local/share/io.github.clash-verge-rev.clash-verge-rev/   ($XDG_DATA_HOME)
         ~/.config/io.github.clash-verge-rev.clash-verge-rev/        ($XDG_CONFIG_HOME)
         ~/.config/clash-verge/
Windows: %APPDATA%\io.github.clash-verge-rev.clash-verge-rev\
         %APPDATA%\clash-verge-rev\
         %LOCALAPPDATA%\io.github.clash-verge-rev.clash-verge-rev\
         %LOCALAPPDATA%\clash-verge-rev\
         C:\Program Files\Clash Verge\
         C:\Program Files (x86)\Clash Verge\
```

**Windows first run:** if no installation is found and you are in an interactive terminal, the CLI prompts for the config path. You can also pass `--config-dir` or set `CLASH_VERGE_DIR`.

Key files:
- `profiles.yaml` - Profile management
- `verge.yaml` - Verge settings
- `clash-verge.yaml` - Clash core config (controller address and secret)

Backups are stored in `clash-verge-rev-backup/` inside the config directory.

## Examples

### Daily usage

```bash
# Morning health check
clash-verge health

# Switch to fastest node
clash-verge test GLOBAL --limit 10
clash-verge select GLOBAL "德国hy2-5-三网优化"

# Check traffic
clash-verge traffic

# Create backup before changes
clash-verge backup
```

### Automation

```bash
# Cron job for health check
*/5 * * * * /usr/local/bin/clash-verge health >> /var/log/clash.log 2>&1

# Auto-switch on failure (via guardian)
clash-verge guardian --interval 300
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest          # tests (HTTP is mocked, your real config is never touched)
ruff check .    # lint
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

Project layout:

```
src/clash_verge_cli/
  commands.py   # click commands + entry point
  api.py        # mihomo external-controller client
  store.py      # profiles.yaml / verge.yaml / backups / logs
  platforms.py  # macOS / Linux / Windows paths and helpers
  output.py     # JSON / text output helpers
clash_verge_cli.py, clash_verge_cli_windows.py   # legacy launchers
tests/
```

## License

GPL-3.0 – see [LICENSE](LICENSE).
