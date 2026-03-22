"""Pydantic configuration models — mirror config/settings.example.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BitbucketSettings(BaseModel):
    server_url: str = Field(..., description="Bitbucket Server base URL")
    token: str = Field(default="", description="Token or ${ENV_VAR}")
    username: str = Field(default="x-token-auth", description="Basic user for PAT")
    project_key: str = Field(..., description="Project key")
    repository_slug: str = Field(..., description="Repo slug")
    pull_request_id: int = Field(..., ge=1, description="PR ID")
    api_path_prefix: str = Field(default="/rest/api/latest")
    verify_ssl: bool = True


class RepositorySettings(BaseModel):
    clone_url_override: str = ""
    pr_ref_strategy: str = Field(default="from", pattern="^(from|merge)$")


class PathsSettings(BaseModel):
    git: str = "git"
    maven: str = "mvn"
    java_home: str = ""
    workspace_root: str = Field(
        default="workspaces",
        description="Root directory for per-PR clones",
    )


class SpotbugsSettings(BaseModel):
    home: str = ""
    findsecbugs_plugin_jar: str = ""
    enabled: bool = False


class SemgrepSettings(BaseModel):
    executable: str = "semgrep"
    extra_args: list[str] = Field(default_factory=lambda: ["--config=p/java"])
    enabled: bool = False


class PmdSettings(BaseModel):
    executable: str = "pmd"
    rulesets: list[str] = Field(
        default_factory=lambda: ["category/java/errorprone.xml", "category/java/security.xml"]
    )
    enabled: bool = False


class DependencyCheckSettings(BaseModel):
    executable: str = ""
    enabled: bool = False


class SonarqubeSettings(BaseModel):
    scanner_path: str = "sonar-scanner"
    host_url: str = ""
    token: str = ""
    project_key: str = ""
    enabled: bool = False


class IdeSettings(BaseModel):
    intellij_path: str = ""
    eclipse_path: str = ""
    print_open_hints: bool = True


class PipelineSettings(BaseModel):
    maven_compile: bool = True
    maven_compile_args: list[str] = Field(
        default_factory=lambda: ["-q", "-DskipTests", "compile"]
    )
    maven_timeout_sec: int = 3600
    analyzer_timeout_sec: int = 1800


class ReportsSettings(BaseModel):
    output_subdir: str = "pr-review-reports"


class Settings(BaseModel):
    bitbucket: BitbucketSettings
    repository: RepositorySettings = Field(default_factory=RepositorySettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)
    spotbugs: SpotbugsSettings = Field(default_factory=SpotbugsSettings)
    semgrep: SemgrepSettings = Field(default_factory=SemgrepSettings)
    pmd: PmdSettings = Field(default_factory=PmdSettings)
    dependency_check: DependencyCheckSettings = Field(default_factory=DependencyCheckSettings)
    sonarqube: SonarqubeSettings = Field(default_factory=SonarqubeSettings)
    ide: IdeSettings = Field(default_factory=IdeSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    reports: ReportsSettings = Field(default_factory=ReportsSettings)

    def workspace_dir(self) -> Path:
        bb = self.bitbucket
        name = f"{bb.project_key}_{bb.repository_slug}_PR{bb.pull_request_id}"
        return Path(self.paths.workspace_root).resolve() / name

    def reports_dir(self) -> Path:
        return self.workspace_dir() / self.reports.output_subdir

    def clone_url(self) -> str:
        if self.repository.clone_url_override.strip():
            return self.repository.clone_url_override.strip()
        base = self.bitbucket.server_url.rstrip("/")
        pk = self.bitbucket.project_key
        slug = self.bitbucket.repository_slug
        return f"{base}/scm/{pk}/{slug}.git"
