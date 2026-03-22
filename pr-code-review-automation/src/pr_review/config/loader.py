"""Load YAML settings with ${ENV_VAR} substitution."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from pr_review.config.schema import Settings

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute_env(obj: Any) -> Any:
    if isinstance(obj, str):
        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            return os.environ.get(key, "")

        return _ENV_PATTERN.sub(repl, obj)
    if isinstance(obj, dict):
        return {k: _substitute_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env(x) for x in obj]
    return obj


def load_settings(path: str | Path) -> Settings:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Config not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")
    data = _substitute_env(raw)
    return Settings.model_validate(data)
