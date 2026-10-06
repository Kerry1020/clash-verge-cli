"""Click command definitions and the console entry point."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests

from clash_verge_cli import __version__, platforms
from clash_verge_cli.api import DEFAULT_DELAY_URL, DEFAULT_TIMEOUT, ClashAPI, ControllerError
from clash_verge_cli.output import (
    configure_console,
    echo_json,
    echo_yaml,
    fail,
    on_off,
    success,
)
from clash_verge_cli.store import ClashVergeCLI, parse_scalar

SKIP_IN_LATENCY_TEST = ("DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE", "fallback", "url-test")
HEALTH_CHECK_URL = "https://api.minimax.io/anthropic"
DEFAULT_MIXED_PORT = 7897


class State:
    """Lazily built per-invocation objects (config store + API client)."""

    def __init__(
        self,
        config_dir: Optional[str] = None,
        controller: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._config_dir_opt = config_dir
        self._controller_opt = controller
        self._secret_opt = secret
        self.timeout = timeout
        self._client: Optional[ClashVergeCLI] = None
        self._api: Optional[ClashAPI] = None

    @property
    def platform(self) -> str:
        return platforms.detect_platform()

    def _resolve_config_dir(self) -> Path:
        path = platforms.resolve_config_dir(self._config_dir_opt)
        explicit = self._config_dir_opt or os.environ.get(platforms.CONFIG_DIR_ENV)
        if not explicit and not path.is_dir() and self.platform == platforms.WINDOWS and sys.stdin.isatty():
            # Behaviour of the original Windows edition: ask the user.
            click.echo("⚠️  Clash Verge not found in default location.", err=True)
            click.echo("Default: {}".format(path), err=True)
            path = Path(click.prompt("Please enter Clash Verge config path", type=str)).expanduser()
        return path

    @property
    def client(self) -> ClashVergeCLI:
        if self._client is None:
            self._client = ClashVergeCLI(self._resolve_config_dir())
        return self._client

    @property
    def api(self) -> ClashAPI:
        if self._api is None:
            controller, secret = self._controller_opt, self._secret_opt
            if not controller or secret is None:
                cfg_controller, cfg_secret = self.client.get_controller()
                controller = controller or cfg_controller
                secret = cfg_secret if secret is None else secret
            self._api = ClashAPI(controller, secret, timeout=self.timeout)
        return self._api


class AliasedGroup(click.Group):
    """Accept ``port_set`` as well as ``port-set``.

    Click >= 7 turns ``def port_set`` into the command ``port-set``, so the
    underscore names documented in the README never actually worked.
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        command = super().get_command(ctx, cmd_name)
        if command is None:
            command = super().get_command(ctx, cmd_name.replace("_", "-"))
        return command

    def resolve_command(self, ctx: click.Context, args: List[str]):  # type: ignore[override]
        _, command, rest = super().resolve_command(ctx, args)
        return (command.name if command else None), command, rest


pass_state = click.make_pass_decorator(State)
json_option = click.option("--json", "as_json", is_flag=True, help="Output as JSON")


@click.group(cls=AliasedGroup, invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config-dir",
    envvar="CLASH_VERGE_DIR",
    type=click.Path(file_okay=False),
    help="Clash Verge config directory (env: CLASH_VERGE_DIR). Auto-detected by default.",
)
@click.option(
    "--controller",
    envvar="CLASH_API_URL",
    help="External controller address, e.g. 127.0.0.1:9097 (env: CLASH_API_URL). "
    "Defaults to external-controller in clash-verge.yaml.",
)
@click.option(
    "--secret",
    envvar="CLASH_API_SECRET",
    help="External controller secret (env: CLASH_API_SECRET). Defaults to secret in clash-verge.yaml.",
)
@click.option(
    "--timeout",
    type=click.FloatRange(min=0.1),
    default=DEFAULT_TIMEOUT,
    show_default=True,
    help="Network timeout in seconds.",
)
@click.version_option(__version__, "-V", "--version", prog_name="clash-verge")
@click.pass_context
def cli(ctx: click.Context, config_dir: Optional[str], controller: Optional[str], secret: Optional[str],
        timeout: float) -> None:
    """Clash Verge CLI - Comprehensive command line interface for Clash Verge"""
    ctx.obj = State(config_dir, controller, secret, timeout)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ============== STATUS COMMANDS ==============

@cli.command()
@json_option
@pass_state
def status(state: State, as_json: bool) -> None:
    """Show comprehensive status"""
    client = state.client
    current = client.get_current_profile()
    traffic = client.get_traffic_stats()
    sys_proxy = client.get_system_proxy_status()
    ports = client.get_ports()
    profiles_count = len(client.get_profiles())

    if as_json:
        result: Dict[str, Any] = {
            "config_dir": str(client.config_dir),
            "profiles_count": profiles_count,
            "current_profile": None,
            "traffic": traffic,
            "system_proxy": sys_proxy,
            "ports": ports,
        }
        if current:
            result["current_profile"] = {
                "name": current.get("name") or current.get("file"),
                "type": current.get("type"),
                "uid": current.get("uid"),
                "selected": current.get("selected") or [],
            }
        echo_json(result)
        return

    suffix = " (Windows)" if state.platform == platforms.WINDOWS else ""
    click.echo("=== Clash Verge Status{} ===".format(suffix))
    click.echo("📁 Config: {}".format(client.config_dir))
    click.echo("📋 Profiles: {}".format(profiles_count))
    if current:
        click.echo("\n🟢 Active: {}".format(current.get("name") or current.get("file")))
        for sel in current.get("selected") or []:
            click.echo("   • {}: {}".format(sel.get("name"), sel.get("now")))
    click.echo("\n📊 Traffic: ↑{}GB ↓{}GB".format(traffic.get("upload_gb", 0), traffic.get("download_gb", 0)))
    click.echo("\n🔌 Proxy: HTTP:{} SOCKS:{} Mixed:{}".format(
        ports.get("http_port"), ports.get("socks_port"), ports.get("mixed_port")))
    click.echo("   System: {} | TUN: {}".format(
        on_off(sys_proxy.get("system_proxy")), on_off(sys_proxy.get("tun_mode"))))


@cli.command()
@pass_state
def path(state: State) -> None:
    """Show Clash Verge config path"""
    client = state.client
    click.echo("Config directory: {}".format(client.config_dir))
    click.echo("Exists: {}".format(client.config_dir.exists()))


# ============== PROFILE COMMANDS ==============

@cli.command()
@json_option
@pass_state
def profiles(state: State, as_json: bool) -> None:
    """List all profiles"""
    items = state.client.get_profiles()
    if not items:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No profiles found")
        return

    if as_json:
        echo_json([{
            "name": p.get("name") or p.get("file"),
            "type": p.get("type"),
            "uid": p.get("uid"),
            "is_current": p.get("is_current"),
            "url": p.get("url"),
        } for p in items])
        return

    click.echo("=== Profiles ===")
    for i, p in enumerate(items, 1):
        name = p.get("name") or p.get("file") or "Profile {}".format(i)
        mark = "🟢 ACTIVE" if p.get("is_current") else "⚪"
        click.echo("{}. {} [{}] {}".format(i, name, p.get("type"), mark))


@cli.command()
@click.argument("profile_name")
@pass_state
def activate(state: State, profile_name: str) -> None:
    """Activate a profile by name or UID"""
    target = state.client.find_profile(profile_name)
    if not target or not target.get("uid"):
        fail("Profile '{}' not found".format(profile_name))
    state.client.activate_profile(target["uid"])
    success("Switched to: {}".format(target.get("name") or target.get("file")))


@cli.command()
@click.argument("profile_url")
@click.option("--name", help="Profile name")
@pass_state
def add(state: State, profile_url: str, name: Optional[str]) -> None:
    """Add a profile from URL"""
    click.echo("📥 Downloading: {}".format(profile_url))
    try:
        response = requests.get(profile_url, timeout=max(state.timeout, 10))
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        fail("Error: {}".format(exc))
    try:
        item = state.client.add_profile(profile_url, response.text, name)
    except OSError as exc:
        fail("Error: {}".format(exc))
    success("Added profile: {}".format(item["name"]))


@cli.command()
@click.argument("profile_name")
@pass_state
def delete(state: State, profile_name: str) -> None:
    """Delete a profile"""
    client = state.client
    target = client.find_profile(profile_name, match_file=False)
    if not target:
        fail("Profile '{}' not found".format(profile_name))
    if target.get("is_current"):
        fail("Cannot delete active profile")
    client.delete_profile(target)
    success("Deleted: {}".format(target.get("name")))


# ============== PROXY COMMANDS ==============

@cli.command()
@json_option
@click.option("--group", help="Filter by proxy group")
@pass_state
def proxies(state: State, as_json: bool, group: Optional[str]) -> None:
    """List all proxies"""
    client = state.client
    all_proxies = client.get_proxies()
    groups = [g for g in client.get_proxy_groups() if not group or g.get("name") == group]

    if as_json:
        echo_json({
            "proxies": {k: v for k, v in all_proxies.items() if k not in ("DIRECT", "REJECT")},
            "groups": [{"name": g.get("name"), "type": g.get("type"), "proxies": g.get("proxies") or []}
                       for g in groups],
        })
        return

    click.echo("=== Proxy Groups ===")
    for g in groups:
        click.echo("\n📂 {} [{}]".format(g.get("name"), g.get("type")))
        for p in (g.get("proxies") or [])[:10]:
            click.echo("   • {}".format(p))


@cli.command()
@click.argument("group_name")
@click.option("--limit", default=5, show_default=True, help="Number of proxies to test")
@click.option("--url", "test_url", help="Latency test URL (default: default_latency_test from verge.yaml)")
@json_option
@pass_state
def test(state: State, group_name: str, limit: int, test_url: Optional[str], as_json: bool) -> None:
    """Test proxy latency for a group (via the Clash API)"""
    api = state.api
    try:
        live = api.proxies()
    except ControllerError as exc:
        fail(str(exc))
    target = live.get(group_name)
    if not isinstance(target, dict) or "all" not in target:
        fail("Group '{}' not found".format(group_name))

    test_url = test_url or state.client.get_verge_config().get("default_latency_test") or DEFAULT_DELAY_URL
    configured = state.client.get_proxies()
    timeout_ms = int(state.timeout * 1000)

    results = []
    for proxy_name in (target.get("all") or [])[:limit]:
        if proxy_name in SKIP_IN_LATENCY_TEST:
            continue
        try:
            latency = api.delay(proxy_name, test_url, timeout_ms)
        except ControllerError as exc:
            if exc.status == 404:
                continue
            fail(str(exc))
        results.append({
            "name": proxy_name,
            "server": (configured.get(proxy_name) or {}).get("server"),
            "latency_ms": latency,
        })

    if as_json:
        echo_json(results)
        return

    click.echo("=== Latency Test: {} ===".format(group_name))
    for r in sorted(results, key=lambda x: x["latency_ms"] or 99999):
        lat = "{}ms".format(r["latency_ms"]) if r["latency_ms"] else "timeout"
        click.echo("   {}: {}".format(r["name"], lat))


@cli.command()
@click.argument("group_name")
@click.argument("proxy_name")
@pass_state
def select(state: State, group_name: str, proxy_name: str) -> None:
    """Select a proxy for a group (via the Clash API)"""
    try:
        state.api.select(group_name, proxy_name)
    except ControllerError as exc:
        if exc.status == 404:
            fail("Group '{}' not found".format(group_name))
        fail(str(exc))
    state.client.remember_selection(group_name, proxy_name)
    success("Selected {} for {}".format(proxy_name, group_name))


# ============== SYSTEM PROXY COMMANDS ==============

def _resolve_toggle(action: str, current: Any) -> bool:
    if action == "toggle":
        return not current
    return action == "on"


@cli.command()
@json_option
@pass_state
def sysproxy(state: State, as_json: bool) -> None:
    """Show system proxy status"""
    st = state.client.get_system_proxy_status()
    if as_json:
        echo_json(st)
        return
    click.echo("=== System Proxy Status ===")
    click.echo("System Proxy: {}".format(on_off(st.get("system_proxy"))))
    click.echo("TUN Mode: {}".format(on_off(st.get("tun_mode"))))
    click.echo("Proxy Guard: {}".format(on_off(st.get("proxy_guard"))))


@cli.command("sysproxy-set")
@click.argument("action", type=click.Choice(["on", "off", "toggle"]))
@pass_state
def sysproxy_set(state: State, action: str) -> None:
    """Control system proxy (on/off/toggle)"""
    client = state.client
    new_state = _resolve_toggle(action, client.get_system_proxy_status().get("system_proxy"))
    client.set_system_proxy(new_state)
    success("System Proxy: {}".format(on_off(new_state)))


@cli.command()
@click.argument("action", type=click.Choice(["on", "off", "toggle"]))
@pass_state
def tun(state: State, action: str) -> None:
    """Control TUN mode (on/off/toggle)"""
    client = state.client
    new_state = _resolve_toggle(action, client.get_system_proxy_status().get("tun_mode"))
    client.set_tun_mode(new_state)
    success("TUN Mode: {}".format(on_off(new_state)))


# ============== PORT COMMANDS ==============

@cli.command()
@json_option
@pass_state
def ports(state: State, as_json: bool) -> None:
    """Show port configuration"""
    p = state.client.get_ports()
    if as_json:
        echo_json(p)
        return

    def enabled(key: str) -> str:
        return "(enabled)" if p.get(key) else "(disabled)"

    click.echo("=== Port Configuration ===")
    click.echo("HTTP Port: {} {}".format(p.get("http_port"), enabled("enable_http")))
    click.echo("SOCKS Port: {} {}".format(p.get("socks_port"), enabled("enable_socks")))
    click.echo("Mixed Port: {}".format(p.get("mixed_port")))
    click.echo("Redir Port: {} {}".format(p.get("redir_port"), enabled("enable_redir")))


@cli.command("port-set")
@click.argument("port_type", type=click.Choice(["http", "socks", "mixed", "redir"]))
@click.argument("port", type=click.IntRange(1, 65535))
@click.option("--enable/--disable", default=None, help="Enable or disable")
@pass_state
def port_set(state: State, port_type: str, port: int, enable: Optional[bool]) -> None:
    """Set port (http/socks/mixed/redir)"""
    result = state.client.set_port(port_type, port, enable)
    if "error" in result:
        fail(result["error"])
    success("{} port set to {}".format(port_type.upper(), port))


# ============== DNS / RULES / TRAFFIC ==============

@cli.command()
@json_option
@pass_state
def dns(state: State, as_json: bool) -> None:
    """Show DNS configuration"""
    data = state.client.get_dns_config()
    if as_json:
        echo_json(data)
        return
    click.echo("=== DNS Configuration ===")
    echo_yaml(data)


@cli.command()
@json_option
@click.option("--type", "rule_type", help="Filter by rule type")
@click.option("--limit", default=20, show_default=True, help="Number of rules to show")
@pass_state
def rules(state: State, as_json: bool, rule_type: Optional[str], limit: int) -> None:
    """Show routing rules"""
    items = state.client.get_rules()
    if rule_type:
        items = [r for r in items if r.get("type") == rule_type]
    items = items[:max(limit, 0)]
    if as_json:
        echo_json(items)
        return
    click.echo("=== Routing Rules ===")
    for r in items:
        click.echo("{:20} {}".format(r.get("type"), r.get("value", "")[:50]))


@cli.command()
@json_option
@pass_state
def traffic(state: State, as_json: bool) -> None:
    """Show traffic statistics"""
    t = state.client.get_traffic_stats()
    if as_json:
        echo_json(t)
        return
    click.echo("=== Traffic Statistics ===")
    click.echo("Upload:   {} GB".format(t.get("upload_gb", 0)))
    click.echo("Download: {} GB".format(t.get("download_gb", 0)))
    click.echo("Total:    {} GB".format(t.get("total_gb", 0)))


# ============== BACKUP COMMANDS ==============

@cli.command()
@json_option
@pass_state
def backups(state: State, as_json: bool) -> None:
    """List all backups"""
    items = state.client.list_backups()
    if as_json:
        echo_json(items)
        return
    click.echo("=== Backups ===")
    for b in items:
        click.echo("• {} - {}".format(b.get("name"), b.get("created")))


@cli.command()
@click.argument("name", required=False)
@pass_state
def backup(state: State, name: Optional[str]) -> None:
    """Create a backup"""
    try:
        backup_path = state.client.create_backup(name)
    except (ValueError, OSError) as exc:
        fail(str(exc))
    success("Backup created: {}".format(backup_path))


@cli.command()
@click.argument("name")
@pass_state
def restore(state: State, name: str) -> None:
    """Restore from a backup"""
    if not state.client.restore_backup(name):
        fail("Backup not found: {}".format(name))
    success("Restored from: {}".format(name))


# ============== LOGS COMMANDS ==============

@cli.command()
@click.option("--lines", default=50, show_default=True, help="Number of lines")
@json_option
@pass_state
def logs(state: State, lines: int, as_json: bool) -> None:
    """Show logs"""
    log_lines = state.client.get_logs(lines)
    if as_json:
        echo_json(log_lines, indent=None)
        return
    for line in log_lines:
        click.echo(line.rstrip())


@cli.command()
@click.argument("keyword")
@click.option("--lines", default=100, show_default=True, help="Search range")
@pass_state
def loggrep(state: State, keyword: str, lines: int) -> None:
    """Search logs for keyword"""
    needle = keyword.lower()
    matched = [line for line in state.client.get_logs(lines) if needle in line.lower()]
    click.echo("=== Found {} matches ===".format(len(matched)))
    for line in matched[-20:]:
        click.echo(line.rstrip())


# ============== CONFIG COMMANDS ==============

@cli.command()
@json_option
@pass_state
def config(state: State, as_json: bool) -> None:
    """Show Clash configuration"""
    clash = state.client.get_clash_config()
    if as_json:
        echo_json(clash)
        return
    click.echo("=== Clash Configuration ===")
    echo_yaml(clash)


@cli.command()
@json_option
@pass_state
def vergecfg(state: State, as_json: bool) -> None:
    """Show Verge configuration"""
    verge = state.client.get_verge_config()
    if as_json:
        echo_json(verge)
        return
    click.echo("=== Verge Configuration ===")
    echo_yaml({k: v for k, v in verge.items()
               if "password" not in str(k).lower() and "secret" not in str(k).lower()})


@cli.command()
@json_option
@pass_state
def webui(state: State, as_json: bool) -> None:
    """Show Web UI list"""
    items = state.client.get_web_ui_list()
    if as_json:
        echo_json(items)
        return
    click.echo("=== Web UI ===")
    if not items:
        click.echo("No custom Web UI configured")
    for ui in items:
        if isinstance(ui, dict):
            click.echo("• {}: {}".format(ui.get("name"), ui.get("url")))
        else:
            click.echo("• {}".format(ui))


@cli.command("set")
@click.argument("key")
@click.argument("value")
@pass_state
def set_value(state: State, key: str, value: str) -> None:
    """Set Verge config key (experimental)"""
    client = state.client
    verge = client.get_verge_config()
    parsed = parse_scalar(value)
    verge[key] = parsed
    client.save_verge_config(verge)
    success("Set {} = {}".format(key, parsed))


@cli.command()
@pass_state
def core(state: State) -> None:
    """Show Clash core info"""
    click.echo("Clash Core: {}".format(state.client.get_verge_config().get("clash_core", "verge-mihomo")))


@cli.command()
@pass_state
def refresh(state: State) -> None:
    """Force refresh configuration"""
    profiles_yaml = state.client.profiles_yaml
    if profiles_yaml.exists():
        os.utime(str(profiles_yaml), None)
    success("Configuration refreshed")


# ============== CONTROL COMMANDS ==============

@cli.command()
def restart() -> None:
    """Restart Clash Verge"""
    click.echo("🔄 Restarting Clash Verge...")
    platforms.stop_app()
    executable = platforms.app_executable()
    if not executable:
        fail("Clash Verge app not found")
    platforms.start_app(executable)
    success("Clash Verge restarted")


@cli.command("open-dir")
@pass_state
def open_dir(state: State) -> None:
    """Open config directory"""
    platforms.open_path(state.client.config_dir)


@cli.command("open-logs")
@pass_state
def open_logs(state: State) -> None:
    """Open logs directory"""
    platforms.open_path(state.client.logs_dir)


# ============== GUARDIAN / HEALTH ==============

def find_guardian_script() -> Optional[Path]:
    """Locate the optional external ``minimax_guardian.py`` script."""
    candidates = []
    env = os.environ.get("CLASH_VERGE_GUARDIAN")
    if env:
        candidates.append(Path(env))
    if sys.argv and sys.argv[0]:
        candidates.append(Path(os.path.realpath(sys.argv[0])).parent / "minimax_guardian.py")
    candidates.append(Path.cwd() / "minimax_guardian.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


@cli.command()
@click.option("--once", is_flag=True, help="Run once only")
@click.option("--interval", default=120, show_default=True, help="Check interval in seconds")
@click.option("--max-latency", default=3000, show_default=True, help="Max latency in ms")
def guardian(once: bool, interval: int, max_latency: int) -> None:
    """Run MiniMax Guardian (auto-monitor and heal)"""
    script = find_guardian_script()
    if script is None:
        fail("minimax_guardian.py not found (place it next to the CLI, in the current "
             "directory, or set CLASH_VERGE_GUARDIAN)")
    click.echo("🛡️  Starting MiniMax Guardian...")
    click.echo("   Max latency: {}ms, Interval: {}s".format(max_latency, interval))
    click.echo("   Press Ctrl+C to stop\n")
    env = dict(os.environ, PYTHONPATH=str(script.parent))
    cmd = [sys.executable, str(script)] + (["--once"] if once else [])
    try:
        code = subprocess.call(cmd, env=env)  # noqa: S603
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)


@cli.command()
@pass_state
def health(state: State) -> None:
    """Quick health check"""
    ok = True
    try:
        state.api.configs()
        click.echo("✅ Clash API: 在线")
    except ControllerError as exc:
        ok = False
        click.echo("❌ Clash API: {}".format(exc))

    port = state.client.get_ports().get("mixed_port") or DEFAULT_MIXED_PORT
    proxy = "http://127.0.0.1:{}".format(port)
    try:
        start = time.time()
        requests.get(HEALTH_CHECK_URL, proxies={"http": proxy, "https": proxy}, timeout=state.timeout)
        click.echo("✅ MiniMax API: {}ms".format(int((time.time() - start) * 1000)))
    except requests.exceptions.RequestException as exc:
        ok = False
        click.echo("❌ MiniMax API: {}".format(str(exc)[:50]))

    if not ok:
        sys.exit(1)


def main(argv: Optional[List[str]] = None, prog_name: Optional[str] = None) -> None:
    """Console-script entry point."""
    configure_console()
    cli.main(args=argv, prog_name=prog_name)


if __name__ == "__main__":  # pragma: no cover
    main()
