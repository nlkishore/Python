"""Parse filesList.txt YAML (same keys as Case 1 / hotfix_validation)."""

from __future__ import annotations

import re
from typing import Any

import yaml

from release_control.exceptions import InventoryError
from release_control.models import FileSet, normalize_path


_PR_RE = re.compile(r"PR[-_]?(\d+)", re.IGNORECASE)


def parse_files_list(content: str, *, name: str = "hotfix_list") -> FileSet:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise InventoryError(f"filesList.txt is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise InventoryError("filesList.txt must be a YAML mapping")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise InventoryError("filesList.txt entries must be a non-empty list")
    paths: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("path"):
            raise InventoryError(f"entries[{index}] must have a path")
        path = normalize_path(str(entry["path"]))
        if ".." in path.split("/"):
            raise InventoryError(f"path must not contain '..': {path}")
        paths.append(path)
    pr_ids = _extract_pr_ids(data)
    return FileSet(
        name=name,
        paths=paths,
        extras={
            "pr_ids": pr_ids,
            "baseline": data.get("baseline") or {},
            "source": data.get("source") or {},
            "version": data.get("version"),
        },
    )


def _extract_pr_ids(data: dict[str, Any]) -> list[int]:
    found: list[int] = []
    source = data.get("source") or {}
    if isinstance(source, dict) and source.get("pr_id") is not None:
        found.append(int(source["pr_id"]))
    for entry in data.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        reason = str(entry.get("reason") or "")
        match = _PR_RE.search(reason)
        if match:
            found.append(int(match.group(1)))
    # preserve order, unique
    seen: set[int] = set()
    unique: list[int] = []
    for pr_id in found:
        if pr_id not in seen:
            seen.add(pr_id)
            unique.append(pr_id)
    return unique
