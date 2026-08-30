"""Validate filesList YAML schema and paired-file presence before commit."""

from __future__ import annotations

from typing import Any

import yaml

from hotfix_prep.exceptions import ValidationError

_FORBIDDEN_SEGMENTS = frozenset({".."})


def validate_file_list_yaml(content: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValidationError(f"filesList.txt is not valid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError("filesList.txt must be a YAML mapping")
    if data.get("version") is None or int(data["version"]) < 1:
        raise ValidationError("filesList.txt version must be an integer >= 1")

    baseline = data.get("baseline") or {}
    if not isinstance(baseline, dict):
        raise ValidationError("baseline must be a mapping")
    release_commit = baseline.get("release_commit") or ""
    if not isinstance(release_commit, str) or len(release_commit) < 7:
        raise ValidationError("baseline.release_commit must be at least 7 characters")
    if "full_build_id" in baseline:
        build_id = baseline["full_build_id"]
        if not isinstance(build_id, str) or not build_id.strip():
            raise ValidationError("baseline.full_build_id must be a non-empty string when present")

    entries = data.get("entries")
    if not isinstance(entries, list) or len(entries) < 1:
        raise ValidationError("entries must be a non-empty list")

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("path"):
            raise ValidationError(f"entries[{index}] must have a non-empty path")
        path = str(entry["path"]).replace("\\", "/")
        parts = path.split("/")
        if any(part in _FORBIDDEN_SEGMENTS for part in parts) or path.startswith("/"):
            raise ValidationError(f"entries[{index}].path is not allowed: {path}")

    return data


def validate_paired_contents(files_list: str | None, build_scripts: str | None) -> None:
    if not files_list or not files_list.strip():
        raise ValidationError("filesList.txt is missing or empty")
    if not build_scripts or not build_scripts.strip():
        raise ValidationError("buildScripts.sh is missing or empty")
    validate_file_list_yaml(files_list)
