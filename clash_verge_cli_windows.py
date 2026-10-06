#!/usr/bin/env python3
"""
Clash Verge CLI - Windows launcher (backward compatible).

macOS, Linux and Windows are now handled by the same ``clash_verge_cli``
package with automatic platform detection; this file only forwards to it.
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
