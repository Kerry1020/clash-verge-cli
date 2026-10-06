# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-10-06

### Changed
- Refactored the two duplicated scripts into the `clash_verge_cli` package (`src/` layout) with
  automatic macOS / Linux / Windows detection. `clash_verge_cli.py` and `clash_verge_cli_windows.py`
  remain as thin launchers, so existing commands keep working.
- Packaging moved to `pyproject.toml`; installs a `clash-verge` console script. `setup.py` removed.
- `test` now measures latency through the Clash controller (`/proxies/{name}/delay`) and accepts `--url`.
- `select` now switches the proxy in the running core (`PUT /proxies/{group}`) and remembers the choice
  in `profiles.yaml`, instead of reordering the generated `clash-verge.yaml`.
- Errors are printed to stderr and exit with status 1 (invalid usage: 2).
- `webui`, `core`, `restart`, `path`, `open-dir`, `open-logs` are available on every platform.
- License metadata corrected to GPL-3.0.

### Added
- Global options `--config-dir`, `--controller`, `--secret`, `--timeout`, `--version`
  (env: `CLASH_VERGE_DIR`, `CLASH_API_URL`, `CLASH_API_SECRET`).
- Linux support and the current Clash Verge Rev Windows path (`%APPDATA%\io.github.clash-verge-rev.clash-verge-rev`).
- pytest suite with mocked HTTP and GitHub Actions CI (ubuntu / macOS / Windows, Python 3.9 & 3.12, ruff).

### Fixed
- `proxies` and `test` crashed because Clash stores `proxies` as a list.
- `test` built `ss://` / `vmess://` proxy URLs that `requests` cannot use, so every node showed "timeout".
- `health` used a hard-coded secret sent without the `Bearer` scheme and a fixed controller address;
  the controller address and secret are now read from `clash-verge.yaml`.
- `health` checked through `socks5://` which needs the optional PySocks dependency; it now uses the mixed port over HTTP.
- Proxy / group names with spaces, `/`, `#`, CJK or emoji are percent-encoded in API URLs.
- A friendly message (no traceback) when the controller is unreachable, times out or rejects the secret.
- Underscore command names documented in the README (`sysproxy_set`, `port_set`, `open_dir`) work again.
- Windows: no prompt at import time; no relative path when `%APPDATA%` is unset; emoji output no longer
  crashes on non-UTF-8 consoles; backups copy files byte-for-byte instead of using the locale encoding.
- Backup / restore reject names containing path separators (`../`).
- `delete` removes the profile's actual `file`; `add` creates `profiles/` if missing and avoids uid clashes.
- Config files are written atomically, keeping key order and file permissions.
- `guardian` runs with the current Python interpreter and reports a missing `minimax_guardian.py`.
- The config directory is no longer created as a side effect of read-only commands.

## [1.0.0] - 2026-03-16

### Added
- **Profile Management**: List, add, delete, activate profiles
- **Proxy Management**: List proxies, test latency, select proxies
- **System Proxy Control**: Enable/disable system proxy, TUN mode
- **Traffic Monitoring**: Real-time upload/download statistics
- **Guardian Mode**: Auto-monitor and heal when API fails
- **Backup & Restore**: Configuration backup system
- **Logs & Diagnostics**: Log viewing and search
- **Port Configuration**: HTTP/SOCKS/Mixed/Redir port management
- **JSON Output**: All commands support `--json` flag
- **Health Check**: Quick API connectivity check

### Features
- Click-based CLI with subcommands
- YAML configuration handling
- Multiple proxy group support
- Automatic node switching on latency threshold

## [0.9.0] - 2026-03-15

### Added
- Initial release
- Basic profile switching
- Proxy listing

## [0.5.0] - 2026-03-12

### Added
- Beta testing phase
