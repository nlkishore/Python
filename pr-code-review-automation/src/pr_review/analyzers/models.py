from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnalyzerRun:
    name: str
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
