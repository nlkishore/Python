#!/usr/bin/env python3
"""
Convert legacy CP-1252 source files to UTF-8 and emit a report of non-ASCII / extended bytes.

For .java (and selected formats), classifies each extended character as comment vs literal vs code
for compile-impact hints. Heuristics are not a full parser — always review `high_*` rows.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

# CP-1252: every byte 0x00-0xFF maps to Unicode; UTF-8 can represent all of them.
ENCODING_IN = "cp1252"
ENCODING_OUT = "utf-8"
_TQ = '"' * 3  # text block delimiter (avoids quote-parsing edge cases)


@dataclass
class Finding:
    path: str
    line: int
    column: int
    offset: int
    codepoint: int
    char_repr: str
    category: str
    compile_impact: str
    note: str = ""


def build_java_regions(text: str) -> List[str]:
    """
    Single-pass: mark each character as comment | literal | code.
    Handles //, block comments, string and char literals, and triple-quoted text blocks (approximate).
    """
    n = len(text)
    r = ["code"] * n
    i = 0
    NORMAL, LINE, BLOCK, STR, CH = range(5)
    state = NORMAL

    while i < n:
        if state == NORMAL:
            if text[i] == "/" and i + 1 < n:
                if text[i + 1] == "/":
                    state = LINE
                    r[i] = r[i + 1] = "comment"
                    i += 2
                    continue
                if text[i + 1] == "*":
                    state = BLOCK
                    r[i] = r[i + 1] = "comment"
                    i += 2
                    continue
            if text[i] == '"' and i + 2 < n and text[i : i + 3] == _TQ:
                for j in range(i, min(i + 3, n)):
                    r[j] = "literal"
                i += 3
                end = text.find(_TQ, i)
                if end < 0:
                    while i < n:
                        r[i] = "literal"
                        i += 1
                    break
                while i < end:
                    r[i] = "literal"
                    i += 1
                for j in range(end, min(end + 3, n)):
                    r[j] = "literal"
                i = end + 3
                continue
            if text[i] == '"':
                state = STR
                r[i] = "literal"
                i += 1
                continue
            if text[i] == "'":
                state = CH
                r[i] = "literal"
                i += 1
                continue
            i += 1
            continue

        if state == LINE:
            r[i] = "comment"
            if text[i] in "\n\r":
                state = NORMAL
            i += 1
            continue

        if state == BLOCK:
            r[i] = "comment"
            if text[i] == "*" and i + 1 < n and text[i + 1] == "/":
                r[i + 1] = "comment"
                state = NORMAL
                i += 2
                continue
            i += 1
            continue

        if state == STR:
            r[i] = "literal"
            if text[i] == "\\" and i + 1 < n:
                r[i + 1] = "literal"
                i += 2
                continue
            if text[i] == '"':
                state = NORMAL
            i += 1
            continue

        if state == CH:
            r[i] = "literal"
            if text[i] == "\\" and i + 1 < n:
                r[i + 1] = "literal"
                i += 2
                continue
            if text[i] == "'":
                state = NORMAL
            i += 1
            continue

    return r


def build_properties_regions(text: str) -> List[str]:
    """Java .properties: #/! lines = comment; value side of = or : = literal."""
    n = len(text)
    r = ["code"] * n
    offset = 0
    for line in text.splitlines(keepends=True):
        line_core = line.rstrip("\r\n")
        core_len = len(line_core)
        stripped = line_core.lstrip()
        base = offset
        if stripped.startswith("#") or stripped.startswith("!"):
            for j in range(base, base + core_len):
                r[j] = "comment"
        elif "=" in line_core:
            eq = line_core.index("=")
            for j in range(base, base + eq + 1):
                r[j] = "code"
            for j in range(base + eq + 1, base + core_len):
                r[j] = "literal"
        elif ":" in line_core and not stripped.startswith(":"):
            c = line_core.find(":")
            for j in range(base, base + c + 1):
                r[j] = "code"
            for j in range(base + c + 1, base + core_len):
                r[j] = "literal"
        offset += len(line)
        if offset > n:
            break
    return r


def build_xml_regions(text: str) -> List[str]:
    """<!-- --> = comment; double/single quoted spans = literal (heuristic for attributes)."""
    n = len(text)
    r = ["code"] * n
    i = 0
    while i < n:
        if i + 3 < n and text[i : i + 4] == "<!--":
            end = text.find("-->", i)
            if end < 0:
                while i < n:
                    r[i] = "comment"
                    i += 1
                break
            while i < end + 3:
                r[i] = "comment"
                i += 1
            continue
        i += 1
    in_quote: Optional[str] = None
    i = 0
    while i < n:
        if r[i] == "comment":
            i += 1
            continue
        ch = text[i]
        if in_quote:
            r[i] = "literal"
            if ch == in_quote:
                in_quote = None
        else:
            if ch in '"\'':
                in_quote = ch
                r[i] = "literal"
        i += 1
    return r


def compile_impact_from_category(category: str) -> str:
    if category in ("comment", "text"):
        return "low_comment_only"
    if category == "literal":
        return "medium_string_or_char"
    return "high_review_code_or_markup"


def decode_text(
    raw: bytes,
    replace_replacement_char_with_space: bool,
    assume_cp1252_only: bool,
) -> Tuple[str, int, str]:
    """
    Try UTF-8 (strict) first so already-converted files are not misread as CP-1252.
    Returns (text, ufffd_count, encoding_label).
    """
    if not assume_cp1252_only:
        try:
            text = raw.decode("utf-8")
            return text, 0, "utf-8"
        except UnicodeDecodeError:
            pass
    text = raw.decode(ENCODING_IN, errors="replace")
    n = text.count("\ufffd")
    if replace_replacement_char_with_space and n:
        text = text.replace("\ufffd", " ")
    return text, n, ENCODING_IN


def line_col_from_offset(text: str, offset: int) -> Tuple[int, int]:
    """1-based line and column."""
    if offset > len(text):
        offset = len(text)
    prefix = text[:offset]
    line = prefix.count("\n") + 1
    last_nl = prefix.rfind("\n")
    col = offset - last_nl
    return line, col


def collect_non_ascii_findings(
    path: Path,
    text: str,
    suffix: str,
    replacement_events: int,
) -> List[Finding]:
    findings: List[Finding] = []
    regions: Optional[List[str]] = None
    if suffix == ".java":
        regions = build_java_regions(text)
    elif suffix == ".properties":
        regions = build_properties_regions(text)
    elif suffix in (
        ".xml",
        ".xhtml",
        ".html",
        ".jsp",
        ".jspf",
        ".jspx",
        ".tag",
        ".tld",
        ".vm",
        ".ftl",
    ):
        regions = build_xml_regions(text)

    for i, ch in enumerate(text):
        o = ord(ch)
        if o <= 127:
            continue
        if regions is not None and i < len(regions):
            cat = regions[i]
        elif suffix in (".md", ".txt", ".csv"):
            cat = "text"
        else:
            cat = "unknown"

        line, col = line_col_from_offset(text, i)
        findings.append(
            Finding(
                path=str(path),
                line=line,
                column=col,
                offset=i,
                codepoint=o,
                char_repr=repr(ch),
                category=cat,
                compile_impact=compile_impact_from_category(cat),
                note="",
            )
        )

    if replacement_events:
        findings.insert(
            0,
            Finding(
                path=str(path),
                line=0,
                column=0,
                offset=-1,
                codepoint=0,
                char_repr="",
                category="decode",
                compile_impact="high_review_code_or_markup",
                note=(
                    f"Decoder inserted U+FFFD {replacement_events} time(s); "
                    "file may be mixed encoding or binary — review before compile."
                ),
            ),
        )
    return findings


def should_process(path: Path, includes: Sequence[str], excludes: Sequence[str]) -> bool:
    name = path.name
    rel = str(path).replace("\\", "/")
    for ex in excludes:
        if fnmatch.fnmatch(name, ex) or fnmatch.fnmatch(rel, ex):
            return False
    if not includes:
        return True
    for inc in includes:
        if fnmatch.fnmatch(name, inc) or fnmatch.fnmatch(rel, inc):
            return True
    return False


def walk_files(root: Path, includes: Sequence[str], excludes: Sequence[str]) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in (".git", "target", "build", ".idea", "node_modules", "__pycache__")
            and not d.startswith("charset-migration-report")
        ]
        for fn in filenames:
            p = Path(dirpath) / fn
            if should_process(p, includes, excludes):
                yield p


def write_utf8(path: Path, text: str, bom: bool) -> None:
    data = ("\ufeff" + text if bom else text).encode(ENCODING_OUT)
    path.write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert CP-1252 sources to UTF-8 and report non-ASCII positions (with compile-impact hints for .java)."
    )
    ap.add_argument("--root", type=Path, required=True, help="Root directory to scan")
    ap.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Glob (file name or path). Repeatable. Default: common source extensions.",
    )
    ap.add_argument("--exclude", action="append", default=[], metavar="PATTERN", help="Glob to exclude. Repeatable.")
    ap.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Write report CSV/JSON here (default: <root>/charset-migration-report-<timestamp>)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Do not write converted files")
    ap.add_argument("--write", action="store_true", help="Write UTF-8 files (omit for report-only)")
    ap.add_argument("--backup-suffix", default=".cp1252.bak", help="Backup original with this suffix when writing")
    ap.add_argument("--utf8-bom", action="store_true", help="Write UTF-8 with BOM (optional)")
    ap.add_argument(
        "--replace-undecodable-with-space",
        action="store_true",
        help="Replace U+FFFD (from decode) with ASCII space",
    )
    ap.add_argument(
        "--assume-cp1252-only",
        action="store_true",
        help="Do not try UTF-8 first; force CP-1252 decode (for raw legacy trees only)",
    )
    args = ap.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2

    default_includes = [
        "*.java",
        "*.xml",
        "*.xhtml",
        "*.html",
        "*.jsp",
        "*.jspf",
        "*.jspx",
        "*.tag",
        "*.tld",
        "*.properties",
        "*.vm",
        "*.ftl",
        "*.js",
        "*.ts",
        "*.css",
        "*.json",
        "*.gradle",
        "*.md",
        "*.txt",
    ]
    includes = args.include if args.include else default_includes
    excludes = list(args.exclude) + ["*.cp1252.bak"]

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    report_dir = args.report_dir or (root / f"charset-migration-report-{ts}")
    report_dir.mkdir(parents=True, exist_ok=True)

    all_findings: List[Finding] = []
    processed = 0
    written = 0
    decoded_as_utf8 = 0
    decoded_as_cp1252 = 0

    for path in sorted(walk_files(root, includes, excludes)):
        try:
            raw = path.read_bytes()
        except OSError as e:
            print(f"SKIP read error {path}: {e}", file=sys.stderr)
            continue

        text, repl_count, enc_label = decode_text(
            raw, args.replace_undecodable_with_space, args.assume_cp1252_only
        )
        if enc_label == "utf-8":
            decoded_as_utf8 += 1
        else:
            decoded_as_cp1252 += 1
        suffix = path.suffix.lower()
        findings = collect_non_ascii_findings(path, text, suffix, repl_count)
        all_findings.extend(findings)
        processed += 1

        if args.write and not args.dry_run:
            if args.backup_suffix:
                bak = path.with_name(path.name + args.backup_suffix)
                try:
                    shutil.copy2(path, bak)
                except OSError as e:
                    print(f"ERROR backup {path}: {e}", file=sys.stderr)
                    return 1
            try:
                write_utf8(path, text, args.utf8_bom)
                written += 1
            except OSError as e:
                print(f"ERROR write {path}: {e}", file=sys.stderr)
                return 1

    csv_path = report_dir / "findings.csv"
    json_path = report_dir / "findings.json"
    summary_path = report_dir / "summary.txt"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "line",
                "column",
                "offset",
                "codepoint",
                "char_repr",
                "category",
                "compile_impact",
                "note",
            ],
        )
        w.writeheader()
        for fd in all_findings:
            w.writerow(asdict(fd))

    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in all_findings], f, indent=2)

    low = sum(1 for x in all_findings if x.compile_impact == "low_comment_only")
    med = sum(1 for x in all_findings if x.compile_impact == "medium_string_or_char")
    high = sum(1 for x in all_findings if x.compile_impact == "high_review_code_or_markup")

    summary_lines = [
        f"root={root}",
        f"files_scanned={processed}",
        f"decoded_as_utf8={decoded_as_utf8}",
        f"decoded_as_cp1252={decoded_as_cp1252}",
        f"files_written={written if args.write and not args.dry_run else 0}",
        f"dry_run={args.dry_run}",
        f"findings_total={len(all_findings)}",
        f"findings_low_comment_only={low}",
        f"findings_medium_literal={med}",
        f"findings_high_review={high}",
        "",
        "compile_impact legend:",
        "  low_comment_only    - non-ASCII in comments or plain text docs (usually no compile impact).",
        "  medium_string_or_char - in string/char literal or attribute-like span (runtime/display may change).",
        "  high_review_code_or_markup - identifiers/markup/heuristic unknown (review before OpenRewrite).",
        "",
        f"csv={csv_path}",
        f"json={json_path}",
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
