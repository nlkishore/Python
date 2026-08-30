"""Parse Bitbucket Server pr:merged webhook payloads."""

from __future__ import annotations

from typing import Any

from hotfix_prep.exceptions import ValidationError
from hotfix_prep.models import MergedPrEvent


def parse_pr_merged_payload(payload: dict[str, Any]) -> MergedPrEvent:
    event_key = str(payload.get("eventKey") or payload.get("event_key") or "")
    pr = payload.get("pullRequest") or payload.get("pull_request")
    if not isinstance(pr, dict):
        raise ValidationError("Webhook payload is missing pullRequest")
    if event_key and event_key != "pr:merged":
        raise ValidationError(f"Unsupported eventKey: {event_key}")

    from_ref = pr.get("fromRef") or {}
    to_ref = pr.get("toRef") or {}
    from_repo = from_ref.get("repository") or {}
    to_repo = to_ref.get("repository") or from_repo
    project = ((to_repo.get("project") or {}).get("key")) or ""
    slug = to_repo.get("slug") or ""

    props = pr.get("properties") or {}
    merge = props.get("mergeCommit") or {}
    merge_sha = str(merge.get("id") or to_ref.get("latestCommit") or "")
    if not merge_sha:
        raise ValidationError("Webhook payload has no merge commit SHA")

    actor = payload.get("actor") or pr.get("author") or {}
    author = ""
    if isinstance(actor, dict):
        user = actor.get("user") if "user" in actor else actor
        if isinstance(user, dict):
            author = str(user.get("name") or user.get("displayName") or "")
        elif isinstance(actor.get("name"), str):
            author = actor["name"]

    try:
        pr_id = int(pr.get("id"))
    except (TypeError, ValueError) as exc:
        raise ValidationError("pullRequest.id is required") from exc

    if not project or not slug:
        raise ValidationError("Webhook payload is missing repository project/slug")

    return MergedPrEvent(
        pr_id=pr_id,
        title=str(pr.get("title") or ""),
        from_branch=str(from_ref.get("displayId") or ""),
        to_branch=str(to_ref.get("displayId") or ""),
        merge_commit=merge_sha,
        project=str(project),
        slug=str(slug),
        author=author,
        raw=payload,
    )
