# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Shared exit-code contract for every tools/ check: 0 conforms, 1 does not, 2 the
tool could not decide. Unreadable/unparseable input is 2, never a traceback, never
a silent skip; 2 always wins over 1. Kept import-only (no CLI surface of its own).

`.exists()`/`.is_dir()`/`.is_file()` are not used anywhere below: on some Python
versions those silently swallow an OSError (permission denied, a symlink loop) and
return False, indistinguishable from genuine absence -- every check here goes
through one explicit `Path.stat()` and classifies what it raises instead. A FIFO or
other non-regular file is rejected before any open(), so a reader can never block
forever waiting for a writer that will never come."""
from __future__ import annotations

import json
import os
import stat as _stat
from pathlib import Path

OK, FAIL, ERROR = 0, 1, 2


class Undecidable(Exception):
    """Raised with an already-safe (reason()-produced) message; never raw exception text."""


def reason(exc: BaseException) -> str:
    """Path-free, safe-to-print description. Never forwards raw exception text for an
    exception type not explicitly mapped here -- an arbitrary ValueError's message
    could itself contain an absolute path; only the class name is safe by default."""
    if isinstance(exc, UnicodeDecodeError):
        return f"not valid UTF-8 ({exc.reason})"
    if isinstance(exc, json.JSONDecodeError):
        return f"invalid JSON ({exc.msg} at line {exc.lineno})"
    if isinstance(exc, OSError):
        return exc.strerror or exc.__class__.__name__
    return exc.__class__.__name__


def code(fail: bool, errored: bool) -> int:
    """2 wins over 1 wins over 0."""
    return ERROR if errored else (FAIL if fail else OK)


def stat_kind(path: Path):
    """One stat call, follows symlinks. (st, None) on success; (None, None) if the
    path is genuinely absent; (None, reason) for anything else undecidable (denied,
    a symlink loop, ...). A NON-directory PARENT (ENOTDIR) is filed with absent, not
    undecidable: "some/file/nested" is exactly as decidable as "some/missing/nested" --
    a component of the prefix cannot contain anything, so there is definitely nothing
    at the composed path. Every caller that stats a path it built by joining onto a
    candidate it did not itself just classify (`c / "llms.txt"`, `repo / "docs" / "x"`)
    depends on this: without it, a fully conforming repo whose candidate happened to
    already be a plain file went from a decided pass to a wrongly-aborted 2."""
    try:
        return path.stat(), None
    except (FileNotFoundError, NotADirectoryError):
        return None, None
    except OSError as e:
        return None, reason(e)


def dir_kind(path: Path):
    """"dir" it is a directory; "absent" nothing is there; "other" something else is
    there -- all three are decided, the filesystem answered. (None, reason) only when
    stat itself could not tell (denied, a symlink loop). "Is there a nested skills
    directory" is a yes/no question that a plain file answers just as decidably as
    nothing there at all -- "other" is not the same thing as undecidable and must not
    be escalated to it (that was a real regression: a conforming repo whose author
    happened to name a *file* "skills" went from 0 to a wrongly-aborted 2)."""
    st, err = stat_kind(path)
    if err is not None:
        return None, err
    if st is None:
        return "absent", None
    return ("dir" if _stat.S_ISDIR(st.st_mode) else "other"), None


def read_regular(path: Path):
    """(text, None) on success; (None, None) if genuinely absent; (None, reason) if
    present but unreadable, unparseable, or not a regular file. Type is checked via
    stat before any open -- a named pipe with no writer is rejected, not blocked on."""
    st, err = stat_kind(path)
    if err is not None:
        return None, err
    if st is None:
        return None, None
    if not _stat.S_ISREG(st.st_mode):
        return None, "not a regular file"
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:  # raced away between stat and open
        return None, None
    except (OSError, UnicodeDecodeError) as e:
        return None, reason(e)


def dir_entries(path: Path, *, explicit: bool = False):
    """(entries, None) on success (possibly empty). Absent, and (unless `explicit`)
    "exists but is not a directory", decide "nothing to list" -- ([], None): a plain
    file is a decided no, not an unknown. When `explicit` (the caller named this exact
    path itself, e.g. a --flag), any of absent/wrong-type/undecidable is the caller's
    mistake to be told about: ([], reason)."""
    kind, err = dir_kind(path)
    if err is not None:
        return [], err
    if kind != "dir":
        if explicit:
            return [], ("not found" if kind == "absent" else "not a directory")
        return [], None
    try:
        return list(os.scandir(path)), None
    except OSError as e:
        return [], reason(e)
