# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""One module per plane family; ``ALL`` is the registration order."""
from . import assurance, catalogue, controls, deontic, epistemic, factual, ingest, norm, operators, releases, skills, solver, topos, versum

ALL = [*catalogue.TOOLS, *releases.TOOLS, *skills.TOOLS, *versum.TOOLS, *deontic.TOOLS, *factual.TOOLS, *epistemic.TOOLS, *norm.TOOLS, *topos.TOOLS,
       *solver.TOOLS, *ingest.TOOLS, *operators.TOOLS, *assurance.TOOLS, *controls.TOOLS]

__all__ = ["ALL"]
