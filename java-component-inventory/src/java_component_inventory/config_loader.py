"""Load scan configuration from INI file."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScanConfig:
    base_folder: Path
    """Only these directory names (immediate children of base_folder)."""
    component_names: list[str]
    report_dir: Path
    detect_collisions: bool


def _parse_bool(value: str, default: bool = True) -> bool:
    v = (value or "").strip().lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off", ""):
        return False
    return default


def load_ini(path: str | Path) -> ScanConfig:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"INI file not found: {p}")

    cp = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    cp.read(p, encoding="utf-8")

    if not cp.has_section("paths"):
        raise ValueError("INI must contain [paths] section with base_folder")

    base_raw = cp.get("paths", "base_folder", fallback="").strip()
    if not base_raw:
        raise ValueError("paths.base_folder is required")
    base_folder = Path(base_raw).expanduser().resolve()
    if not base_folder.is_dir():
        raise NotADirectoryError(f"base_folder is not a directory: {base_folder}")

    comp_raw = ""
    if cp.has_section("scan"):
        comp_raw = cp.get("scan", "components", fallback="")
    components = [c.strip() for c in comp_raw.split(",") if c.strip()]
    if not components:
        raise ValueError(
            "scan.components is required (comma-separated folder names under base_folder)"
        )

    report_dir_raw = ""
    if cp.has_section("output"):
        report_dir_raw = cp.get("output", "report_dir", fallback="").strip()
    if report_dir_raw:
        report_dir = Path(report_dir_raw).expanduser().resolve()
    else:
        report_dir = base_folder / "java-inventory-reports"

    detect = True
    if cp.has_section("options"):
        detect = _parse_bool(cp.get("options", "detect_collisions", fallback="true"), True)

    return ScanConfig(
        base_folder=base_folder,
        component_names=components,
        report_dir=report_dir,
        detect_collisions=detect,
    )
