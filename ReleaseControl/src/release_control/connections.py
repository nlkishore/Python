"""Load Settings once and open Bitbucket / Jenkins / Artifactory clients.

Auth is token-only (PAT / API token). Login passwords are rejected.
Import these factories in every new use case.
"""

from __future__ import annotations

import os

from release_control.clients.artifactory import ArtifactoryClient
from release_control.clients.bitbucket import BitbucketServerClient
from release_control.clients.jenkins import JenkinsClient
from release_control.config import Settings
from release_control.exceptions import ConfigError

_PASSWORD_ENV = (
    "BITBUCKET_PASSWORD",
    "JENKINS_PASSWORD",
    "ARTIFACTORY_PASSWORD",
)


def load_settings() -> Settings:
    """Single config entry: env and optional `.env`. Secrets never hardcoded."""
    _reject_password_env()
    return Settings()


def bitbucket_client(settings: Settings | None = None) -> BitbucketServerClient:
    s = settings or load_settings()
    token = _require_token("BITBUCKET", s.bitbucket_token)
    return BitbucketServerClient(
        s.bitbucket_url,
        s.bitbucket_username or "x-token-auth",
        token,
        api_prefix=s.bitbucket_api_prefix,
        verify_ssl=s.bitbucket_verify_ssl,
        timeout=s.http_timeout_seconds,
    )


def jenkins_client(settings: Settings | None = None) -> JenkinsClient:
    s = settings or load_settings()
    token = _require_token("JENKINS", s.jenkins_token)
    return JenkinsClient(
        s.jenkins_url,
        s.jenkins_username,
        token,
        verify_ssl=s.jenkins_verify_ssl,
        timeout=s.http_timeout_seconds,
    )


def artifactory_client(settings: Settings | None = None) -> ArtifactoryClient:
    s = settings or load_settings()
    token = _require_token("ARTIFACTORY", s.artifactory_token)
    return ArtifactoryClient(
        s.artifactory_url,
        s.artifactory_username,
        token,
        verify_ssl=s.artifactory_verify_ssl,
        timeout=s.http_timeout_seconds,
    )


def _reject_password_env() -> None:
    present = [name for name in _PASSWORD_ENV if os.environ.get(name)]
    if present:
        raise ConfigError(
            "Password credentials are not allowed. Use PAT/API tokens via "
            "BITBUCKET_TOKEN, JENKINS_TOKEN, ARTIFACTORY_TOKEN. Remove: "
            + ", ".join(present)
        )


def _require_token(system: str, token: str) -> str:
    value = (token or "").strip()
    if not value:
        raise ConfigError(
            f"{system} requires an API token (not a login password). "
            f"Set {system}_TOKEN in the environment."
        )
    return value
