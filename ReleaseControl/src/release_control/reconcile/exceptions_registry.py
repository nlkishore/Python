"""Exception registry: skip / generated / overlay / config_zip / manual."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

from release_control.exceptions import ConfigError
from release_control.models import ExceptionRule, normalize_path


_DROP_CLASSES = frozenset({"skip", "generated", "overlay"})
_REVIEW_CLASSES = frozenset({"manual"})
_CONFIG_CLASSES = frozenset({"config_zip"})


class ExceptionRegistry:
    def __init__(self, rules: list[ExceptionRule]) -> None:
        self.rules = rules

    @classmethod
    def from_yaml(cls, path: Path) -> ExceptionRegistry:
        if not path.is_file():
            raise ConfigError(f"exceptions file not found: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw = data.get("exceptions") if isinstance(data, dict) else None
        if raw is None:
            return cls([])
        if not isinstance(raw, list):
            raise ConfigError("exceptions must be a list")
        rules = [ExceptionRule.model_validate(item) for item in raw]
        return cls(rules)

    def classify(self, path: str) -> ExceptionRule | None:
        posix = normalize_path(path)
        for rule in self.rules:
            if rule.path and normalize_path(rule.path) == posix:
                return rule
            if rule.glob and (
                fnmatch.fnmatch(posix, rule.glob)
                or fnmatch.fnmatch(posix.split("/")[-1], rule.glob)
            ):
                return rule
        return None

    def drop_from_equation(self, paths: set[str]) -> tuple[set[str], list[str], list[str]]:
        """Return (kept, dropped labels, review labels)."""
        kept: set[str] = set()
        dropped: list[str] = []
        review: list[str] = []
        for path in paths:
            rule = self.classify(path)
            if rule is None:
                kept.add(path)
                continue
            label = f"{path} [{rule.class_name}]"
            if rule.class_name in _DROP_CLASSES:
                dropped.append(label)
            elif rule.class_name in _REVIEW_CLASSES:
                if not rule.owner or not rule.ticket:
                    kept.add(path)
                    review.append(f"{path} [manual missing owner/ticket]")
                else:
                    review.append(f"{label} {rule.ticket} {rule.owner}")
            elif rule.class_name in _CONFIG_CLASSES:
                dropped.append(f"{label} -> {rule.package or 'config.zip'}")
            else:
                kept.add(path)
        return kept, dropped, review
