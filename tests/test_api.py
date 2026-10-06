import pytest
import requests

from clash_verge_cli.api import ClashAPI, ControllerError, normalize_controller, quote_name
from tests.conftest import FakeResponse


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "http://127.0.0.1:9097"),
        ("127.0.0.1:9097", "http://127.0.0.1:9097"),
        (":9090", "http://127.0.0.1:9090"),
        ("0.0.0.0:9090", "http://127.0.0.1:9090"),
        ("[::]:9090", "http://[::1]:9090"),
        ("http://10.0.0.2:9090/", "http://10.0.0.2:9090"),
        ("localhost", "http://localhost:9097"),
    ],
)
def test_normalize_controller(value, expected):
    assert normalize_controller(value) == expected


def test_quote_name_escapes_everything():
    assert quote_name("a b/c#d?e") == "a%20b%2Fc%23d%3Fe"
    assert quote_name("🇯🇵 日本") == "%F0%9F%87%AF%F0%9F%87%B5%20%E6%97%A5%E6%9C%AC"


def test_bearer_header_and_timeout(http):
    http.handle(lambda m, u, k: FakeResponse(200, {"version": "1.18"}))
    api = ClashAPI("127.0.0.1:9097", "abc", timeout=2.5)
    assert api.version() == {"version": "1.18"}
    call = http.calls[0]
    assert call["headers"]["Authorization"] == "Bearer abc"
    assert call["timeout"] == 2.5
    assert call["url"] == "http://127.0.0.1:9097/version"


def test_no_auth_header_without_secret(http):
    http.handle(lambda m, u, k: FakeResponse(200, {}))
    ClashAPI("127.0.0.1:9097", None).configs()
    assert "Authorization" not in http.calls[0]["headers"]


def test_trust_env_disabled():
    assert ClashAPI().session.trust_env is False


@pytest.mark.parametrize(
    "exc,needle",
    [
        (requests.exceptions.ConnectionError("refused"), "Cannot connect"),
        (requests.exceptions.ReadTimeout("slow"), "timed out"),
    ],
)
def test_unreachable(http, exc, needle):
    http.handle(lambda m, u, k: exc)
    with pytest.raises(ControllerError, match=needle):
        ClashAPI().configs()


def test_unauthorized(http):
    http.handle(lambda m, u, k: FakeResponse(401, {"message": "Unauthorized"}))
    with pytest.raises(ControllerError) as info:
        ClashAPI(secret="wrong").configs()
    assert info.value.status == 401
    assert "secret" in str(info.value)


def test_error_message_propagates(http):
    http.handle(lambda m, u, k: FakeResponse(400, {"message": "Selector update error: proxy not exist"}))
    with pytest.raises(ControllerError, match="proxy not exist"):
        ClashAPI().select("G", "x")


def test_select_encodes_group_and_sends_body(http):
    http.handle(lambda m, u, k: FakeResponse(204))
    ClashAPI().select("🚀 节点/选择", "德国 1")
    call = http.calls[0]
    assert call["method"] == "PUT"
    assert call["url"].endswith("/proxies/%F0%9F%9A%80%20%E8%8A%82%E7%82%B9%2F%E9%80%89%E6%8B%A9")
    assert call["json"] == {"name": "德国 1"}


def test_delay_ok_and_timeout(http):
    def handler(method, url, kwargs):
        if "good" in url:
            return FakeResponse(200, {"delay": 123})
        return FakeResponse(504, {"message": "Timeout"})

    http.handle(handler)
    api = ClashAPI()
    assert api.delay("good", "https://x", 3000) == 123
    assert api.delay("bad", "https://x", 3000) is None
    assert http.calls[0]["params"] == {"url": "https://x", "timeout": 3000}


def test_delay_unknown_proxy_raises(http):
    http.handle(lambda m, u, k: FakeResponse(404, {"message": "resource not found"}))
    with pytest.raises(ControllerError) as info:
        ClashAPI().delay("missing")
    assert info.value.status == 404
