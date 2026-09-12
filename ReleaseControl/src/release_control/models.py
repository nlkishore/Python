"""Shared models: file sets, mapped paths, reconcile outcomes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ReconcileStatus = Literal["PASS", "REVIEW", "FAIL"]


class PrChange(BaseModel):
    path: str
    change_type: str = "MODIFY"


class MappedEntry(BaseModel):
    source_path: str
    path: str
    reason: str = ""


class MappingDefaults(BaseModel):
    skip_globs: list[str] = Field(
        default_factory=lambda: [
            "**/pom.xml",
            "**/*Test.java",
            "**/src/test/**",
            "**/*.md",
            "**/.gitignore",
        ]
    )
    java_roots: list[str] = Field(default_factory=lambda: ["src/main/java"])
    resource_roots: list[str] = Field(default_factory=lambda: ["src/main/resources"])
    webapp_roots: list[str] = Field(default_factory=lambda: ["src/main/webapp"])
    class_prefix: str = "WEB-INF/classes"
    skip_deleted: bool = True


class FileSet(BaseModel):
    name: str
    paths: list[str] = Field(default_factory=list)
    digests: dict[str, str] = Field(default_factory=dict)
    extras: dict[str, Any] = Field(default_factory=dict)

    def as_set(self) -> set[str]:
        return {normalize_path(p) for p in self.paths}


class ArtifactRef(BaseModel):
    uri: str
    sha256: str = ""
    local_path: str = ""
    source: str = ""


class ExceptionRule(BaseModel):
    glob: str | None = None
    path: str | None = None
    class_name: str = Field(alias="class", default="skip")
    package: str | None = None
    note: str = ""
    owner: str = ""
    ticket: str = ""

    model_config = {"populate_by_name": True}


class SetDiff(BaseModel):
    left_name: str
    right_name: str
    missing_in_right: list[str] = Field(default_factory=list)
    extra_in_right: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_in_right and not self.extra_in_right


class ReconcileReport(BaseModel):
    run_id: str
    status: ReconcileStatus
    diffs: list[SetDiff] = Field(default_factory=list)
    exceptions_applied: list[str] = Field(default_factory=list)
    review_items: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    timestamps: dict[str, datetime] = Field(default_factory=dict)
    lead_time_seconds: float | None = None
    message: str = ""
    extras: dict[str, Any] = Field(default_factory=dict)

    def to_cli_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["status"] = self.status
        return payload


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./").lstrip("/")
