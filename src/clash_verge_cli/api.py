"""Minimal client for the mihomo / Clash external controller REST API."""

from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

DEFAULT_CONTROLLER = "127.0.0.1:9097"
DEFAULT_TIMEOUT = 5.0
DEFAULT_DELAY_URL = "https://www.gstatic.com/generate_204"


class ControllerError(Exception):
    """Raised when the controller is unreachable or returns an error."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def normalize_controller(address: Optional[str]) -> str:
    """Turn an ``external-controller`` value into a base URL.

    Accepts ``127.0.0.1:9097``, ``:9090``, ``0.0.0.0:9090``, ``[::]:9090`` or a
    full ``http(s)://`` URL.
    """
    address = (address or DEFAULT_CONTROLLER).strip()
    if address.startswith(("http://", "https://")):
        return address.rstrip("/")
    if address.startswith(":"):
        address = "127.0.0.1" + address
    host, sep, port = address.rpartition(":")
    if not sep:
        host, port = address, "9097"
    if host in ("", "0.0.0.0", "*"):  # noqa: S104 - wildcard bind means "connect locally"
        host = "127.0.0.1"
    elif host in ("[::]", "::"):
        host = "[::1]"
    return "http://{}:{}".format(host, port)


def quote_name(name: str) -> str:
    """Percent-encode a proxy/group name as a single URL path segment.

    Names frequently contain spaces, CJK characters, emoji, ``/`` or ``#`` –
    all of which must be escaped (``safe=''``) to stay inside one segment.
    """
    return quote(name, safe="")


class ClashAPI:
    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = normalize_controller(base_url)
        self.secret = secret or None
        self.timeout = timeout
        self.session = session or requests.Session()
        # Never route controller traffic through HTTP(S)_PROXY env vars.
        self.session.trust_env = False

    def headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.secret:
            headers["Authorization"] = "Bearer {}".format(self.secret)
        return headers

    def request(self, method: str, path: str, timeout: Optional[float] = None, **kwargs: Any) -> Any:
        url = self.base_url + path
        try:
            response = self.session.request(
                method,
                url,
                headers=self.headers(),
                timeout=self.timeout if timeout is None else timeout,
                **kwargs,
            )
        except requests.exceptions.Timeout:
            raise ControllerError("Clash API timed out ({})".format(self.base_url)) from None
        except requests.exceptions.ConnectionError:
            raise ControllerError(
                "Cannot connect to Clash API at {} (is Clash Verge running?)".format(self.base_url)
            ) from None
        except requests.exceptions.RequestException as exc:
            raise ControllerError("Clash API request failed: {}".format(exc)) from None

        if response.status_code == 401:
            raise ControllerError("Clash API rejected the secret (401 Unauthorized)", 401)
        if response.status_code >= 400:
            message = ""
            try:
                message = (response.json() or {}).get("message", "")
            except ValueError:
                message = response.text.strip()
            raise ControllerError(
                "Clash API error {}{}".format(response.status_code, ": " + message if message else ""),
                response.status_code,
            )
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    # ---- endpoints -------------------------------------------------------

    def version(self) -> Dict[str, Any]:
        return self.request("GET", "/version") or {}

    def configs(self) -> Dict[str, Any]:
        return self.request("GET", "/configs") or {}

    def proxies(self) -> Dict[str, Any]:
        return (self.request("GET", "/proxies") or {}).get("proxies", {})

    def proxy(self, name: str) -> Dict[str, Any]:
        return self.request("GET", "/proxies/" + quote_name(name)) or {}

    def select(self, group: str, proxy: str) -> None:
        self.request("PUT", "/proxies/" + quote_name(group), json={"name": proxy})

    def delay(self, name: str, url: str = DEFAULT_DELAY_URL, timeout_ms: int = 5000) -> Optional[int]:
        """Latency in ms for a proxy, or None on timeout / failure."""
        try:
            data = self.request(
                "GET",
                "/proxies/{}/delay".format(quote_name(name)),
                params={"url": url, "timeout": int(timeout_ms)},
                timeout=timeout_ms / 1000.0 + self.timeout,
            )
        except ControllerError as exc:
            # 503/504/408 are how mihomo reports "proxy timed out / unreachable".
            if exc.status is not None and exc.status not in (401, 404):
                return None
            raise
        delay = (data or {}).get("delay")
        return int(delay) if delay else None
