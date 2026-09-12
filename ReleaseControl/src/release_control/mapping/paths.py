"""Map PR source paths to binary paths. Keep in sync with hotfix_prep.mapping.path_mapper."""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath

from release_control.exceptions import MappingError
from release_control.models import MappedEntry, MappingDefaults, PrChange, normalize_path


_SKIP_TYPES = frozenset({"DELETE", "REMOVED"})


def _glob_match(path: str, pattern: str) -> bool:
    pat = pattern.replace("\\", "/")
    if fnmatch.fnmatch(path, pat):
        return True
    if fnmatch.fnmatch(PurePosixPath(path).name, pat):
        return True
    if pat.startswith("**/"):
        rest = pat[3:]
        parts = path.split("/")
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            if fnmatch.fnmatch(suffix, rest) or suffix == rest:
                return True
    return False


def _matches_any(path: str, globs: list[str]) -> bool:
    posix = normalize_path(path)
    return any(_glob_match(posix, pattern) for pattern in globs)


def _strip_root(path: str, root: str) -> str | None:
    posix = normalize_path(path)
    prefix = normalize_path(root).rstrip("/") + "/"
    if posix.startswith(prefix):
        return posix[len(prefix) :]
    if posix == normalize_path(root):
        return ""
    return None


def map_single(path: str, defaults: MappingDefaults) -> str | None:
    posix = normalize_path(path)
    if _matches_any(posix, defaults.skip_globs):
        return None
    for java_root in defaults.java_roots:
        rel = _strip_root(posix, java_root)
        if rel is not None:
            if rel.endswith(".java"):
                class_rel = rel[: -len(".java")] + ".class"
                return f"{defaults.class_prefix.rstrip('/')}/{class_rel}"
            return f"{defaults.class_prefix.rstrip('/')}/{rel}"
    for res_root in defaults.resource_roots:
        rel = _strip_root(posix, res_root)
        if rel is not None:
            return f"{defaults.class_prefix.rstrip('/')}/{rel}"
    for web_root in defaults.webapp_roots:
        rel = _strip_root(posix, web_root)
        if rel is not None:
            return rel
    return ""


def map_changes(
    changes: list[PrChange],
    defaults: MappingDefaults | None = None,
    *,
    reason: str = "",
    allow_empty: bool = False,
) -> list[MappedEntry]:
    defaults = defaults or MappingDefaults()
    mapped: list[MappedEntry] = []
    unmapped: list[str] = []
    seen: set[str] = set()
    for change in changes:
        change_type = (change.change_type or "MODIFY").upper()
        if defaults.skip_deleted and change_type in _SKIP_TYPES:
            continue
        posix = normalize_path(change.path)
        if _matches_any(posix, defaults.skip_globs):
            continue
        target = map_single(posix, defaults)
        if target is None:
            continue
        if target == "":
            unmapped.append(posix)
            continue
        if target in seen:
            continue
        seen.add(target)
        mapped.append(MappedEntry(source_path=posix, path=target, reason=reason))
    if unmapped:
        raise MappingError(
            f"Source paths have no binary mapping: {', '.join(unmapped[:20])}",
            paths=unmapped,
        )
    if not mapped and not allow_empty:
        raise MappingError("No HotFix entries after mapping and filtering")
    return mapped
