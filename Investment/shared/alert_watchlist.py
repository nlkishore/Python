"""Load AlertApp watchlist from config.ini [watchlist] sections."""

from __future__ import annotations

import configparser
from pathlib import Path


def load_watchlist(base_dir: Path | None = None) -> dict[str, list[float]]:
    """
    Parse symbol = ref_price, up_pct, down_pct from the first config with [watchlist].
    Searches AlertApp/config.ini then parent config.ini.
    """
    script_dir = Path(__file__).resolve().parent.parent / "AlertApp"
    candidates = []
    if base_dir is not None:
        candidates.append(base_dir / "config.ini")
    candidates.extend(
        [
            script_dir / "config.ini",
            script_dir.parent / "config.ini",
        ]
    )

    seen: set[str] = set()
    for cfg_file in candidates:
        key = str(cfg_file.resolve())
        if key in seen:
            continue
        seen.add(key)
        if not cfg_file.is_file():
            continue
        parser = configparser.ConfigParser()
        parser.read(cfg_file, encoding="utf-8-sig")
        if not parser.has_section("watchlist"):
            continue
        out: dict[str, list[float]] = {}
        for sym, val in parser.items("watchlist"):
            parts = [p.strip() for p in val.split(",")]
            try:
                ref = float(parts[0]) if parts else 0.0
                up = float(parts[1]) if len(parts) > 1 else 0.0
                down = float(parts[2]) if len(parts) > 2 else 0.0
                out[sym.strip().upper()] = [ref, up, down]
            except (ValueError, IndexError):
                continue
        if out:
            return out

    return {"AAPL": [230.0, 2.0, 2.0], "TSLA": [320.0, 5.0, 5.0]}
