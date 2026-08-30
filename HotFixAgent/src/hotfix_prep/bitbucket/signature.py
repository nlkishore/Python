"""HMAC verification for Bitbucket Server webhook secret."""

from __future__ import annotations

import hashlib
import hmac

from hotfix_prep.exceptions import WebhookAuthError


def verify_signature(body: bytes, signature_header: str | None, secret: str) -> None:
    if not secret:
        raise WebhookAuthError("WEBHOOK_SECRET is not configured")
    if not signature_header:
        raise WebhookAuthError("Missing X-Hub-Signature header")
    provided = signature_header.strip()
    if provided.lower().startswith("sha256="):
        provided = provided.split("=", 1)[1]
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise WebhookAuthError("Invalid webhook signature")
