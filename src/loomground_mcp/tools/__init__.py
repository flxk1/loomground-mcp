# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""One module per plane family; ``ALL`` is the registration order."""
from . import assurance, ingest, operators, solver, versum

ALL = [*versum.TOOLS, *solver.TOOLS, *ingest.TOOLS, *operators.TOOLS, *assurance.TOOLS]

__all__ = ["ALL"]
