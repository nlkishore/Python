"""LangGraph workflow compilation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from langgraph.graph import END, StateGraph

from completely_sold_alert.adapters.excel_loader import load_completely_sold as load_completely_sold_sheet
from completely_sold_alert.adapters.flex_report import run_flex_refresh
from completely_sold_alert.adapters.whatsapp_green import send_whatsapp
from completely_sold_alert.config import AppSettings
from completely_sold_alert.logging_util import log_event
from completely_sold_alert.services.cooldown import filter_cooldown, record_alerts
from completely_sold_alert.services.digest_formatter import DigestMeta, build_digest
from completely_sold_alert.services.evaluate import evaluate_rows
from completely_sold_alert.services.freshness import is_stale, write_last_export
from completely_sold_alert.services.market_calendar import is_market_day
from completely_sold_alert.state import AlertState


def build_graph(settings: AppSettings):
    def check_market_day(state: AlertState) -> AlertState:
        errors = list(state.get("errors") or [])
        logs = list(state.get("log_messages") or [])

        if state.get("force_market_day"):
            logs.append(log_event("market_day_forced", is_market_day=True))
            return {
                "is_market_day": True,
                "market_calendar": settings.schedule.market_calendar,
                "skip_reason": None,
                "log_messages": logs,
                "errors": errors,
            }

        if not settings.schedule.run_market_days_only:
            logs.append(log_event("market_day_check", skipped_gate=False))
            return {
                "is_market_day": True,
                "market_calendar": settings.schedule.market_calendar,
                "skip_reason": None,
                "log_messages": logs,
                "errors": errors,
            }

        ok = is_market_day(settings.schedule.market_calendar, settings.schedule.timezone)
        if not ok:
            reason = "non_trading_day"
            logs.append(log_event("market_day_skip", reason=reason))
            return {
                "is_market_day": False,
                "market_calendar": settings.schedule.market_calendar,
                "skip_reason": reason,
                "log_messages": logs,
                "errors": errors,
            }

        logs.append(log_event("market_day_ok", calendar=settings.schedule.market_calendar))
        return {
            "is_market_day": True,
            "market_calendar": settings.schedule.market_calendar,
            "skip_reason": None,
            "log_messages": logs,
            "errors": errors,
        }

    def route_after_market(state: AlertState) -> str:
        return "continue" if state.get("is_market_day") else "skip"

    def check_freshness(state: AlertState) -> AlertState:
        errors = list(state.get("errors") or [])
        logs = list(state.get("log_messages") or [])
        report_path = Path(settings.data.report_path)

        if state.get("fixture_path"):
            logs.append(log_event("freshness_skipped", reason="fixture_mode"))
            return {
                "is_stale": False,
                "data_age_hours": 0.0,
                "last_export_at": None,
                "report_path": state["fixture_path"],
                "log_messages": logs,
                "errors": errors,
            }

        stale, age, exported_at = is_stale(
            settings.data_dir, settings.data.max_age_hours, report_path
        )
        logs.append(
            log_event(
                "freshness_check",
                is_stale=stale,
                data_age_hours=round(age, 2),
                last_export_at=exported_at,
            )
        )
        return {
            "is_stale": stale,
            "data_age_hours": age,
            "last_export_at": exported_at,
            "report_path": str(report_path),
            "log_messages": logs,
            "errors": errors,
        }

    def route_after_freshness(state: AlertState) -> str:
        if state.get("fixture_path"):
            return "load"
        return "refresh" if state.get("is_stale") else "load"

    def refresh_data(state: AlertState) -> AlertState:
        errors = list(state.get("errors") or [])
        logs = list(state.get("log_messages") or [])
        logs.append(log_event("refresh_start", mode=settings.data.refresh_mode))

        ok, msg = run_flex_refresh(settings)
        if not ok:
            errors.append(msg)
            logs.append(log_event("refresh_failed", error=msg))
            return {
                "refresh_attempted": True,
                "refresh_success": False,
                "refresh_error": msg,
                "log_messages": logs,
                "errors": errors,
            }

        logs.append(log_event("refresh_done", success=True))
        return {
            "refresh_attempted": True,
            "refresh_success": True,
            "refresh_error": None,
            "log_messages": logs,
            "errors": errors,
        }

    def route_after_refresh(state: AlertState) -> str:
        return "load" if state.get("refresh_success") else "fail"

    def load_completely_sold(state: AlertState) -> AlertState:
        errors = list(state.get("errors") or [])
        logs = list(state.get("log_messages") or [])

        path = Path(state.get("fixture_path") or state.get("report_path") or settings.data.report_path)
        try:
            rows = load_completely_sold_sheet(path)
        except Exception as exc:
            msg = f"load failed: {exc}"
            errors.append(msg)
            logs.append(log_event("load_failed", error=msg))
            return {
                "completely_sold_rows": [],
                "row_count": 0,
                "log_messages": logs,
                "errors": errors,
            }

        if state.get("refresh_success") and not state.get("fixture_path"):
            write_last_export(settings.data_dir, path, len(rows))

        logs.append(log_event("load_done", row_count=len(rows), path=str(path)))
        return {
            "completely_sold_rows": rows,
            "row_count": len(rows),
            "report_path": str(path),
            "log_messages": logs,
            "errors": errors,
        }

    def route_after_load(state: AlertState) -> str:
        return "evaluate" if state.get("row_count", 0) > 0 else "empty"

    def evaluate_alerts(state: AlertState) -> AlertState:
        errors = list(state.get("errors") or [])
        logs = list(state.get("log_messages") or [])
        rows = state.get("completely_sold_rows") or []

        candidates, skipped = evaluate_rows(rows, settings)
        cooldown_path = settings.data_dir / "alert_cooldown.json"
        if settings.alert.notify_all_positions:
            filtered = candidates
            suppressed: list[str] = []
        else:
            filtered, suppressed = filter_cooldown(
                candidates,
                cooldown_path,
                settings.notify.cooldown_hours,
            )

        logs.append(
            log_event(
                "evaluate",
                row_count=len(rows),
                candidate_count=len(filtered),
                suppressed=len(suppressed),
                notify_all=settings.alert.notify_all_positions,
                threshold=settings.alert.price_drop_threshold_pct,
            )
        )
        return {
            "alert_candidates": filtered,
            "skipped_rows": skipped,
            "cooldown_suppressed": suppressed,
            "log_messages": logs,
            "errors": errors,
        }

    def route_after_evaluate(state: AlertState) -> str:
        return "format" if state.get("alert_candidates") else "no_alerts"

    def format_digest(state: AlertState) -> AlertState:
        logs = list(state.get("log_messages") or [])
        candidates = state.get("alert_candidates") or []
        meta = DigestMeta(
            run_at=datetime.now(timezone.utc),
            total_completely_sold=state.get("row_count", 0),
            cooldown_suppressed=state.get("cooldown_suppressed") or [],
            skipped_quote_count=len(state.get("skipped_rows") or []),
            notify_all_positions=settings.alert.notify_all_positions,
            threshold_pct=settings.alert.price_drop_threshold_pct,
        )
        text = build_digest(candidates, settings, meta)
        logs.append(
            log_event("digest_formatted", length=len(text), symbols=len(candidates))
        )
        return {"digest_text": text, "log_messages": logs}

    def send_digest(state: AlertState) -> AlertState:
        errors = list(state.get("errors") or [])
        logs = list(state.get("log_messages") or [])
        text = state.get("digest_text") or ""
        dry = bool(state.get("dry_run"))

        ok, msg = send_whatsapp(settings, text, dry_run=dry)
        if not ok:
            errors.append(msg)
            logs.append(log_event("notify_failed", error=msg))
            return {
                "digest_sent": False,
                "log_messages": logs,
                "errors": errors,
            }

        if not dry and not settings.alert.notify_all_positions:
            symbols = [
                str(r.get("Symbol")).upper()
                for r in state.get("alert_candidates") or []
                if r.get("Symbol")
            ]
            record_alerts(settings.data_dir / "alert_cooldown.json", symbols)

        logs.append(log_event("notify_sent", dry_run=dry, detail=msg))
        return {"digest_sent": True, "log_messages": logs, "errors": errors}

    g = StateGraph(AlertState)
    g.add_node("check_market_day", check_market_day)
    g.add_node("check_freshness", check_freshness)
    g.add_node("refresh_data", refresh_data)
    g.add_node("load_completely_sold", load_completely_sold)
    g.add_node("evaluate_alerts", evaluate_alerts)
    g.add_node("format_digest", format_digest)
    g.add_node("send_digest", send_digest)

    g.set_entry_point("check_market_day")
    g.add_conditional_edges(
        "check_market_day",
        route_after_market,
        {"continue": "check_freshness", "skip": END},
    )
    g.add_conditional_edges(
        "check_freshness",
        route_after_freshness,
        {"refresh": "refresh_data", "load": "load_completely_sold"},
    )
    g.add_conditional_edges(
        "refresh_data",
        route_after_refresh,
        {"load": "load_completely_sold", "fail": END},
    )
    g.add_conditional_edges(
        "load_completely_sold",
        route_after_load,
        {"evaluate": "evaluate_alerts", "empty": END},
    )
    g.add_conditional_edges(
        "evaluate_alerts",
        route_after_evaluate,
        {"format": "format_digest", "no_alerts": END},
    )
    g.add_edge("format_digest", "send_digest")
    g.add_edge("send_digest", END)

    return g.compile()
