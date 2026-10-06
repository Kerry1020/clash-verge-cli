"""Clash Verge CLI - command line interface for Clash Verge (Rev) / mihomo."""

__version__ = "1.1.0"

__all__ = ["__version__", "cli", "main", "ClashVergeCLI"]


def __getattr__(name):
    # Lazy re-exports keep ``clash_verge_cli:cli`` (the 1.0 entry point) working
    # without importing click on ``import clash_verge_cli``.
    if name in ("cli", "main"):
        from clash_verge_cli import commands

        return getattr(commands, name)
    if name == "ClashVergeCLI":
        from clash_verge_cli.store import ClashVergeCLI

        return ClashVergeCLI
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
