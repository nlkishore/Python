"""Map PR source paths to HotFix binary paths. Fail if any kept path cannot be mapped."""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath

from hotfix_prep.exceptions import EmptyFileListError, UnmappedPathError
from hotfix_prep.models import MappedEntry, MappingDefaults, PrChange


_SKIP_TYPES = frozenset({"DELETE", "REMOVED"})


def _normalize(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/"))).lstrip("./")


def _glob_match(path: str, pattern: str) -> bool:
    """Match POSIX path against a glob. ``**`` means any number of directories."""
    pat = pattern.replace("\\", "/")
    if fnmatch.fnmatch(path, pat):
        return True
    if fnmatch.fnmatch(PurePosixPath(path).name, pat):
        return True
    if pat.startswith("**/"):
        rest = pat[3:]
        if rest.endswith("/**"):
            prefix = rest[:-3]
            if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
                return True
        parts = path.split("/")
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            if fnmatch.fnmatch(suffix, rest) or suffix == rest:
                return True
            if rest.endswith("/**"):
                prefix = rest[:-3]
                if suffix == prefix or suffix.startswith(prefix + "/"):
                    return True
    return False


def _matches_any(path: str, globs: list[str]) -> bool:
    posix = _normalize(path)
    return any(_glob_match(posix, pattern) for pattern in globs)


def _strip_root(path: str, root: str) -> str | None:
    posix = _normalize(path)
    prefix = _normalize(root).rstrip("/") + "/"
    if posix.startswith(prefix):
        return posix[len(prefix) :]
    if posix == _normalize(root):
        return ""
    return None


def map_single(path: str, defaults: MappingDefaults) -> str | None:
    """Return mapped HotFix path, or None if the file should be skipped (not an error)."""
    posix = _normalize(path)
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

    return ""  # empty string means unmapped (caller distinguishes skip None vs unmapped "")


def map_changes(
    changes: list[PrChange],
    defaults: MappingDefaults,
    *,
    reason: str = "",
) -> list[MappedEntry]:
    mapped: list[MappedEntry] = []
    unmapped: list[str] = []
    seen: set[str] = set()

    for change in changes:
        change_type = (change.change_type or "MODIFY").upper()
        if defaults.skip_deleted and change_type in _SKIP_TYPES:
            continue
        posix = _normalize(change.path)
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
        raise UnmappedPathError(unmapped)
    if not mapped:
        raise EmptyFileListError()
    return mapped
