"""Environment configuration. Secrets come from env only."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bitbucket_url: str = "https://bitbucket.example.com"
    bitbucket_username: str = "x-token-auth"
    bitbucket_token: str = ""  # PAT — never a login password
    bitbucket_verify_ssl: bool = True
    bitbucket_api_prefix: str = "/rest/api/1.0"

    jenkins_url: str = ""
    jenkins_username: str = ""
    jenkins_token: str = ""  # Jenkins API token — never a login password
    jenkins_verify_ssl: bool = True

    artifactory_url: str = ""
    artifactory_username: str = ""
    artifactory_token: str = ""  # Artifactory access/identity token — never a login password
    artifactory_verify_ssl: bool = True

    log_level: str = "INFO"
    workdir: Path | None = None
    exceptions_file: Path = Path("config/exceptions.yaml")
    http_timeout_seconds: float = 60.0
