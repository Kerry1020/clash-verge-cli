import json
from pathlib import Path
from unittest import mock

import pytest
import requests
import yaml
from click.testing import CliRunner

from clash_verge_cli.commands import cli

GROUP = "🚀 节点 选择/Proxy #1"
NODE_A = "🇯🇵 Japan 01"
NODE_B = "德国hy2-5-三网优化"

CLASH = {
    "mixed-port": 7897,
    "external-controller": "127.0.0.1:9097",
    "secret": "s3cret",
    "dns": {"enable": True, "nameserver": ["223.5.5.5"]},
    "proxies": [
        {"name": NODE_A, "type": "ss", "server": "jp.example.com", "port": 443, "cipher": "aes-128-gcm",
         "password": "pw"},
        {"name": NODE_B, "type": "hysteria2", "server": "de.example.com", "port": 8443},
    ],
    "proxy-groups": [
        {"name": GROUP, "type": "select", "proxies": [NODE_A, NODE_B, "DIRECT"]},
        {"name": "Auto", "type": "url-test", "proxies": [NODE_A, NODE_B]},
    ],
    "rules": ["DOMAIN-SUFFIX,google.com,Proxy", "GEOIP,CN,DIRECT", "MATCH,Proxy"],
}

VERGE = {
    "enable_system_proxy": False,
    "enable_tun_mode": False,
    "verge_mixed_port": 7897,
    "verge_port": 7899,
    "verge_socks_port": 7898,
    "verge_http_enabled": True,
    "current_profile": "p1",
    "web_ui_list": [{"name": "yacd", "url": "http://yacd.example"}],
}

PROFILES = {
    "current": "p1",
    "items": [
        {"uid": "p1", "name": "Main", "type": "remote", "file": "p1.yaml", "url": "https://sub.example/a",
         "selected": [{"name": GROUP, "now": NODE_A}],
         "extra": {"upload": 1073741824, "download": 2147483648, "total": 10737418240}},
        {"uid": "p2", "name": "Backup 订阅", "type": "local", "file": "p2.yaml"},
    ],
}


def write_yaml(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    """Never let a test touch the real Clash Verge installation of the machine."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    for var in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(var, str(fake_home))
    for var in ("APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(var, str(fake_home / var.lower()))
    monkeypatch.setenv("CLASH_VERGE_DIR", str(tmp_path / "default-config"))
    monkeypatch.delenv("CLASH_API_URL", raising=False)
    monkeypatch.delenv("CLASH_API_SECRET", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    return fake_home


@pytest.fixture
def config_dir(tmp_path):
    d = tmp_path / "Clash Verge 配置"
    (d / "profiles").mkdir(parents=True)
    write_yaml(d / "clash-verge.yaml", CLASH)
    write_yaml(d / "verge.yaml", VERGE)
    write_yaml(d / "profiles.yaml", PROFILES)
    (d / "profiles" / "p1.yaml").write_text("proxies: []\n", encoding="utf-8")
    (d / "profiles" / "p2.yaml").write_text("proxies: []\n", encoding="utf-8")
    return d


@pytest.fixture
def run(config_dir, monkeypatch):
    for var in ("CLASH_VERGE_DIR", "CLASH_API_URL", "CLASH_API_SECRET"):
        monkeypatch.delenv(var, raising=False)
    runner = CliRunner()

    def _run(*args, **kwargs):
        return runner.invoke(cli, ["--config-dir", str(config_dir)] + list(args), **kwargs)

    return _run


class FakeResponse:
    def __init__(self, status=200, payload=None, text=None):
        self.status_code = status
        if payload is not None:
            self.content = json.dumps(payload).encode()
        else:
            self.content = (text or "").encode()
        self.text = self.content.decode()

    def json(self):
        return json.loads(self.content.decode())


@pytest.fixture
def http(monkeypatch):
    """Route ``requests.Session.request`` to a handler; records every call."""
    calls = []
    state = {"handler": lambda method, url, kwargs: FakeResponse(404, {"message": "not mocked"})}

    def fake_request(self, method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        result = state["handler"](method, url, kwargs)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(requests.Session, "request", fake_request)

    class Http:
        def handle(self, fn):
            state["handler"] = fn

    h = Http()
    h.calls = calls
    return h


@pytest.fixture
def no_network(monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network disabled in tests")

    monkeypatch.setattr(requests, "get", mock.Mock(side_effect=boom))
