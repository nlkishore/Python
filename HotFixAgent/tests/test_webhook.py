import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from hotfix_prep.api.app import create_app
from hotfix_prep.bitbucket.signature import verify_signature
from hotfix_prep.bitbucket.webhook import parse_pr_merged_payload
from hotfix_prep.config import Settings
from hotfix_prep.exceptions import WebhookAuthError


PR_MERGED = {
    "eventKey": "pr:merged",
    "actor": {"name": "dev1"},
    "pullRequest": {
        "id": 1842,
        "title": "CR-1234: fix login",
        "fromRef": {
            "displayId": "feature/CR-1234-fix-login",
            "repository": {"slug": "core-app", "project": {"key": "BANK"}},
        },
        "toRef": {
            "displayId": "release/sg",
            "latestCommit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            "repository": {"slug": "core-app", "project": {"key": "BANK"}},
        },
        "properties": {
            "mergeCommit": {"id": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"}
        },
    },
}


def test_parse_pr_merged() -> None:
    event = parse_pr_merged_payload(PR_MERGED)
    assert event.pr_id == 1842
    assert event.to_branch == "release/sg"
    assert event.project == "BANK"
    assert event.merge_commit.startswith("deadbeef")


def test_signature_roundtrip() -> None:
    secret = "s3cret"
    body = b'{"ok":true}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    verify_signature(body, f"sha256={digest}", secret)
    try:
        verify_signature(body, "sha256=deadbeef", secret)
        raise AssertionError("expected WebhookAuthError")
    except WebhookAuthError:
        pass


def test_health() -> None:
    settings = Settings(allow_insecure_webhook=True, webhook_secret="")
    client = TestClient(create_app(settings))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_rejects_bad_signature() -> None:
    settings = Settings(webhook_secret="s3cret", allow_insecure_webhook=False)
    client = TestClient(create_app(settings))
    response = client.post(
        "/webhooks/bitbucket/pr-merged",
        content=json.dumps(PR_MERGED),
        headers={"X-Hub-Signature": "sha256=nope", "Content-Type": "application/json"},
    )
    assert response.status_code == 401
