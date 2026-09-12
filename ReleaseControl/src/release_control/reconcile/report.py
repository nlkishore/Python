"""Assemble PASS / REVIEW / FAIL from set diffs and exception leftovers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from release_control.models import (
    ArtifactRef,
    FileSet,
    ReconcileReport,
    ReconcileStatus,
    SetDiff,
)
from release_control.reconcile.exceptions_registry import ExceptionRegistry
from release_control.reconcile.sets import compare_equal, compare_subset


def apply_exceptions(file_set: FileSet, registry: ExceptionRegistry) -> tuple[FileSet, list[str], list[str]]:
    kept, dropped, review = registry.drop_from_equation(file_set.as_set())
    return (
        FileSet(
            name=file_set.name,
            paths=sorted(kept),
            digests={k: v for k, v in file_set.digests.items() if k in kept},
            extras=file_set.extras,
        ),
        dropped,
        review,
    )


def build_report(
    *,
    pr_mapped: FileSet,
    hotfix_list: FileSet,
    hotfix_zip: FileSet | None = None,
    full_binary: FileSet | None = None,
    patched: FileSet | None = None,
    uat_prod_delta: FileSet | None = None,
    registry: ExceptionRegistry | None = None,
    artifacts: list[ArtifactRef] | None = None,
    timestamps: dict[str, datetime] | None = None,
    run_id: str | None = None,
) -> ReconcileReport:
    registry = registry or ExceptionRegistry([])
    dropped_all: list[str] = []
    review_all: list[str] = []

    def clean(fs: FileSet) -> FileSet:
        cleaned, dropped, review = apply_exceptions(fs, registry)
        dropped_all.extend(dropped)
        review_all.extend(review)
        return cleaned

    pr_c = clean(pr_mapped)
    hf_c = clean(hotfix_list)
    diffs: list[SetDiff] = [compare_equal(pr_c, hf_c)]

    if hotfix_zip is not None:
        diffs.append(compare_subset(hf_c, clean(hotfix_zip)))
    if full_binary is not None:
        diffs.append(compare_subset(hf_c, clean(full_binary)))
    if patched is not None:
        diffs.append(compare_subset(hf_c, clean(patched)))
    if uat_prod_delta is not None:
        diffs.append(compare_equal(hf_c, clean(uat_prod_delta)))

    hard_fail = any(not diff.ok for diff in diffs)
    status: ReconcileStatus
    if hard_fail:
        status = "FAIL"
        message = "Incremental file lists do not match after exceptions"
    elif review_all:
        status = "REVIEW"
        message = "Lists match; manual exceptions need sign-off"
    else:
        status = "PASS"
        message = "PR, HotFix, and binary inventories match"

    stamps = timestamps or {}
    lead = None
    if "t_pr_merged" in stamps and "t_reconcile" in stamps:
        lead = (stamps["t_reconcile"] - stamps["t_pr_merged"]).total_seconds()
    elif "t_pr_merged" in stamps:
        lead = (datetime.now(timezone.utc) - stamps["t_pr_merged"]).total_seconds()

    return ReconcileReport(
        run_id=run_id or uuid4().hex,
        status=status,
        diffs=diffs,
        exceptions_applied=sorted(set(dropped_all)),
        review_items=sorted(set(review_all)),
        artifacts=artifacts or [],
        timestamps=stamps,
        lead_time_seconds=lead,
        message=message,
        extras={
            "pr_count": len(pr_c.paths),
            "hotfix_count": len(hf_c.paths),
            "pr_ids": hotfix_list.extras.get("pr_ids") or [],
        },
    )
