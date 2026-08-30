"""Pydantic models for events, mapping results, and process outcomes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RepoRef(BaseModel):
    project: str
    slug: str


class MarketConfig(BaseModel):
    id: str
    release_branches: list[str]
    hotfix_branch: str
    repo: RepoRef


class MappingDefaults(BaseModel):
    files_list_name: str = "filesList.txt"
    build_scripts_name: str = "buildScripts.sh"
    skip_globs: list[str] = Field(default_factory=list)
    java_roots: list[str] = Field(default_factory=lambda: ["src/main/java"])
    resource_roots: list[str] = Field(default_factory=lambda: ["src/main/resources"])
    webapp_roots: list[str] = Field(default_factory=lambda: ["src/main/webapp"])
    class_prefix: str = "WEB-INF/classes"
    skip_deleted: bool = True


class MarketsDocument(BaseModel):
    defaults: MappingDefaults = Field(default_factory=MappingDefaults)
    markets: list[MarketConfig]


class PrChange(BaseModel):
    path: str
    change_type: str = "MODIFY"


class MappedEntry(BaseModel):
    source_path: str
    path: str
    reason: str = ""


class MergedPrEvent(BaseModel):
    pr_id: int
    title: str = ""
    from_branch: str = ""
    to_branch: str
    merge_commit: str
    project: str
    slug: str
    author: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class FileListDocument(BaseModel):
    version: int = 1
    baseline: dict[str, str]
    source: dict[str, Any]
    entries: list[dict[str, str]]


class ProcessResult(BaseModel):
    status: Literal["success", "ignored", "already_processed", "dry_run", "failed"]
    message: str
    market_id: str | None = None
    pr_id: int | None = None
    merge_sha: str | None = None
    hotfix_branch: str | None = None
    files_list_name: str | None = None
    entry_count: int = 0
    hotfix_commit: str | None = None
    dry_run: bool = False
    files_list_yaml: str | None = None
    build_scripts_content: str | None = None
    error_code: str | None = None
