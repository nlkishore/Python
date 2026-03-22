"""Discover .java files and extract package + class name."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from java_component_inventory.config_loader import ScanConfig

_PACKAGE_RE = re.compile(
    r"^\s*package\s+([\w.]+)\s*;",
    re.MULTILINE,
)


@dataclass
class JavaFileRecord:
    component_name: str
    folder_name: str
    """Folder immediately containing the .java file (directory name only)."""
    package_name: str
    """Declared package, or empty if default package."""
    class_file_name: str
    relative_path: str
    """Path relative to component root."""
    fqn: str
    """Fully qualified name of public top-level type (package.Type)."""


def _read_package(java_path: Path) -> str:
    try:
        text = java_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = _PACKAGE_RE.search(text)
    return m.group(1) if m else ""


def iter_java_files(cfg: ScanConfig) -> list[JavaFileRecord]:
    records: list[JavaFileRecord] = []
    for comp in cfg.component_names:
        comp_path = (cfg.base_folder / comp).resolve()
        if not comp_path.is_dir():
            raise NotADirectoryError(
                f"Component folder not found under base_folder: {comp_path} "
                f"(expected direct child of {cfg.base_folder})"
            )
        for java_file in comp_path.rglob("*.java"):
            rel = java_file.relative_to(comp_path)
            parts = rel.parts
            if any(p in ("target", "build", "out", "bin") for p in parts):
                continue
            pkg = _read_package(java_file)
            stem = java_file.stem
            fqn = f"{pkg}.{stem}" if pkg else stem
            records.append(
                JavaFileRecord(
                    component_name=comp,
                    folder_name=java_file.parent.name,
                    package_name=pkg,
                    class_file_name=java_file.name,
                    relative_path=rel.as_posix(),
                    fqn=fqn,
                )
            )
    return records


def group_by_fqn(records: list[JavaFileRecord]) -> dict[str, list[JavaFileRecord]]:
    m: dict[str, list[JavaFileRecord]] = {}
    for r in records:
        m.setdefault(r.fqn, []).append(r)
    return {k: v for k, v in m.items() if len(v) > 1}
