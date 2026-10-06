"""Access to Clash Verge's on-disk configuration (profiles.yaml, verge.yaml, ...)."""

import os
import re
import shutil
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from clash_verge_cli.api import DEFAULT_CONTROLLER

BACKUP_FILES = ("profiles.yaml", "verge.yaml", "clash-verge.yaml")

PORT_MAPPING = {
    "http": ("verge_port", "verge_http_enabled"),
    "socks": ("verge_socks_port", "verge_socks_enabled"),
    "mixed": ("verge_mixed_port", None),
    "redir": ("verge_redir_port", "verge_redir_enabled"),
}

_SAFE_NAME = re.compile(r"^[^/\\:*?\"<>|\x00-\x1f]+$")


def load_yaml(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _target_mode(file_path: Path) -> int:
    """Permissions for the rewritten file: keep the existing ones, else 0666 & ~umask."""
    try:
        return stat.S_IMODE(file_path.stat().st_mode)
    except OSError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o666 & ~umask


def save_yaml(file_path: Path, data: Dict[str, Any]) -> None:
    """Write YAML atomically (temp file + replace) keeping key order and file mode."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    mode = _target_mode(file_path)
    fd, tmp = tempfile.mkstemp(dir=str(file_path.parent), prefix=".tmp-", suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1 << 16
            )
        os.chmod(tmp, mode)
        os.replace(tmp, str(file_path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def is_safe_name(name: str) -> bool:
    """A backup name must be a single, plain path component."""
    return bool(name) and name not in (".", "..") and bool(_SAFE_NAME.match(name))


def proxies_by_name(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Clash configs store ``proxies`` as a *list*; index it by name.

    The original scripts called ``.items()`` / ``.get()`` on it and crashed.
    """
    if isinstance(raw, dict):
        return raw
    result: Dict[str, Dict[str, Any]] = {}
    for item in raw or []:
        if isinstance(item, dict) and item.get("name") is not None:
            result[str(item["name"])] = item
    return result


def parse_scalar(value: str) -> Any:
    """Parse a CLI value for ``set``: true/false, integers, else string."""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


class ClashVergeCLI:
    """File based view of a Clash Verge installation."""

    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.profiles_dir = self.config_dir / "profiles"
        self.profiles_yaml = self.config_dir / "profiles.yaml"
        self.verge_config = self.config_dir / "verge.yaml"
        self.clash_config = self.config_dir / "clash-verge.yaml"
        self.backup_dir = self.config_dir / "clash-verge-rev-backup"
        self.logs_dir = self.config_dir / "logs"

    load_yaml = staticmethod(load_yaml)
    save_yaml = staticmethod(save_yaml)

    # ---- profiles --------------------------------------------------------

    def get_profiles(self) -> List[Dict[str, Any]]:
        data = load_yaml(self.profiles_yaml)
        current_uid = data.get("current")
        profiles = []
        for item in data.get("items") or []:
            if not isinstance(item, dict):
                continue
            item["is_current"] = item.get("uid") == current_uid
            profiles.append(item)
        return profiles

    def get_current_profile(self) -> Optional[Dict[str, Any]]:
        for item in self.get_profiles():
            if item["is_current"]:
                return item
        return None

    def find_profile(self, name: str, match_file: bool = True) -> Optional[Dict[str, Any]]:
        for p in self.get_profiles():
            stem = re.sub(r"\.(yaml|yml|js)$", "", p.get("file") or "")
            if p.get("name") == name or p.get("uid") == name or (match_file and stem and stem == name):
                return p
        return None

    def activate_profile(self, uid: str) -> None:
        data = load_yaml(self.profiles_yaml)
        data["current"] = uid
        save_yaml(self.profiles_yaml, data)
        verge = self.get_verge_config()
        verge["current_profile"] = uid
        self.save_verge_config(verge)

    def add_profile(self, url: str, content: str, name: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now()
        name = name or now.strftime("profile_%Y%m%d%H%M%S")
        existing = {p.get("uid") for p in self.get_profiles()}
        uid = "url_{}".format(int(now.timestamp()))
        suffix = 1
        while uid in existing:
            uid = "url_{}_{}".format(int(now.timestamp()), suffix)
            suffix += 1
        file_name = "{}.yaml".format(uid)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        (self.profiles_dir / file_name).write_text(content, encoding="utf-8")

        data = load_yaml(self.profiles_yaml)
        item = {"uid": uid, "name": name, "type": "url", "url": url, "file": file_name}
        data.setdefault("items", [])
        if data["items"] is None:
            data["items"] = []
        data["items"].append(item)
        save_yaml(self.profiles_yaml, data)
        return item

    def delete_profile(self, profile: Dict[str, Any]) -> None:
        uid = profile.get("uid")
        data = load_yaml(self.profiles_yaml)
        data["items"] = [p for p in data.get("items") or [] if p.get("uid") != uid]
        save_yaml(self.profiles_yaml, data)
        file_name = profile.get("file") or "{}.yaml".format(uid)
        profile_file = self.profiles_dir / Path(file_name).name
        if profile_file.exists():
            profile_file.unlink()

    def remember_selection(self, group: str, proxy: str) -> bool:
        """Persist a group selection in the current profile (like the GUI does)."""
        data = load_yaml(self.profiles_yaml)
        current_uid = data.get("current")
        for item in data.get("items") or []:
            if isinstance(item, dict) and item.get("uid") == current_uid:
                selected = item.get("selected") or []
                for sel in selected:
                    if sel.get("name") == group:
                        sel["now"] = proxy
                        break
                else:
                    selected.append({"name": group, "now": proxy})
                item["selected"] = selected
                save_yaml(self.profiles_yaml, data)
                return True
        return False

    # ---- configs ---------------------------------------------------------

    def get_clash_config(self) -> Dict[str, Any]:
        return load_yaml(self.clash_config)

    def get_verge_config(self) -> Dict[str, Any]:
        return load_yaml(self.verge_config)

    def save_verge_config(self, config: Dict[str, Any]) -> None:
        save_yaml(self.verge_config, config)

    def get_proxies(self) -> Dict[str, Dict[str, Any]]:
        return proxies_by_name(self.get_clash_config().get("proxies"))

    def get_proxy_groups(self) -> List[Dict[str, Any]]:
        return [g for g in self.get_clash_config().get("proxy-groups") or [] if isinstance(g, dict)]

    def get_controller(self) -> Tuple[str, Optional[str]]:
        """(external-controller address, secret) from the generated config."""
        clash = self.get_clash_config()
        verge = self.get_verge_config()
        address = clash.get("external-controller") or DEFAULT_CONTROLLER
        secret = clash.get("secret")
        if secret is None:
            secret = (verge.get("clash_info") or {}).get("secret")
        return str(address), (str(secret) if secret else None)

    def get_system_proxy_status(self) -> Dict[str, Any]:
        verge = self.get_verge_config()
        return {
            "system_proxy": verge.get("enable_system_proxy", False),
            "tun_mode": verge.get("enable_tun_mode", False),
            "proxy_guard": verge.get("enable_proxy_guard", False),
        }

    def _set_flag(self, key: str, enabled: bool) -> bool:
        verge = self.get_verge_config()
        verge[key] = enabled
        self.save_verge_config(verge)
        return enabled

    def set_system_proxy(self, enabled: bool) -> bool:
        return self._set_flag("enable_system_proxy", enabled)

    def set_tun_mode(self, enabled: bool) -> bool:
        return self._set_flag("enable_tun_mode", enabled)

    def get_dns_config(self) -> Dict[str, Any]:
        return self.get_clash_config().get("dns") or {}

    def get_rules(self) -> List[Dict[str, str]]:
        result = []
        for rule in self.get_clash_config().get("rules") or []:
            if isinstance(rule, str):
                parts = rule.split(",")
                result.append({
                    "type": parts[0].strip() if parts else "UNKNOWN",
                    "value": parts[1].strip() if len(parts) > 1 else "",
                    "payload": ",".join(parts[2:]).strip() if len(parts) > 2 else "",
                })
        return result

    def get_traffic_stats(self) -> Dict[str, Any]:
        current = self.get_current_profile()
        if not current:
            return {}
        extra = current.get("extra") or {}
        up, down, total = (int(extra.get(k) or 0) for k in ("upload", "download", "total"))
        gb = 1024 ** 3
        return {
            "upload": up,
            "download": down,
            "total": total,
            "upload_gb": round(up / gb, 2),
            "download_gb": round(down / gb, 2),
            "total_gb": round(total / gb, 2),
        }

    def get_web_ui_list(self) -> List[Any]:
        return self.get_verge_config().get("web_ui_list") or []

    def get_ports(self) -> Dict[str, Any]:
        verge = self.get_verge_config()
        return {
            "http_port": verge.get("verge_port"),
            "socks_port": verge.get("verge_socks_port"),
            "mixed_port": verge.get("verge_mixed_port"),
            "redir_port": verge.get("verge_redir_port"),
            "enable_http": verge.get("verge_http_enabled"),
            "enable_socks": verge.get("verge_socks_enabled"),
            "enable_redir": verge.get("verge_redir_enabled"),
        }

    def set_port(self, port_type: str, port: int, enabled: Optional[bool] = None) -> Dict[str, Any]:
        if port_type not in PORT_MAPPING:
            return {"error": "Unknown port type: {}".format(port_type)}
        verge = self.get_verge_config()
        port_key, enable_key = PORT_MAPPING[port_type]
        verge[port_key] = port
        if enabled is not None and enable_key:
            verge[enable_key] = enabled
        self.save_verge_config(verge)
        return self.get_ports()

    # ---- backups ---------------------------------------------------------

    def create_backup(self, name: Optional[str] = None) -> str:
        name = name or datetime.now().strftime("%Y%m%d_%H%M%S")
        if not is_safe_name(name):
            raise ValueError("Invalid backup name: {}".format(name))
        backup_path = self.backup_dir / name
        backup_path.mkdir(parents=True, exist_ok=True)
        for file in BACKUP_FILES:
            src = self.config_dir / file
            if src.exists():
                shutil.copy2(str(src), str(backup_path / file))
        return str(backup_path)

    def list_backups(self) -> List[Dict[str, str]]:
        if not self.backup_dir.is_dir():
            return []
        backups = []
        for item in sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if item.is_dir():
                backups.append({
                    "name": item.name,
                    "path": str(item),
                    "created": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
        return backups

    def restore_backup(self, name: str) -> bool:
        if not is_safe_name(name):
            return False
        backup_path = self.backup_dir / name
        if not backup_path.is_dir():
            return False
        for file in BACKUP_FILES:
            src = backup_path / file
            if src.exists():
                shutil.copy2(str(src), str(self.config_dir / file))
        return True

    # ---- logs ------------------------------------------------------------

    def get_logs(self, lines: int = 50) -> List[str]:
        if not self.logs_dir.is_dir():
            return []
        log_files = list(self.logs_dir.glob("*.log"))
        if not log_files or lines <= 0:
            return []
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_log, encoding="utf-8", errors="replace") as f:
                return f.readlines()[-lines:]
        except OSError:
            return []
