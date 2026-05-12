#!/usr/bin/env python3
"""Shared config loader for the task system.

Reads `docs/developers/task-system.yaml` (or the path in the
`TASK_SYSTEM_CONFIG` env var) and returns a dict. Missing file or
missing keys fall back to the documented defaults — scripts never fail
because the config is absent.
"""
from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_CONFIG_PATH = "docs/developers/task-system.yaml"
ENV_VAR = "TASK_SYSTEM_CONFIG"

DEFAULTS: dict[str, Any] = {
    "ideas": {
        "enabled": True,
        "base_folder": "docs/developers/ideas",
    },
    "tasks": {
        "enabled": True,
        "base_folder": "docs/developers/tasks",
        "active": {"enabled": True},
        "paused": {"enabled": True},
        "epics": {"enabled": True},
        "releases": {"enabled": True},
    },
    "scripts": {"base_folder": "scripts"},
    "visualizations": {
        "epics": {"enabled": True, "style": "dependency-graph"},
        "kanban": {"enabled": True},
        "burnup": {"enabled": True},
    },
}


def _deep_merge(base: dict, overrides: dict) -> dict:
    out = deepcopy(base)
    for key, value in (overrides or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def config_path() -> Path:
    return Path(os.environ.get(ENV_VAR, DEFAULT_CONFIG_PATH))


def get(cfg: dict, *keys: str, default: Any = None) -> Any:
    """Safely walk nested config keys: get(cfg, 'tasks', 'active', 'enabled')."""
    node: Any = cfg
    for k in keys:
        if not isinstance(node, dict) or k not in node:
            return default
        node = node[k]
    return node


def paused_enabled(cfg: dict) -> bool:
    """Return True iff the paused status is effectively enabled.

    Paused depends on active: turning active off forces paused off too,
    because there is no `active` lifecycle to pause from.
    """
    return bool(get(cfg, "tasks", "active", "enabled", default=True)
                and get(cfg, "tasks", "paused", "enabled", default=True))


_KNOWN_TOP_LEVEL = frozenset(DEFAULTS.keys())
_KNOWN_TASKS_KEYS = frozenset({"enabled", "base_folder", "active", "paused", "epics", "releases"})
_KNOWN_IDEAS_KEYS = frozenset({"enabled", "base_folder"})
_KNOWN_VIZ_KEYS = frozenset({"epics", "kanban", "burnup"})
_KNOWN_VIZ_EPICS_KEYS = frozenset({"enabled", "style"})
_KNOWN_VIZ_KANBAN_KEYS = frozenset({"enabled"})
_KNOWN_VIZ_BURNUP_KEYS = frozenset({"enabled"})


def validate(loaded: dict, *, path: str = "") -> None:
    """Warn to stderr about unrecognised keys in the raw loaded config dict.

    Does not raise — the merged config (with defaults) is still usable.
    """
    label = f" in {path}" if path else ""

    unknown_top = set(loaded) - _KNOWN_TOP_LEVEL
    for k in sorted(unknown_top):
        print(
            f"task_system_config: unknown key '{k}'{label} — ignored.",
            file=sys.stderr,
        )

    def _check(section: dict | None, known: frozenset, section_name: str) -> None:
        if not isinstance(section, dict):
            return
        for k in sorted(set(section) - known):
            print(
                f"task_system_config: unknown key '{section_name}.{k}'{label} — ignored.",
                file=sys.stderr,
            )

    _check(loaded.get("tasks"), _KNOWN_TASKS_KEYS, "tasks")
    _check(loaded.get("ideas"), _KNOWN_IDEAS_KEYS, "ideas")
    viz = loaded.get("visualizations") or {}
    _check(viz, _KNOWN_VIZ_KEYS, "visualizations")
    _check(viz.get("epics"), _KNOWN_VIZ_EPICS_KEYS, "visualizations.epics")
    _check(viz.get("kanban"), _KNOWN_VIZ_KANBAN_KEYS, "visualizations.kanban")
    _check(viz.get("burnup"), _KNOWN_VIZ_BURNUP_KEYS, "visualizations.burnup")


def load(path: str | Path | None = None, *, warn=True) -> dict:
    """Return the merged config dict — defaults overlaid with file contents."""
    if path is None:
        path = config_path()
    p = Path(path)
    if not p.is_file():
        if warn:
            print(
                f"task_system_config: {p} not found — using defaults.",
                file=sys.stderr,
            )
        return deepcopy(DEFAULTS)
    if yaml is None:
        if warn:
            print(
                "task_system_config: PyYAML not installed —"
                " using defaults (pip install pyyaml to enable config).",
                file=sys.stderr,
            )
        return deepcopy(DEFAULTS)
    with p.open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f) or {}
    if warn:
        validate(loaded, path=str(p))
    return _deep_merge(DEFAULTS, loaded)


if __name__ == "__main__":
    import json
    print(json.dumps(load(), indent=2))
