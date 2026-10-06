"""Platform detection and per-platform paths / helpers.

Everything that differs between macOS, Linux and Windows lives here so the
rest of the code base can stay platform agnostic.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

APP_ID = "io.github.clash-verge-rev.clash-verge-rev"
CONFIG_DIR_ENV = "CLASH_VERGE_DIR"

MACOS = "macos"
LINUX = "linux"
WINDOWS = "windows"


def detect_platform(platform: Optional[str] = None) -> str:
    """Return one of ``macos``, ``linux`` or ``windows``."""
    platform = platform or sys.platform
    if platform.startswith("win") or platform == "cygwin":
        return WINDOWS
    if platform == "darwin":
        return MACOS
    return LINUX


def _env_path(environ: Dict[str, str], key: str) -> Optional[Path]:
    """Return ``Path(environ[key])`` or None when the variable is unset/empty.

    The old Windows script used ``Path(os.environ.get('APPDATA', ''))`` which
    silently turned into a path relative to the current directory when the
    variable was missing.
    """
    value = environ.get(key)
    if not value:
        return None
    return Path(value)


def candidate_config_dirs(
    platform: Optional[str] = None,
    environ: Optional[Dict[str, str]] = None,
    home: Optional[Path] = None,
) -> List[Path]:
    """Known Clash Verge config directories for a platform, most likely first."""
    platform = detect_platform(platform)
    environ = dict(os.environ) if environ is None else environ
    home = Path.home() if home is None else home
    candidates: List[Path] = []

    if platform == MACOS:
        candidates.append(home / "Library" / "Application Support" / APP_ID)
    elif platform == WINDOWS:
        appdata = _env_path(environ, "APPDATA") or home / "AppData" / "Roaming"
        localappdata = _env_path(environ, "LOCALAPPDATA") or home / "AppData" / "Local"
        candidates.extend([
            appdata / APP_ID,
            appdata / "clash-verge-rev",
            localappdata / APP_ID,
            localappdata / "clash-verge-rev",
            Path("C:/Program Files/Clash Verge"),
            Path("C:/Program Files (x86)/Clash Verge"),
        ])
    else:
        data_home = _env_path(environ, "XDG_DATA_HOME") or home / ".local" / "share"
        config_home = _env_path(environ, "XDG_CONFIG_HOME") or home / ".config"
        candidates.extend([
            data_home / APP_ID,
            config_home / APP_ID,
            config_home / "clash-verge",
        ])
    return candidates


def resolve_config_dir(
    explicit: Optional[str] = None,
    platform: Optional[str] = None,
    environ: Optional[Dict[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    """Pick the config directory.

    Order: explicit value (``--config-dir``) > ``$CLASH_VERGE_DIR`` > first
    existing known location > platform default (first candidate).
    """
    environ = dict(os.environ) if environ is None else environ
    if explicit:
        return Path(explicit).expanduser()
    env_dir = environ.get(CONFIG_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser()
    candidates = candidate_config_dirs(platform, environ, home)
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]


def open_path(path: Path, platform: Optional[str] = None) -> None:
    """Open a directory in the platform file manager."""
    platform = detect_platform(platform)
    if platform == WINDOWS:
        os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
    elif platform == MACOS:
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def app_executable(platform: Optional[str] = None, environ: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Locate the Clash Verge GUI executable, or None."""
    platform = detect_platform(platform)
    environ = dict(os.environ) if environ is None else environ
    if platform == MACOS:
        candidates = [Path("/Applications/Clash Verge.app/Contents/MacOS/clash-verge")]
    elif platform == WINDOWS:
        candidates = []
        local = _env_path(environ, "LOCALAPPDATA")
        if local:
            candidates.append(local / "Programs" / "Clash Verge" / "clash-verge.exe")
        candidates += [
            Path("C:/Program Files/Clash Verge/clash-verge.exe"),
            Path("C:/Program Files (x86)/Clash Verge/clash-verge.exe"),
        ]
    else:
        found = shutil.which("clash-verge")
        candidates = [Path(found)] if found else [Path("/usr/bin/clash-verge")]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def stop_app(platform: Optional[str] = None) -> None:
    """Best effort: terminate a running Clash Verge GUI."""
    platform = detect_platform(platform)
    try:
        if platform == WINDOWS:
            for image in ("clash-verge.exe", "Clash Verge.exe"):
                subprocess.run(
                    ["taskkill", "/F", "/IM", image],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        elif platform == MACOS:
            subprocess.run(["pkill", "-f", "Clash Verge"], check=False)
        else:
            subprocess.run(["pkill", "-x", "clash-verge"], check=False)
    except OSError:
        pass
    time.sleep(1)


def start_app(executable: str) -> None:
    subprocess.Popen([executable])  # noqa: S603
