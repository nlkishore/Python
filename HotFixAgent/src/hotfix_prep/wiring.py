"""Compose settings, Bitbucket client, git committer, and service."""

from __future__ import annotations

from pathlib import Path

from hotfix_prep.bitbucket.client import BitbucketServerClient
from hotfix_prep.commit.hotfix_committer import GitHotfixCommitter
from hotfix_prep.config import AppConfig, Settings, load_app_config
from hotfix_prep.idempotency.store import FileIdempotencyStore
from hotfix_prep.service import HotfixPrepService


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_service(
    settings: Settings | None = None,
    *,
    base_dir: Path | None = None,
) -> tuple[HotfixPrepService, AppConfig, BitbucketServerClient]:
    settings = settings or Settings()
    root = base_dir or package_root()
    config = load_app_config(settings, base_dir=root)
    bitbucket = BitbucketServerClient(
        settings.bitbucket_url,
        settings.bitbucket_username,
        settings.bitbucket_token,
        api_prefix=settings.bitbucket_api_prefix,
        verify_ssl=settings.bitbucket_verify_ssl,
    )
    committer = GitHotfixCommitter(
        username=settings.bitbucket_username,
        token=settings.bitbucket_token,
        timeout_seconds=settings.git_clone_timeout_seconds,
    )
    idem_dir = Path(settings.hotfix_prep_idem_dir)
    if not idem_dir.is_absolute():
        idem_dir = root / idem_dir
    store = FileIdempotencyStore(idem_dir)
    template = Path(settings.hotfix_prep_template)
    if not template.is_absolute():
        template = root / template
    service = HotfixPrepService(
        config,
        bitbucket,
        committer,
        store,
        template_path=template,
        base_dir=root,
    )
    return service, config, bitbucket
