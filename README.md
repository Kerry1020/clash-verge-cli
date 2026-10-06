# Clash Verge CLI 🖥️

[![CI](https://github.com/Kerry1020/clash-verge-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Kerry1020/clash-verge-cli/actions/workflows/ci.yml)

Enhanced command-line interface for Clash Verge VPN client on macOS, Linux and Windows.

## Platforms

One code base for all platforms – the OS is detected automatically.

- **macOS / Linux / Windows**: `clash-verge` command (after `pip install .`)
- Legacy launchers still work: `clash_verge_cli.py` and `clash_verge_cli_windows.py`

## Overview

A comprehensive CLI tool to manage Clash Verge VPN client programmatically. Control proxies, profiles, system settings, monitor traffic, and more - all from terminal.

## Features

### 📋 Profile Management
- List, add, delete, and activate profiles
- Support for URL-based subscription profiles
- Quick profile switching by name or UID

### 🌐 Proxy Management
- List all proxies and proxy groups
- Test proxy latency (ping)
- Select specific proxy for any group
- Auto node optimization

### 🔌 System Proxy Control
- Enable/disable system proxy
- Toggle TUN mode
- View proxy guard status

### 📊 Traffic Monitoring
- Real-time upload/download statistics
- Display in human-readable format (GB)
- Traffic data per profile

### 🛡️ Guardian Mode
- Auto-monitor API connectivity
- Automatic node switching on timeout
- Configurable latency thresholds

### 💾 Backup & Restore
- One-click configuration backup
- Restore from previous backups
- Multiple backup slots

### 📝 Logs & Diagnostics
- View real-time logs
- Search logs by keyword
- Health check for APIs

### ⚙️ Advanced Configuration
- Port configuration (HTTP/SOCKS/Mixed/Redir)
- DNS settings display
- Routing rules inspection
- Direct config file editing

## Installation

**Requirements:**
- Python 3.8+
- click >= 8.0.0
- pyyaml >= 6.0
- requests >= 2.28.0

### Install as CLI (recommended, all platforms)

```bash
git clone https://github.com/Kerry1020/clash-verge-cli.git
cd clash-verge-cli
pip install .            # or: pipx install .

clash-verge --help
python -m clash_verge_cli --help   # equivalent
```

### Run without installing

```bash
pip install -r requirements.txt

# macOS / Linux
./clash_verge_cli.py --help

# Windows
python clash_verge_cli_windows.py --help
```

Symlinks keep working too:

```bash
sudo ln -s $(pwd)/clash_verge_cli.py /usr/local/bin/clash-verge
```

### Windows

**First Run**: the CLI auto-detects your Clash Verge installation. If it is not found and you are in an interactive terminal, it will prompt you to enter the config path manually. You can also pass `--config-dir` or set `CLASH_VERGE_DIR`.

Searched Windows paths:
```
%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\
%APPDATA%\clash-verge-rev\
%LOCALAPPDATA%\io.github.clash-verge-rev.clash-verge-rev\
%LOCALAPPDATA%\clash-verge-rev\
C:\Program Files\Clash Verge\
```

## Usage

### Quick Start

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

### Global Options

Global options go **before** the command, e.g. `clash-verge --timeout 10 test GLOBAL`.

| Option | Env variable | Description |
|--------|--------------|-------------|
| `--config-dir PATH` | `CLASH_VERGE_DIR` | Clash Verge config directory (auto-detected) |
| `--controller ADDR` | `CLASH_API_URL` | External controller, e.g. `127.0.0.1:9097` (default: `external-controller` from `clash-verge.yaml`) |
| `--secret TEXT` | `CLASH_API_SECRET` | Controller secret (default: `secret` from `clash-verge.yaml`) |
| `--timeout SEC` | | Network timeout, default 5s |
| `-V, --version` | | Show version |

### Command Reference

| Command | Description |
|---------|-------------|
| `status` | Show comprehensive status |
| `profiles` | List all profiles |
| `activate <name>` | Switch to profile |
| `add <url>` | Add profile from URL |
| `delete <name>` | Delete profile |
| `proxies` | List all proxies |
| `test <group>` | Test latency for group |
| `select <group> <proxy>` | Select proxy |
| `sysproxy` | Show system proxy status |
| `sysproxy-set on/off/toggle` | Control system proxy (`sysproxy_set` also works) |
| `tun on/off/toggle` | Control TUN mode |
| `ports` | Show port configuration |
| `port-set <type> <port>` | Set port (`port_set` also works) |
| `dns` | Show DNS configuration |
| `rules` | Show routing rules |
| `traffic` | Show traffic stats |
| `backup` | Create backup |
| `backups` | List backups |
| `restore <name>` | Restore backup |
| `logs` | Show logs |
| `loggrep <keyword>` | Search logs |
| `guardian` | Auto-heal mode |
| `health` | Quick health check |
| `restart` | Restart Clash Verge |
| `open-dir` / `open-logs` | Open config / logs folder |
| `config` | Show Clash config |
| `vergecfg` | Show Verge config |
| `webui` | Show Web UI list |
| `core` | Show Clash core |
| `path` | Show detected config directory |
| `set <key> <value>` | Set a `verge.yaml` key (experimental) |
| `refresh` | Touch `profiles.yaml` to trigger a reload |

> `test`, `select` and `health` talk to the running Clash core through its external controller (REST API), so Clash Verge must be running. The secret is read from `clash-verge.yaml` and sent as `Authorization: Bearer <secret>`.
>
> `sysproxy-set`, `tun`, `port-set`, `activate` and `set` edit Clash Verge's config files; changes are picked up when Clash Verge reloads (use `restart` if needed).

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (not found, controller unreachable, health check failed, ...) – message on stderr |
| `2` | Invalid usage / arguments |

### JSON Output

All listing commands support `--json` flag for programmatic use:

```bash
clash-verge status --json
clash-verge proxies --json
clash-verge traffic --json
```

### Guardian Mode

Auto-monitor and heal when API fails. Requires the external `minimax_guardian.py` script, placed next to the CLI, in the current directory, or pointed to by `CLASH_VERGE_GUARDIAN`:

```bash
# Run once
clash-verge guardian --once

# Run continuously (default 120s interval)
clash-verge guardian

# Custom interval and latency threshold
clash-verge guardian --interval 60 --max-latency 2000
```

## Configuration

Default config directory:
```
macOS:   ~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/
Linux:   ~/.local/share/io.github.clash-verge-rev.clash-verge-rev/
Windows: %APPDATA%\io.github.clash-verge-rev.clash-verge-rev\
```

Key files:
- `profiles.yaml` - Profile management
- `verge.yaml` - Verge settings
- `clash-verge.yaml` - Clash core config

## Examples

### Daily Usage

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

Project layout:

```
src/clash_verge_cli/
  commands.py   # click commands + entry point
  api.py        # mihomo external-controller client
  store.py      # profiles.yaml / verge.yaml / backups / logs
  platforms.py  # macOS / Linux / Windows paths and helpers
  output.py     # JSON / text output helpers
tests/
```

## License

GPL-3.0 – see [LICENSE](LICENSE).

## Author

Clash Verge CLI - Enhanced Edition
