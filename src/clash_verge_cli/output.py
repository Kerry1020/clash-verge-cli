"""Output helpers shared by all commands."""

import json
import sys
from typing import Any, NoReturn

import click
import yaml

EXIT_OK = 0
EXIT_ERROR = 1


def echo_json(data: Any, indent: int = 2) -> None:
    click.echo(json.dumps(data, ensure_ascii=False, indent=indent, default=str))


def echo_yaml(data: Any) -> None:
    click.echo(yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))


def on_off(value: Any) -> str:
    return "ON" if value else "OFF"


def success(message: str) -> None:
    click.echo("✅ {}".format(message))


def fail(message: str, code: int = EXIT_ERROR) -> NoReturn:
    """Print an error to stderr and exit with a non-zero status."""
    click.echo("❌ {}".format(message), err=True)
    sys.exit(code)


def configure_console() -> None:
    """Avoid UnicodeEncodeError when emoji are written to a non-UTF-8 stream
    (e.g. redirected output on Windows using a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure and encoding not in ("utf8", "utf8sig"):
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):  # pragma: no cover - exotic streams
                pass
