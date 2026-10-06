#!/usr/bin/env python3
"""
Clash Verge CLI - backward compatible launcher.

The implementation now lives in the ``clash_verge_cli`` package (src/).
This file is kept so ``python clash_verge_cli.py ...`` and symlinks to it
keep working. Prefer ``pip install .`` and the ``clash-verge`` command.
"""

import os
import sys

_HERE = os.path.dirname(os.path.realpath(__file__))
_SRC = os.path.join(_HERE, "src")
# This file shares its name with the package; make sure the package wins.
sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != _HERE]
if os.path.isdir(_SRC):
    sys.path.insert(0, _SRC)
if not hasattr(sys.modules.get("clash_verge_cli"), "__path__"):
    sys.modules.pop("clash_verge_cli", None)

from clash_verge_cli.commands import cli, main  # noqa: E402,F401

if __name__ == "__main__":
    main()
