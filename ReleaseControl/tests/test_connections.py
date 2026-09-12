import pytest

from release_control.clients.artifactory import ArtifactoryClient
from release_control.clients.bitbucket import BitbucketServerClient
from release_control.clients.jenkins import JenkinsClient
from release_control.config import Settings
from release_control.connections import (
    artifactory_client,
    bitbucket_client,
    jenkins_client,
    load_settings,
)
from release_control.exceptions import ConfigError


def test_load_settings_returns_settings():
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert settings.bitbucket_api_prefix.startswith("/rest/api")


def test_client_factories_require_tokens():
    settings = Settings(
        bitbucket_url="https://bb.example",
        jenkins_url="https://jk.example",
        artifactory_url="https://af.example",
        bitbucket_token="bb-pat",
        jenkins_token="jk-api",
        artifactory_token="af-token",
    )
    bb = bitbucket_client(settings)
    jk = jenkins_client(settings)
    af = artifactory_client(settings)
    try:
        assert isinstance(bb, BitbucketServerClient)
        assert isinstance(jk, JenkinsClient)
        assert isinstance(af, ArtifactoryClient)
    finally:
        bb.close()
        jk.close()
        af.close()


def test_missing_token_raises_config_error():
    settings = Settings(bitbucket_url="https://bb.example", bitbucket_token="")
    with pytest.raises(ConfigError, match="BITBUCKET"):
        bitbucket_client(settings)


def test_password_env_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BITBUCKET_PASSWORD", "secret")
    with pytest.raises(ConfigError, match="Password credentials are not allowed"):
        load_settings()
