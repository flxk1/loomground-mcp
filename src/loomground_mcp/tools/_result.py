# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Result envelope shared by every tool.

Every call returns a ``CallToolResult`` whose ``structured_content`` is one of
    {"plane", "function", "ok": true,  "result": ...}
    {"plane", "function", "ok": false, "error": {"type", "message"}}
    {"plane", "function", "ok": false, "unavailable": true, "reason"}
The last two carry ``is_error``; a plane that cannot answer never answers with a
fake result.
"""
import dataclasses
import enum
import functools
import importlib
import inspect
import json
from typing import Any, Callable

from mcp import types


class Unavailable(Exception):
    """The plane cannot answer this call; ``reason`` says why."""


def import_plane(module: str) -> Any:
    """Import an optional plane package; one that is not installed is ``unavailable``, never an error."""
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise Unavailable(f"{module} is not installed: {exc}") from exc


def plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(plain(v) for v in value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "to_dict"):
        return plain(value.to_dict())
    return repr(value)


def _wrap(payload: dict, *, is_error: bool) -> types.CallToolResult:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)],
                                structured_content=payload, is_error=is_error)


def ok(plane: str, function: str, result: Any) -> types.CallToolResult:
    return _wrap({"plane": plane, "function": function, "ok": True, "result": plain(result)}, is_error=False)


def failed(plane: str, function: str, exc: BaseException) -> types.CallToolResult:
    err = {"type": type(exc).__name__, "message": str(exc)}
    return _wrap({"plane": plane, "function": function, "ok": False, "error": err}, is_error=True)


def unavailable(plane: str, function: str, reason: str) -> types.CallToolResult:
    return _wrap({"plane": plane, "function": function, "ok": False, "unavailable": True, "reason": reason},
                 is_error=True)


def tool(plane: str, function: str) -> Callable[[Callable[..., Any]], Callable[..., types.CallToolResult]]:
    """Bind a plain function to its plane; the wrapper keeps the parameters and returns the envelope."""
    def deco(fn: Callable[..., Any]) -> Callable[..., types.CallToolResult]:
        @functools.wraps(fn)
        def call(*args: Any, **kwargs: Any) -> types.CallToolResult:
            try:
                return ok(plane, function, fn(*args, **kwargs))
            except Unavailable as exc:
                return unavailable(plane, function, str(exc))
            except Exception as exc:  # fail closed: every plane error is a structured error
                return failed(plane, function, exc)
        call.__signature__ = inspect.signature(fn).replace(return_annotation=types.CallToolResult)  # type: ignore[attr-defined]
        call.__annotations__ = {**fn.__annotations__, "return": types.CallToolResult}
        call.__doc__ = f"[{plane} · {function}] {inspect.getdoc(fn) or ''}".strip()
        call.plane, call.function = plane, function  # type: ignore[attr-defined]
        return call
    return deco


def enum_of(kind: type, value: Any) -> Any:
    """Resolve an enum by value or (case-insensitive) name; the plane's own names, not ours."""
    if isinstance(value, kind):
        return value
    for member in kind:
        if value == member.value or str(value).upper() == member.name:
            return member
    raise ValueError(f"{kind.__name__}: {value!r} not in {[m.value for m in kind]}")
