"""Inventory zip / ear / war / jar members and SHA-256. Recurse nested archives one level."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from release_control.exceptions import InventoryError
from release_control.models import FileSet, normalize_path


_NESTED = (".war", ".jar", ".zip")


def inventory_archive(
    archive: Path,
    *,
    name: str = "archive",
    recurse_nested: bool = True,
) -> FileSet:
    if not archive.is_file():
        raise InventoryError(f"archive not found: {archive}")
    paths: list[str] = []
    digests: dict[str, str] = {}
    try:
        with zipfile.ZipFile(archive) as zf:
            _walk(zf, prefix="", paths=paths, digests=digests, recurse_nested=recurse_nested)
    except zipfile.BadZipFile as exc:
        raise InventoryError(f"not a zip/ear/war/jar: {archive}") from exc
    return FileSet(name=name, paths=sorted(set(paths)), digests=digests)


def digest_delta(left: FileSet, right: FileSet, *, name: str = "delta") -> FileSet:
    """Paths whose digest differs, or that exist on only one side."""
    keys = set(left.digests) | set(right.digests) | left.as_set() | right.as_set()
    changed: list[str] = []
    for path in sorted(keys):
        if left.digests.get(path) != right.digests.get(path):
            changed.append(path)
    return FileSet(name=name, paths=changed)


def _walk(
    zf: zipfile.ZipFile,
    *,
    prefix: str,
    paths: list[str],
    digests: dict[str, str],
    recurse_nested: bool,
) -> None:
    for info in zf.infolist():
        if info.is_dir():
            continue
        member = normalize_path(f"{prefix}{info.filename}")
        data = zf.read(info)
        paths.append(member)
        digests[member] = hashlib.sha256(data).hexdigest()
        if recurse_nested and member.lower().endswith(_NESTED):
            _walk_nested(data, prefix=member.rstrip("/") + "/", paths=paths, digests=digests)


def _walk_nested(
    payload: bytes,
    *,
    prefix: str,
    paths: list[str],
    digests: dict[str, str],
) -> None:
    import io

    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as nested:
            for info in nested.infolist():
                if info.is_dir():
                    continue
                member = normalize_path(f"{prefix}{info.filename}")
                data = nested.read(info)
                paths.append(member)
                digests[member] = hashlib.sha256(data).hexdigest()
    except zipfile.BadZipFile:
        return
