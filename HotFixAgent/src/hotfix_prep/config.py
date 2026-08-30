"""Environment and markets.yaml configuration. Secrets come from env only."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from hotfix_prep.exceptions import ConfigError, UnmappedMarketError
from hotfix_prep.models import MarketConfig, MarketsDocument, MappingDefaults


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bitbucket_url: str = "https://bitbucket.example.com"
    bitbucket_username: str = ""
    bitbucket_token: str = ""
    bitbucket_verify_ssl: bool = True
    bitbucket_api_prefix: str = "/rest/api/1.0"

    webhook_secret: str = ""
    allow_insecure_webhook: bool = False

    hotfix_prep_markets_config: str = "config/markets.yaml"
    hotfix_prep_template: str = "templates/buildScripts.sh.j2"
    hotfix_prep_idem_dir: str = ".idempotency"
    hotfix_prep_dry_run: bool = False
    git_clone_timeout_seconds: int = 120
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8080


class AppConfig:
    """Loaded markets document plus runtime settings."""

    def __init__(self, settings: Settings, document: MarketsDocument, config_dir: Path) -> None:
        self.settings = settings
        self.document = document
        self.config_dir = config_dir
        self._by_branch: dict[tuple[str, str, str], MarketConfig] = {}
        for market in document.markets:
            project = market.repo.project.upper()
            slug = market.repo.slug.lower()
            for branch in market.release_branches:
                key = (project, slug, branch)
                if key in self._by_branch:
                    raise ConfigError(
                        f"Duplicate release branch mapping: {project}/{slug} {branch}"
                    )
                self._by_branch[key] = market

    @property
    def defaults(self) -> MappingDefaults:
        return self.document.defaults

    def lookup_market(self, project: str, slug: str, release_branch: str) -> MarketConfig:
        key = (project.upper(), slug.lower(), release_branch)
        market = self._by_branch.get(key)
        if market is None:
            raise UnmappedMarketError(release_branch)
        return market

    def try_lookup(self, project: str, slug: str, release_branch: str) -> MarketConfig | None:
        return self._by_branch.get((project.upper(), slug.lower(), release_branch))


def load_markets_document(path: Path) -> MarketsDocument:
    if not path.is_file():
        raise ConfigError(f"Markets config not found: {path}")
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    try:
        return MarketsDocument.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — surface YAML/schema issues as ConfigError
        raise ConfigError(f"Invalid markets config {path}: {exc}") from exc


def load_app_config(settings: Settings | None = None, *, base_dir: Path | None = None) -> AppConfig:
    settings = settings or Settings()
    root = base_dir or Path.cwd()
    config_path = Path(settings.hotfix_prep_markets_config)
    if not config_path.is_absolute():
        config_path = root / config_path
    document = load_markets_document(config_path)
    return AppConfig(settings, document, config_path.parent)


def redact_secret(value: str, visible: int = 0) -> str:
    if not value:
        return ""
    if visible <= 0:
        return "***"
    return value[:visible] + "***"
