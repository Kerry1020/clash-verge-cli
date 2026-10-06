import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import requests
import yaml

from clash_verge_cli import __version__
from tests.conftest import GROUP, NODE_A, NODE_B, FakeResponse

ROOT = Path(__file__).resolve().parent.parent


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- basics

def test_help_and_version(run):
    r = run()
    assert r.exit_code == 0
    assert "status" in r.output
    r = run("--version")
    assert r.exit_code == 0 and __version__ in r.output


def test_status_text(run, config_dir):
    r = run("status")
    assert r.exit_code == 0, r.output
    assert "=== Clash Verge Status" in r.output
    assert "🟢 Active: Main" in r.output
    assert "{}: {}".format(GROUP, NODE_A) in r.output
    assert "↑1.0GB ↓2.0GB" in r.output
    assert "Mixed:7897" in r.output
    assert "System: OFF | TUN: OFF" in r.output


def test_status_json(run, config_dir):
    r = run("status", "--json")
    data = json.loads(r.output)
    assert data["profiles_count"] == 2
    assert data["current_profile"]["uid"] == "p1"
    assert data["traffic"]["total_gb"] == 10.0
    assert data["config_dir"] == str(config_dir)


def test_status_without_config_does_not_create_dir(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from clash_verge_cli.commands import cli

    missing = tmp_path / "missing"
    r = CliRunner().invoke(cli, ["--config-dir", str(missing), "status", "--json"])
    assert r.exit_code == 0
    assert json.loads(r.output)["current_profile"] is None
    assert not missing.exists()


def test_env_config_dir(config_dir, monkeypatch):
    from click.testing import CliRunner

    from clash_verge_cli.commands import cli

    monkeypatch.setenv("CLASH_VERGE_DIR", str(config_dir))
    r = CliRunner().invoke(cli, ["path"])
    assert "Config directory: {}".format(config_dir) in r.output
    assert "Exists: True" in r.output


# ---------------------------------------------------------------- profiles

def test_profiles(run):
    r = run("profiles")
    assert "1. Main [remote] 🟢 ACTIVE" in r.output
    assert "2. Backup 订阅 [local] ⚪" in r.output
    data = json.loads(run("profiles", "--json").output)
    assert [p["uid"] for p in data] == ["p1", "p2"]


def test_activate_by_name_file_and_uid(run, config_dir):
    r = run("activate", "Backup 订阅")
    assert r.exit_code == 0 and "✅ Switched to: Backup 订阅" in r.output
    assert load(config_dir / "profiles.yaml")["current"] == "p2"
    assert load(config_dir / "verge.yaml")["current_profile"] == "p2"
    assert run("activate", "p1").exit_code == 0
    assert run("activate", "p2.yaml".replace(".yaml", "")).exit_code == 0


def test_activate_missing_exits_nonzero(run):
    r = run("activate", "nope")
    assert r.exit_code == 1
    assert "❌ Profile 'nope' not found" in r.output


def test_delete(run, config_dir):
    r = run("delete", "Main")
    assert r.exit_code == 1 and "Cannot delete active profile" in r.output
    r = run("delete", "Backup 订阅")
    assert r.exit_code == 0
    assert not (config_dir / "profiles" / "p2.yaml").exists()
    assert [i["uid"] for i in load(config_dir / "profiles.yaml")["items"]] == ["p1"]


def test_add_profile(run, config_dir, monkeypatch):
    class Resp:
        text = "proxies:\n  - {name: 节点}\n"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda url, timeout: Resp())
    (config_dir / "profiles" / "p1.yaml").unlink()
    (config_dir / "profiles" / "p2.yaml").unlink()
    (config_dir / "profiles").rmdir()  # add must create it
    r = run("add", "https://sub.example/x", "--name", "新订阅")
    assert r.exit_code == 0, r.output
    item = load(config_dir / "profiles.yaml")["items"][-1]
    assert item["name"] == "新订阅"
    assert (config_dir / "profiles" / item["file"]).read_text(encoding="utf-8") == Resp.text


def test_add_profile_network_error(run, monkeypatch):
    def boom(url, timeout):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    r = run("add", "https://sub.example/x")
    assert r.exit_code == 1 and "❌ Error" in r.output


# ---------------------------------------------------------------- proxies (file based)

def test_proxies_handles_list_format(run):
    r = run("proxies")
    assert r.exit_code == 0, r.output
    assert "📂 {} [select]".format(GROUP) in r.output
    data = json.loads(run("proxies", "--json").output)
    assert set(data["proxies"]) == {NODE_A, NODE_B}
    assert data["groups"][0]["name"] == GROUP


def test_proxies_group_filter(run):
    r = run("proxies", "--group", "Auto")
    assert "Auto" in r.output and GROUP not in r.output


# ---------------------------------------------------------------- proxies (API)

def live_proxies():
    return {
        "proxies": {
            GROUP: {"name": GROUP, "type": "Selector", "now": NODE_A, "all": [NODE_A, NODE_B, "DIRECT"]},
            NODE_A: {"name": NODE_A, "type": "Shadowsocks"},
            NODE_B: {"name": NODE_B, "type": "Hysteria2"},
            "DIRECT": {"name": "DIRECT", "type": "Direct"},
        }
    }


def test_test_command_uses_delay_api(run, http):
    def handler(method, url, kwargs):
        if url.endswith("/proxies"):
            return FakeResponse(200, live_proxies())
        if "delay" in url and "Japan" in requests.utils.unquote(url):
            return FakeResponse(200, {"delay": 88})
        if "delay" in url:
            return FakeResponse(504, {"message": "Timeout"})
        return FakeResponse(404, {})

    http.handle(handler)
    r = run("test", GROUP)
    assert r.exit_code == 0, r.output
    assert "{}: 88ms".format(NODE_A) in r.output
    assert "{}: timeout".format(NODE_B) in r.output
    # auth header from clash-verge.yaml secret, names percent-encoded
    assert all(c["headers"]["Authorization"] == "Bearer s3cret" for c in http.calls)
    delay_urls = [c["url"] for c in http.calls if "delay" in c["url"]]
    assert len(delay_urls) == 2  # DIRECT skipped
    assert all(" " not in u and "🇯🇵" not in u for u in delay_urls)

    data = json.loads(run("test", GROUP, "--json").output)
    assert data[0] == {"name": NODE_A, "server": "jp.example.com", "latency_ms": 88}


def test_test_unknown_group(run, http):
    http.handle(lambda m, u, k: FakeResponse(200, live_proxies()))
    r = run("test", "Nope")
    assert r.exit_code == 1 and "Group 'Nope' not found" in r.output


def test_test_controller_down(run, http):
    http.handle(lambda m, u, k: requests.exceptions.ConnectionError("refused"))
    r = run("test", GROUP)
    assert r.exit_code == 1
    assert "Cannot connect to Clash API at http://127.0.0.1:9097" in r.output
    assert "Traceback" not in r.output


def test_select(run, http, config_dir):
    http.handle(lambda m, u, k: FakeResponse(204))
    r = run("select", GROUP, NODE_B)
    assert r.exit_code == 0, r.output
    assert "✅ Selected {} for {}".format(NODE_B, GROUP) in r.output
    call = http.calls[0]
    assert call["method"] == "PUT"
    assert call["url"] == "http://127.0.0.1:9097/proxies/" + requests.utils.quote(GROUP, safe="")
    assert call["json"] == {"name": NODE_B}
    selected = load(config_dir / "profiles.yaml")["items"][0]["selected"]
    assert selected == [{"name": GROUP, "now": NODE_B}]


def test_select_cli_overrides(run, http, tmp_path):
    http.handle(lambda m, u, k: FakeResponse(204))
    from click.testing import CliRunner

    from clash_verge_cli.commands import cli

    r = CliRunner().invoke(cli, ["--config-dir", str(tmp_path), "--controller", "10.1.1.1:9090", "--secret", "",
                                 "select", "G", "P"])
    assert r.exit_code == 0, r.output
    assert http.calls[0]["url"] == "http://10.1.1.1:9090/proxies/G"
    assert "Authorization" not in http.calls[0]["headers"]


def test_select_errors(run, http):
    http.handle(lambda m, u, k: FakeResponse(400, {"message": "Selector update error: proxy not exist"}))
    r = run("select", GROUP, "ghost")
    assert r.exit_code == 1 and "proxy not exist" in r.output
    http.handle(lambda m, u, k: FakeResponse(404, {"message": "resource not found"}))
    r = run("select", "ghost", "x")
    assert r.exit_code == 1 and "Group 'ghost' not found" in r.output
    http.handle(lambda m, u, k: FakeResponse(401, {"message": "Unauthorized"}))
    r = run("select", GROUP, NODE_A)
    assert r.exit_code == 1 and "401" in r.output


# ---------------------------------------------------------------- system proxy / ports

@pytest.mark.parametrize("name", ["sysproxy-set", "sysproxy_set"])
def test_sysproxy_set_both_spellings(run, config_dir, name):
    r = run(name, "on")
    assert r.exit_code == 0, r.output
    assert "✅ System Proxy: ON" in r.output
    assert load(config_dir / "verge.yaml")["enable_system_proxy"] is True
    run(name, "toggle")
    assert load(config_dir / "verge.yaml")["enable_system_proxy"] is False


def test_tun(run, config_dir):
    assert "TUN Mode: ON" in run("tun", "toggle").output
    assert load(config_dir / "verge.yaml")["enable_tun_mode"] is True
    assert "TUN Mode: ON" in run("sysproxy").output


def test_ports_and_port_set(run, config_dir):
    assert "HTTP Port: 7899 (enabled)" in run("ports").output
    r = run("port_set", "socks", "1080", "--enable")
    assert r.exit_code == 0 and "✅ SOCKS port set to 1080" in r.output
    verge = load(config_dir / "verge.yaml")
    assert verge["verge_socks_port"] == 1080 and verge["verge_socks_enabled"] is True
    assert run("port-set", "http", "70000").exit_code == 2


def test_verge_key_order_preserved(run, config_dir):
    (config_dir / "verge.yaml").write_text("zeta: 1\nalpha: 2\n", encoding="utf-8")
    run("tun", "on")
    assert list(load(config_dir / "verge.yaml")) == ["zeta", "alpha", "enable_tun_mode"]


# ---------------------------------------------------------------- misc read commands

def test_rules_dns_traffic_config(run):
    assert "DOMAIN-SUFFIX" in run("rules").output
    data = json.loads(run("rules", "--type", "GEOIP", "--json").output)
    assert data == [{"type": "GEOIP", "value": "CN", "payload": "DIRECT"}]
    assert "223.5.5.5" in run("dns").output
    assert "Total:    10.0 GB" in run("traffic").output
    assert json.loads(run("config", "--json").output)["mixed-port"] == 7897


def test_vergecfg_hides_secrets(run, config_dir):
    verge = load(config_dir / "verge.yaml")
    verge["webdav_password"] = "hunter2"
    (config_dir / "verge.yaml").write_text(yaml.safe_dump(verge), encoding="utf-8")
    assert "hunter2" not in run("vergecfg").output


def test_webui_core(run):
    assert "• yacd: http://yacd.example" in run("webui").output
    assert "Clash Core: verge-mihomo" in run("core").output


def test_set(run, config_dir):
    run("set", "foo", "true")
    run("set", "--", "num", "-5")
    run("set", "s", "hello")
    verge = load(config_dir / "verge.yaml")
    assert verge["foo"] is True and verge["num"] == -5 and verge["s"] == "hello"


# ---------------------------------------------------------------- backups / logs

def test_backup_roundtrip(run, config_dir):
    r = run("backup", "snap 1")
    assert r.exit_code == 0, r.output
    data = json.loads(run("backups", "--json").output)
    assert data[0]["name"] == "snap 1"
    run("tun", "on")
    assert run("restore", "snap 1").exit_code == 0
    assert load(config_dir / "verge.yaml")["enable_tun_mode"] is False


def test_backup_unicode_content(run, config_dir):
    run("backup", "u")
    copied = config_dir / "clash-verge-rev-backup" / "u" / "clash-verge.yaml"
    assert NODE_B in copied.read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["../evil", "..", "a/b"])
def test_backup_rejects_path_traversal(run, config_dir, bad):
    assert run("backup", bad).exit_code == 1
    assert run("restore", bad).exit_code == 1


def test_restore_missing(run):
    r = run("restore", "nope")
    assert r.exit_code == 1 and "Backup not found: nope" in r.output


def test_logs(run, config_dir):
    logs = config_dir / "logs"
    logs.mkdir()
    old = logs / "old.log"
    old.write_text("old line\n", encoding="utf-8")
    os.utime(str(old), (1, 1))
    (logs / "new.log").write_text("".join("line {} 错误\n".format(i) for i in range(10)), encoding="utf-8")
    r = run("logs", "--lines", "3")
    assert r.output.splitlines() == ["line 7 错误", "line 8 错误", "line 9 错误"]
    assert len(json.loads(run("logs", "--json").output)) == 10
    assert "=== Found 10 matches ===" in run("loggrep", "错误").output


# ---------------------------------------------------------------- health / guardian / control

def test_health_ok(run, http, monkeypatch):
    http.handle(lambda m, u, k: FakeResponse(200, {"mode": "rule"}))
    seen = {}

    def fake_get(url, proxies, timeout):
        seen.update(proxies)
        return FakeResponse(200, {})

    monkeypatch.setattr(requests, "get", fake_get)
    r = run("health")
    assert r.exit_code == 0, r.output
    assert "✅ Clash API: 在线" in r.output
    assert seen["https"] == "http://127.0.0.1:7897"
    assert http.calls[0]["headers"]["Authorization"] == "Bearer s3cret"


def test_health_down(run, http, no_network):
    http.handle(lambda m, u, k: requests.exceptions.ConnectionError("refused"))
    r = run("health")
    assert r.exit_code == 1
    assert "❌ Clash API: Cannot connect" in r.output
    assert "❌ MiniMax API" in r.output


def test_guardian_missing_script(run, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CLASH_VERGE_GUARDIAN", raising=False)
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "clash-verge")])
    r = run("guardian", "--once")
    assert r.exit_code == 1 and "minimax_guardian.py not found" in r.output


def test_guardian_runs_script(run, monkeypatch, tmp_path):
    script = tmp_path / "minimax_guardian.py"
    script.write_text("import sys; sys.exit(3 if '--once' in sys.argv else 0)\n", encoding="utf-8")
    monkeypatch.setenv("CLASH_VERGE_GUARDIAN", str(script))
    r = run("guardian", "--once")
    assert r.exit_code == 3


def test_restart_app_missing(run, monkeypatch):
    from clash_verge_cli import platforms

    monkeypatch.setattr(platforms, "stop_app", lambda *a, **k: None)
    monkeypatch.setattr(platforms, "app_executable", lambda *a, **k: None)
    r = run("restart")
    assert r.exit_code == 1 and "Clash Verge app not found" in r.output


# ---------------------------------------------------------------- legacy shims

@pytest.mark.parametrize("script", ["clash_verge_cli.py", "clash_verge_cli_windows.py"])
def test_legacy_scripts_still_work(script, config_dir, tmp_path):
    env = dict(os.environ, CLASH_VERGE_DIR=str(config_dir), PYTHONIOENCODING="utf-8")
    out = subprocess.run(
        [sys.executable, str(ROOT / script), "profiles", "--json"],
        cwd=str(tmp_path), env=env, capture_output=True, text=True, encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)[0]["uid"] == "p1"


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions")
def test_save_keeps_file_mode(run, config_dir):
    target = config_dir / "verge.yaml"
    os.chmod(str(target), 0o644)
    run("tun", "on")
    assert (target.stat().st_mode & 0o777) == 0o644


def test_legacy_entry_point_attribute():
    import clash_verge_cli

    assert callable(clash_verge_cli.cli)
