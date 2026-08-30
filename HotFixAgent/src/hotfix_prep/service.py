"""Orchestrate PR-merge → filesList + buildScripts → HotFix branch commit."""

from __future__ import annotations

import logging
from pathlib import Path

from hotfix_prep.bitbucket.client import BitbucketPort
from hotfix_prep.commit.hotfix_committer import HotfixCommitter
from hotfix_prep.config import AppConfig
from hotfix_prep.exceptions import HotfixPrepError
from hotfix_prep.generate.build_scripts import patch_or_template
from hotfix_prep.generate.file_lists import (
    build_file_list_document,
    extract_change_reason,
    render_file_list_yaml,
)
from hotfix_prep.generate.validator import validate_paired_contents
from hotfix_prep.idempotency.store import FileIdempotencyStore
from hotfix_prep.mapping.path_mapper import map_changes
from hotfix_prep.models import MergedPrEvent, ProcessResult

logger = logging.getLogger(__name__)


class HotfixPrepService:
    def __init__(
        self,
        config: AppConfig,
        bitbucket: BitbucketPort,
        committer: HotfixCommitter,
        store: FileIdempotencyStore,
        *,
        template_path: Path,
        base_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._bb = bitbucket
        self._committer = committer
        self._store = store
        self._template = template_path
        self._base_dir = base_dir or Path.cwd()

    def process(self, event: MergedPrEvent, *, dry_run: bool | None = None) -> ProcessResult:
        dry_run = self._config.settings.hotfix_prep_dry_run if dry_run is None else dry_run
        market = self._config.try_lookup(event.project, event.slug, event.to_branch)
        if market is None:
            logger.info(
                "Ignoring PR merge; target is not a mapped release branch",
                extra={"pr_id": event.pr_id},
            )
            return ProcessResult(
                status="ignored",
                message=f"Target branch {event.to_branch!r} is not a mapped market release branch",
                pr_id=event.pr_id,
                merge_sha=event.merge_commit,
                dry_run=dry_run,
            )

        key = FileIdempotencyStore.key(
            event.project, event.slug, event.pr_id, event.merge_commit
        )
        if not dry_run and self._store.already_succeeded(key):
            prior = self._store.get(key) or {}
            return ProcessResult(
                status="already_processed",
                message="This PR merge was already committed to HotFix",
                market_id=market.id,
                pr_id=event.pr_id,
                merge_sha=event.merge_commit,
                hotfix_branch=market.hotfix_branch,
                hotfix_commit=str(prior.get("hotfix_commit") or "") or None,
            )

        try:
            return self._run(event, market_id=market.id, dry_run=dry_run, idem_key=key)
        except HotfixPrepError as exc:
            logger.error(
                "HotFix prep failed: %s",
                exc.message,
                extra={"pr_id": event.pr_id, "market": market.id},
            )
            if not dry_run:
                self._store.record_failure(key, error_code=exc.code, message=exc.message)
            return ProcessResult(
                status="failed",
                message=exc.message,
                market_id=market.id,
                pr_id=event.pr_id,
                merge_sha=event.merge_commit,
                hotfix_branch=market.hotfix_branch,
                error_code=exc.code,
                dry_run=dry_run,
            )

    def _run(
        self,
        event: MergedPrEvent,
        *,
        market_id: str,
        dry_run: bool,
        idem_key: str,
    ) -> ProcessResult:
        market = self._config.lookup_market(event.project, event.slug, event.to_branch)
        defaults = self._config.defaults
        reason = extract_change_reason(event)

        changes = self._bb.iter_pr_changes(event.project, event.slug, event.pr_id)
        entries = map_changes(changes, defaults, reason=reason)

        document = build_file_list_document(event, entries, market_id=market.id)
        files_yaml = render_file_list_yaml(document)

        existing_script = self._bb.get_file(
            event.project, event.slug, market.hotfix_branch, defaults.build_scripts_name
        )
        template = self._template
        if not template.is_absolute():
            template = self._base_dir / template
        build_scripts = patch_or_template(
            existing_script,
            template,
            hf_number=reason,
            target_branch=event.to_branch,
            market=market.id,
            pr_id=str(event.pr_id),
            release_commit=event.merge_commit,
            file_list_name=defaults.files_list_name,
        )
        validate_paired_contents(files_yaml, build_scripts)

        message = (
            f"HotFix {market.id} {reason} from PR-{event.pr_id}\n\n"
            f"Automated: {defaults.files_list_name} + {defaults.build_scripts_name}\n"
            f"Release: {event.to_branch} @ {event.merge_commit[:12]}"
        )

        hotfix_sha: str | None = None
        if not dry_run:
            hotfix_sha = self._committer.commit_pair(
                clone_url=self._bb.clone_url(event.project, event.slug),
                hotfix_branch=market.hotfix_branch,
                files_list_name=defaults.files_list_name,
                files_list_content=files_yaml,
                build_scripts_name=defaults.build_scripts_name,
                build_scripts_content=build_scripts,
                message=message,
            )
            self._store.record_success(idem_key, hotfix_commit=hotfix_sha, market_id=market.id)
            comment = (
                f"HotFix prep committed `{defaults.files_list_name}` and "
                f"`{defaults.build_scripts_name}` to `{market.hotfix_branch}` "
                f"({len(entries)} entries, commit `{hotfix_sha[:12]}`)."
            )
            try:
                self._bb.add_pr_comment(event.project, event.slug, event.pr_id, comment)
            except HotfixPrepError:
                logger.warning(
                    "HotFix committed but PR comment failed",
                    extra={"pr_id": event.pr_id, "market": market.id},
                )

        status = "dry_run" if dry_run else "success"
        logger.info(
            "HotFix prep %s",
            status,
            extra={
                "pr_id": event.pr_id,
                "market": market.id,
                "merge_sha": event.merge_commit,
                "hotfix_branch": market.hotfix_branch,
                "entry_count": len(entries),
                "status": status,
            },
        )
        return ProcessResult(
            status=status,
            message="Dry-run generated HotFix metadata" if dry_run else "HotFix metadata committed",
            market_id=market.id,
            pr_id=event.pr_id,
            merge_sha=event.merge_commit,
            hotfix_branch=market.hotfix_branch,
            files_list_name=defaults.files_list_name,
            entry_count=len(entries),
            hotfix_commit=hotfix_sha,
            dry_run=dry_run,
            files_list_yaml=files_yaml if dry_run else None,
            build_scripts_content=build_scripts if dry_run else None,
        )


__all__ = ["HotfixPrepService"]
