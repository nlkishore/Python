#!/usr/bin/env python3
"""
Analyze Maven dependency tree output and flag likely Java EE dependent libraries.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

DEP_PATTERN = re.compile(
    r"(?P<group>[a-zA-Z0-9_.-]+):(?P<artifact>[a-zA-Z0-9_.-]+):(?P<packaging>[a-zA-Z0-9_.-]+):(?P<version>[^: ]+)(?::(?P<scope>[a-zA-Z]+))?"
)

JAVA_EE_HINT_PREFIXES = (
    "javax.",
    "javaee.",
)

JAVA_EE_GROUP_EXACT = {
    "javax.servlet",
    "javax.persistence",
    "javax.validation",
    "javax.ws.rs",
    "javax.xml.bind",
    "javax.annotation",
    "javax.transaction",
    "javax.jms",
    "javax.mail",
    "javax.activation",
}


@dataclass
class DependencyHit:
    group_id: str
    artifact_id: str
    version: str
    scope: str
    packaging: str
    reason: str
    suggested_action: str
    notes: str


def classify(group_id: str, artifact_id: str) -> tuple[str, str, str]:
    g = group_id.lower()
    a = artifact_id.lower()

    if g in JAVA_EE_GROUP_EXACT or g.startswith(JAVA_EE_HINT_PREFIXES):
        return (
            "Direct Java EE coordinate",
            "upgrade-or-replace",
            "Find Jakarta equivalent (same vendor preferred).",
        )

    if "javaee" in a or "javax" in a:
        return (
            "Artifact name indicates Java EE dependency",
            "manual-review",
            "Check transitive dependencies and API usage before migration.",
        )

    if g.startswith("org.glassfish") and ("javax" in a or "javaee" in a):
        return (
            "Legacy Glassfish Java EE module",
            "replace",
            "Prefer Jakarta artifact line compatible with JDK 17.",
        )

    return ("", "", "")


def parse_dependency_tree(content: str) -> List[DependencyHit]:
    hits: List[DependencyHit] = []
    seen = set()

    for line in content.splitlines():
        match = DEP_PATTERN.search(line)
        if not match:
            continue

        group_id = match.group("group")
        artifact_id = match.group("artifact")
        packaging = match.group("packaging")
        version = match.group("version")
        scope = match.group("scope") or "compile"

        reason, action, notes = classify(group_id, artifact_id)
        if not reason:
            continue

        key = (group_id, artifact_id, version, scope)
        if key in seen:
            continue
        seen.add(key)

        hits.append(
            DependencyHit(
                group_id=group_id,
                artifact_id=artifact_id,
                version=version,
                scope=scope,
                packaging=packaging,
                reason=reason,
                suggested_action=action,
                notes=notes,
            )
        )

    return sorted(hits, key=lambda h: (h.group_id, h.artifact_id, h.version, h.scope))


def write_reports(hits: List[DependencyHit], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "javaee_dependency_report.csv"
    json_path = out_dir / "javaee_dependency_report.json"

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "group_id",
                "artifact_id",
                "version",
                "scope",
                "packaging",
                "reason",
                "suggested_action",
                "notes",
            ]
        )
        for hit in hits:
            writer.writerow(
                [
                    hit.group_id,
                    hit.artifact_id,
                    hit.version,
                    hit.scope,
                    hit.packaging,
                    hit.reason,
                    hit.suggested_action,
                    hit.notes,
                ]
            )

    with json_path.open("w", encoding="utf-8") as json_file:
        payload = {
            "count": len(hits),
            "items": [asdict(hit) for hit in hits],
        }
        json.dump(payload, json_file, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Identify likely Java EE dependent libraries from Maven dependency tree output."
    )
    parser.add_argument("--tree-file", required=True, help="Path to dependency:tree output file")
    parser.add_argument(
        "--out-dir",
        default="target/jakarta-compat-report",
        help="Output folder for CSV/JSON report",
    )
    args = parser.parse_args()

    tree_file = Path(args.tree_file)
    if not tree_file.exists():
        raise FileNotFoundError(f"Dependency tree file not found: {tree_file}")

    content = tree_file.read_text(encoding="utf-8", errors="replace")
    hits = parse_dependency_tree(content)
    out_dir = Path(args.out_dir)
    write_reports(hits, out_dir)

    print(f"Detected {len(hits)} Java EE candidate dependencies")
    print(f"CSV report: {out_dir / 'javaee_dependency_report.csv'}")
    print(f"JSON report: {out_dir / 'javaee_dependency_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
