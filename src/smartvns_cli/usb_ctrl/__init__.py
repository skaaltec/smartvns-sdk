"""USB control package for SmartVNS CLI.

Expose the programmatic API submodules. Importing this package should be
lightweight and must not import or execute CLI parsing code; the CLI is
only reachable via `python -m smartvns_cli.usb_ctrl` (which runs
`__main__.py`) or by importing a separate `cli` module.
"""

from . import controller, routines

__all__ = ["controller", "routines"]
