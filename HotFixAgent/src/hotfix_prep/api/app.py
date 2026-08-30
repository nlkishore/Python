"""FastAPI webhook and health endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hotfix_prep.bitbucket.signature import verify_signature
from hotfix_prep.bitbucket.webhook import parse_pr_merged_payload
from hotfix_prep.config import Settings
from hotfix_prep.exceptions import HotfixPrepError, ValidationError, WebhookAuthError
from hotfix_prep.logging_config import configure_logging
from hotfix_prep.models import ProcessResult
from hotfix_prep.wiring import build_service

logger = logging.getLogger(__name__)

_TRANSIENT_CODES = frozenset({"bitbucket_error", "commit_error"})


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str = "ok"


class ProcessRequest(BaseModel):
    project: str
    slug: str
    pr_id: int = Field(..., ge=1)
    dry_run: bool = False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    service, _config, bitbucket = build_service(settings)

    app = FastAPI(title="HotFix Prep", version="0.1.0")
    app.state.service = service
    app.state.settings = settings
    app.state.bitbucket = bitbucket

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/webhooks/bitbucket/pr-merged",
        response_model=ProcessResult,
        responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    async def pr_merged(
        request: Request,
        x_hub_signature: str | None = Header(default=None, alias="X-Hub-Signature"),
        x_event_key: str | None = Header(default=None, alias="X-Event-Key"),
    ) -> ProcessResult | JSONResponse:
        body = await request.body()
        try:
            _authorize_webhook(settings, body, x_hub_signature)
            try:
                payload: dict[str, Any] = json.loads(body.decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Webhook body is not JSON: {exc}") from exc
            if x_event_key and x_event_key != "pr:merged":
                return ProcessResult(
                    status="ignored",
                    message=f"Ignoring event {x_event_key}",
                )
            event = parse_pr_merged_payload(payload)
            result = service.process(event)
            return _result_or_http(result)
        except WebhookAuthError as exc:
            return JSONResponse(
                status_code=401,
                content=ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message)).model_dump(),
            )
        except ValidationError as exc:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message)).model_dump(),
            )
        except HotfixPrepError as exc:
            status = 503 if exc.code in _TRANSIENT_CODES else 400
            return JSONResponse(
                status_code=status,
                content=ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message)).model_dump(),
            )

    @app.post("/v1/process", response_model=ProcessResult)
    def process_pr(body: ProcessRequest) -> ProcessResult | JSONResponse:
        event = bitbucket.get_pull_request(body.project, body.slug, body.pr_id)
        result = service.process(event, dry_run=body.dry_run)
        return _result_or_http(result)

    return app


def _authorize_webhook(settings: Settings, body: bytes, signature: str | None) -> None:
    if settings.webhook_secret:
        verify_signature(body, signature, settings.webhook_secret)
        return
    if settings.allow_insecure_webhook:
        logger.warning("Webhook accepted without signature (ALLOW_INSECURE_WEBHOOK=true)")
        return
    raise WebhookAuthError("WEBHOOK_SECRET is required unless ALLOW_INSECURE_WEBHOOK=true")


def _result_or_http(result: ProcessResult) -> ProcessResult | JSONResponse:
    if result.status == "failed" and result.error_code in _TRANSIENT_CODES:
        return JSONResponse(
            status_code=503,
            content=result.model_dump(),
        )
    return result


app = create_app()
