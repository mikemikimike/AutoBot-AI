# Copyright 2025-2026 mrveiss
# SPDX-License-Identifier: Apache-2.0
# AutoBot - AI-Powered Automation Platform
# Author: mrveiss
"""No two tracked scripts share one import name (#14873, #15580).

`shared/scripts` is a flat sys.path root: its tests load siblings by bare name, so two files
called `optimize_agents.py` bound one `sys.modules` slot and the loser's tests ran against the
other tool. They were two different tools (one collapses a policy section, one strips code
blocks), so the fix was a rename, not a merge. This guard keeps the import name unique.
"""

from __future__ import annotations

import collections
from pathlib import PurePosixPath

import pytest
from repo_tests._paths import repo_root
from repo_tests._reach import declare

from tools.lint._scan_helpers import EmptyEnumeration, tracked_paths

_ROOT = "autobot-infrastructure/shared/scripts"

#: Basenames that are legitimately repeated (package markers, pytest plumbing).
_EXEMPT_NAMES = frozenset({"__init__.py", "conftest.py"})

#: Known forks not yet resolved. May only shrink; each needs its own de-fork.
_GRANDFATHERED = {
    "fresh_kb_setup.py": (
        f"{_ROOT}/fresh_kb_setup.py",
        f"{_ROOT}/setup/knowledge/fresh_kb_setup.py",
    ),
}


def _python_modules(root) -> list[str]:
    try:
        return [p for p in tracked_paths(root, _ROOT) if p.endswith(".py")]
    except EmptyEnumeration:
        return []


REACH = declare(
    "script-module-name-scan",
    discover=_python_modules,
    # Mid-window, from REACH.window().
    floor=181,
    what="tracked python scripts",
    roots=(_ROOT,),
    growth=100,
)


def shared_names(paths: list[str]) -> dict[str, tuple[str, ...]]:
    """Basename -> the paths sharing it, for every basename held by more than one file."""
    by_name: dict[str, list[str]] = collections.defaultdict(list)
    for rel in paths:
        name = PurePosixPath(rel).name
        if name not in _EXEMPT_NAMES:
            by_name[name].append(rel)
    return {n: tuple(sorted(v)) for n, v in by_name.items() if len(v) > 1}


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["a/optimize_agents.py", "a/utilities/optimize_agents.py"], {"optimize_agents.py"}),
        (["a/collapse_agent_policy.py", "a/utilities/optimize_agents.py"], set()),
        (["a/__init__.py", "a/b/__init__.py", "a/conftest.py", "a/b/conftest.py"], set()),
    ],
)
def test_the_matcher_tells_a_shared_name_from_distinct_ones(paths: list[str], expected: set[str]) -> None:
    assert set(shared_names(paths)) == expected


def test_no_two_scripts_share_an_import_name() -> None:
    found = shared_names(list(REACH.examined(repo_root())))
    new = {n: v for n, v in found.items() if _GRANDFATHERED.get(n) != v}
    assert not new, (
        f"#14873: {new} share an import name; the second one to import it shadows the first. "
        "Different tools: rename one. Same concept: merge onto one module."
    )
    stale = [n for n in _GRANDFATHERED if n not in found]
    assert not stale, f"{stale} are no longer forked: drop them from _GRANDFATHERED"
