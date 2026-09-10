# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""The Loomground planes over MCP."""
from ._version import __version__
from .server import build_server, main

__all__ = ["__version__", "build_server", "main"]
