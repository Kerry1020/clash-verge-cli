# Clash Verge CLI 🖥️

Enhanced command-line interface for Clash Verge VPN client on macOS and Windows.

## Platforms

- **macOS**: `clash_verge_cli.py`
- **Windows**: `clash_verge_cli_windows.py`

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

### Windows

```powershell
# Install Python dependencies
pip install -r requirements.txt

# Run directly
python clash_verge_cli_windows.py --help
```

**First Run**: On first run, the Windows version will auto-detect your Clash Verge installation. If not found, it will prompt you to enter the config path manually.

Default Windows paths:
```
%APPDATA%\clash-verge-rev\
%LOCALAPPDATA%\clash-verge-rev\
C:\Program Files\Clash Verge\
```

### macOS

```bash
# Install Python dependencies
pip install -r requirements.txt
```

**Requirements:**
- Python 3.8+
- click >= 8.0.0
- pyyaml >= 6.0
- requests >= 2.28.0

### Install as CLI

```bash
# Make executable
chmod +x clash_verge_cli.py

# Option 1: Run directly
./clash_verge_cli.py --help

# Option 2: Add to PATH
sudo ln -s $(pwd)/clash_verge_cli.py /usr/local/bin/clash-verge
clash-verge --help
```

## Usage

### Quick Start

```bash
# Show status
python clash_verge_cli.py status

# List profiles
python clash_verge_cli.py profiles

# Activate profile
python clash_verge_cli.py activate "my-profile"

# Test proxy latency
python clash_verge_cli.py test "GLOBAL"
```

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
| `sysproxy_set on/off/toggle` | Control system proxy |
| `tun on/off/toggle` | Control TUN mode |
| `ports` | Show port configuration |
| `port_set <type> <port>` | Set port |
| `traffic` | Show traffic stats |
| `backup` | Create backup |
| `backups` | List backups |
| `restore <name>` | Restore backup |
| `logs` | Show logs |
| `loggrep <keyword>` | Search logs |
| `guardian` | Auto-heal mode |
| `health` | Quick health check |
| `restart` | Restart Clash Verge |
| `open_dir` | Open config folder |
| `config` | Show Clash config |
| `vergecfg` | Show Verge config |

### JSON Output

All commands support `--json` flag for programmatic use:

```bash
python clash_verge_cli.py status --json
python clash_verge_cli.py proxies --json
python clash_verge_cli.py traffic --json
```

### Guardian Mode

Auto-monitor and heal when API fails:

```bash
# Run once
python clash_verge_cli.py guardian --once

# Run continuously (default 120s interval)
python clash_verge_cli.py guardian

# Custom interval and latency threshold
python clash_verge_cli.py guardian --interval 60 --max-latency 2000
```

## Configuration

Default config directory:
```
~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/
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

## License

MIT License

## Author

Clash Verge CLI - Enhanced Edition
