"""Wire Bitbucket REST inventories into the reconcile report. No local git."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from release_control.clients.bitbucket import BitbucketServerClient
from release_control.inventory.fileslist import parse_files_list
from release_control.mapping.paths import map_changes
from release_control.models import (
    ArtifactRef,
    FileSet,
    MappingDefaults,
    ReconcileReport,
)
from release_control.reconcile.exceptions_registry import ExceptionRegistry
from release_control.reconcile.report import build_report


def collect_pr_set(
    bitbucket: BitbucketServerClient,
    *,
    project: str,
    slug: str,
    pr_id: int,
    defaults: MappingDefaults | None = None,
) -> FileSet:
    changes = bitbucket.iter_pr_changes(project, slug, pr_id)
    mapped = map_changes(changes, defaults, reason=f"PR-{pr_id}")
    return FileSet(
        name="pr_mapped",
        paths=[entry.path for entry in mapped],
        extras={
            "pr_id": pr_id,
            "source_paths": [entry.source_path for entry in mapped],
        },
    )


def collect_hotfix_set(
    bitbucket: BitbucketServerClient,
    *,
    project: str,
    slug: str,
    branch: str,
    files_list_name: str = "filesList.txt",
) -> FileSet:
    content = bitbucket.get_raw_file(project, slug, branch, files_list_name)
    if content is None:
        from release_control.exceptions import InventoryError

        raise InventoryError(f"{files_list_name} not found on {project}/{slug} {branch}")
    return parse_files_list(content, name="hotfix_list")


def run_from_sets(
    *,
    pr_mapped: FileSet,
    hotfix_list: FileSet,
    hotfix_zip: FileSet | None = None,
    full_binary: FileSet | None = None,
    patched: FileSet | None = None,
    uat_prod_delta: FileSet | None = None,
    registry: ExceptionRegistry | None = None,
    artifacts: list[ArtifactRef] | None = None,
) -> ReconcileReport:
    now = datetime.now(timezone.utc)
    return build_report(
        pr_mapped=pr_mapped,
        hotfix_list=hotfix_list,
        hotfix_zip=hotfix_zip,
        full_binary=full_binary,
        patched=patched,
        uat_prod_delta=uat_prod_delta,
        registry=registry,
        artifacts=artifacts,
        timestamps={"t_reconcile": now},
        run_id=uuid4().hex,
    )
