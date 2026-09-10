# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""loomground-solver: evaluate a .lg patch, verify a reasoning.interop request, read the manifest,
and the seven skill scripts (``skills/<skill>/scripts/run.py`` / ``advise.py``) as tools.

Each ``solver_*`` skill tool takes the JSON its script reads on stdin, as named arguments, and
returns what the script prints. The script stays in the skill as the shell fallback; the parity
tests feed both the same JSON.
"""
from typing import Any, Optional

from ._result import tool

PLANE = "loomground-solver"

Payoffs = Optional[dict[str, dict[str, float]]]
Probs = Optional[dict[str, float]]
Likelihoods = Optional[dict[str, dict[str, float]]]
Extra = Optional[dict[str, Any]]


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


def _skill(method_name: str, extra: Extra, **kwargs: Any) -> dict[str, Any]:
    """The logic of every ``skills/*/scripts/run.py``: ``method(name)(**payload)`` under ``{"method", "result"}``."""
    from loomground_solver import method
    payload = {k: v for k, v in kwargs.items() if v is not None}
    payload.update(extra or {})
    return {"method": method_name, "result": method(method_name)(**payload)}


@tool(PLANE, "skills/analyse-risks/scripts/run.py → method('pareto')")
def solver_analyse_risks(vectors: Optional[dict[str, list[float]]] = None, options: Optional[list[str]] = None,
                         method: str = "pareto", extra: Extra = None) -> dict[str, Any]:
    """Score and rank risks: `vectors` = {risk: [impact, likelihood, …]} (higher = worse on each criterion); the Pareto frontier is what to mitigate first. `method` overrides the kernel method; `extra` carries an overridden method's further keyword arguments."""
    return _skill(method, extra, vectors=vectors, options=options)


@tool(PLANE, "skills/estimate-liability/scripts/run.py → method('bayesian_update')")
def solver_estimate_liability(prior: Probs = None, likelihoods: Likelihoods = None, evidence: Optional[str] = None,
                              method: str = "bayesian_update", extra: Extra = None) -> dict[str, Any]:
    """Estimate liability as a posterior over hypotheses: `prior` = {hypothesis: p}, `likelihoods` = {hypothesis: {evidence: p}}, `evidence` = the observed key. `method`/`extra` as in solver_analyse_risks."""
    return _skill(method, extra, prior=prior, likelihoods=likelihoods, evidence=evidence)


@tool(PLANE, "skills/litigation-risk-assessor/scripts/run.py → method('expected_utility')")
def solver_litigation_risk(options: Optional[list[str]] = None, payoffs: Payoffs = None, probabilities: Probs = None,
                           method: str = "expected_utility", extra: Extra = None) -> dict[str, Any]:
    """Fight or settle by expected utility: `payoffs` = {strategy: {outcome: value}}, `probabilities` = {outcome: p} (uniform when absent). `method`/`extra` as in solver_analyse_risks."""
    return _skill(method, extra, options=options, payoffs=payoffs, probabilities=probabilities)


@tool(PLANE, "skills/opponent-modeler/scripts/run.py → method('expected_utility')")
def solver_opponent_model(options: Optional[list[str]] = None, payoffs: Payoffs = None, probabilities: Probs = None,
                          method: str = "expected_utility", extra: Extra = None) -> dict[str, Any]:
    """The opponent's likely move under an attributed decision rule: `payoffs` = {move: {state: value}} from their valuation, `probabilities` = {state: p}. `method` attributes another rule (e.g. `maximin` for a cautious adversary)."""
    return _skill(method, extra, options=options, payoffs=payoffs, probabilities=probabilities)


@tool(PLANE, "skills/probability-tracker/scripts/run.py → method('bayesian_update')")
def solver_probability(prior: Probs = None, likelihoods: Likelihoods = None, evidence: Optional[str] = None,
                       method: str = "bayesian_update", extra: Extra = None) -> dict[str, Any]:
    """Track a probability through one Bayesian update: `prior` = {hypothesis: p}, `likelihoods` = {hypothesis: {evidence: p}}, `evidence` = the observed key. `method`/`extra` as in solver_analyse_risks."""
    return _skill(method, extra, prior=prior, likelihoods=likelihoods, evidence=evidence)


@tool(PLANE, "skills/strategic-analysis/scripts/run.py → method('minimax_regret')")
def solver_strategy(options: Optional[list[str]] = None, payoffs: Payoffs = None,
                    method: str = "minimax_regret", extra: Extra = None) -> dict[str, Any]:
    """Choose a strategy under uncertainty by minimax regret: `payoffs` = {strategy: {state: value}}. `method` overrides (maximin, maximax, hurwicz, …); `extra` carries its further keyword arguments (e.g. {"alpha": 0.3})."""
    return _skill(method, extra, options=options, payoffs=payoffs)


@tool(PLANE, "skills/advise-solver-addons/scripts/advise.py → loomground_solver.addons.advise")
def solver_advise_addons(policy: Optional[dict[str, Any]] = None, problem: Optional[dict[str, Any]] = None,
                         runs: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """Deterministic advice on the world-model and metacognition add-ons from declared `policy`, `problem` and verified `runs` metadata. Advice only: `activation_performed` is always false."""
    from loomground_solver.addons import advise
    return advise({k: v for k, v in (("policy", policy), ("problem", problem), ("runs", runs)) if v is not None})


TOOLS = [solver_evaluate, solver_verify, solver_manifest,
         solver_analyse_risks, solver_estimate_liability, solver_litigation_risk, solver_opponent_model,
         solver_probability, solver_strategy, solver_advise_addons]
