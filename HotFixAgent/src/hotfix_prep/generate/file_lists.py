"""Generate filesList.txt YAML from mapped HotFix entries."""

from __future__ import annotations

import re
from typing import Any

import yaml

from hotfix_prep.models import FileListDocument, MappedEntry, MergedPrEvent


def extract_change_reason(event: MergedPrEvent) -> str:
    """Prefer CR-#### from branch or title."""
    for text in (event.from_branch, event.title):
        match = re.search(r"(CR[-_ ]?\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1).upper().replace(" ", "-").replace("_", "-")
    return f"PR-{event.pr_id}"


def build_file_list_document(
    event: MergedPrEvent,
    entries: list[MappedEntry],
    *,
    market_id: str,
    full_build_id: str = "",
) -> FileListDocument:
    baseline: dict[str, str] = {"release_commit": event.merge_commit}
    if full_build_id:
        baseline["full_build_id"] = full_build_id
    yaml_entries = [{"path": e.path, "reason": e.reason} for e in entries]
    return FileListDocument(
        version=1,
        baseline=baseline,
        source={
            "pr_id": event.pr_id,
            "market": market_id,
            "release_branch": event.to_branch,
            "from_branch": event.from_branch,
            "title": event.title,
        },
        entries=yaml_entries,
    )


def render_file_list_yaml(document: FileListDocument) -> str:
    payload: dict[str, Any] = document.model_dump()
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
