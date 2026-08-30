"""Patch or create buildScripts.sh without rewriting unrelated script logic."""

from __future__ import annotations

import re
from pathlib import Path

_ASSIGN_PATTERN = re.compile(
    r"^(export\s+)?(HF_NUMBER|TARGET_BRANCH|MARKET|PR_ID|RELEASE_COMMIT|FILE_LIST_NAME)\s*=.*$",
    re.MULTILINE,
)


def _assignment(name: str, value: str) -> str:
    safe = value.replace("\n", "").replace("\r", "")
    return f"export {name}={safe}"


def apply_variables(
    script: str,
    *,
    hf_number: str,
    target_branch: str,
    market: str,
    pr_id: str,
    release_commit: str,
    file_list_name: str,
) -> str:
    values = {
        "HF_NUMBER": hf_number,
        "TARGET_BRANCH": target_branch,
        "MARKET": market,
        "PR_ID": pr_id,
        "RELEASE_COMMIT": release_commit,
        "FILE_LIST_NAME": file_list_name,
    }

    def repl(match: re.Match[str]) -> str:
        name = match.group(2)
        return _assignment(name, values[name])

    updated, count = _ASSIGN_PATTERN.subn(repl, script)
    missing = [name for name in values if not re.search(rf"^(export\s+)?{name}\s*=", updated, re.M)]
    if missing:
        suffix = "\n" + "\n".join(_assignment(n, values[n]) for n in missing) + "\n"
        if not updated.endswith("\n"):
            updated += "\n"
        updated += suffix
    elif count == 0 and missing:
        pass
    return updated


def render_from_template(
    template_path: Path,
    *,
    hf_number: str,
    target_branch: str,
    market: str,
    pr_id: str,
    release_commit: str,
    file_list_name: str,
) -> str:
    text = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{HF_NUMBER}}": hf_number,
        "{{TARGET_BRANCH}}": target_branch,
        "{{MARKET}}": market,
        "{{PR_ID}}": pr_id,
        "{{RELEASE_COMMIT}}": release_commit,
        "{{FILE_LIST_NAME}}": file_list_name,
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def patch_or_template(
    existing: str | None,
    template_path: Path,
    **kwargs: str,
) -> str:
    if existing and existing.strip():
        return apply_variables(existing, **kwargs)  # type: ignore[arg-type]
    return render_from_template(template_path, **kwargs)  # type: ignore[arg-type]
