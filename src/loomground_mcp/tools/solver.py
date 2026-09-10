# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-solver: evaluate a .lg patch, verify a reasoning.interop request, read the manifest."""
from typing import Any, Optional

from ._result import tool

PLANE = "loomground-solver"


@tool(PLANE, "loomground_solver.loomground.reason")
def solver_evaluate(patch_lg: str, transport_json: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Evaluate a Loomground .lg patch against a transport (activations with tokens). Returns the verdict JSON: status, accepted/undecided/rejected, trace."""
    from loomground_solver.loomground import reason
    return reason(patch_lg, transport_json)


@tool(PLANE, "loomground_solver.default_service().verify")
def solver_verify(request_json: dict[str, Any]) -> dict[str, Any]:
    """Verify a reasoning.interop 1.0 request; returns the ReasoningResult with its replayable trace."""
    from loomground_solver import default_service
    return default_service().verify(request_json)


@tool(PLANE, "loomground_solver.default_service().manifest")
def solver_manifest() -> dict[str, Any]:
    """The kernel's protocol manifest: protocol, roles, capabilities, schemas, extensions."""
    from loomground_solver import default_service
    return default_service().manifest()


TOOLS = [solver_evaluate, solver_verify, solver_manifest]
