"""Green API WhatsApp sender (AlertApp pattern)."""

from __future__ import annotations

import logging

from completely_sold_alert.config import AppSettings

logger = logging.getLogger("completely_sold_alert")


def send_whatsapp(settings: AppSettings, text: str, *, dry_run: bool = False) -> tuple[bool, str]:
    if dry_run:
        logger.info("DRY-RUN WhatsApp message (%d chars)", len(text))
        return True, "dry_run"

    wa = settings.whatsapp
    if not wa.id_instance or not wa.api_token or not wa.target_phone:
        return (
            False,
            "WhatsApp credentials missing. Set config/settings.yaml, GREEN_API_* env vars, "
            "or [trading] whatsapp_* in AutomatedTrading/config.ini (same as AlertApp).",
        )

    try:
        from whatsapp_api_client_python import API
    except ImportError:
        return False, "Install: pip install whatsapp-api-client-python"

    green_api = API.GreenAPI(wa.id_instance, wa.api_token)

    # Green API returns HTTP 200 with an idMessage even when the instance is not
    # linked to a phone, so the message is silently dropped. Verify authorization
    # first to surface a real, actionable failure instead of a false success.
    try:
        state = green_api.account.getStateInstance()
        state_val = (state.data or {}).get("stateInstance") if state.code == 200 else None
    except Exception as exc:  # noqa: BLE001 - report any state-check failure
        return False, f"could not verify instance state: {exc}"

    if state_val != "authorized":
        return (
            False,
            f"Green API instance not authorized (state={state_val!r}). "
            "Re-link WhatsApp: open https://console.green-api.com, select the "
            "instance, scan the QR under Linked Devices, wait for state=authorized.",
        )

    chat_id = f"{wa.target_phone}@c.us"
    response = green_api.sending.sendMessage(chat_id, text)
    if response.code == 200:
        return True, "sent"
    return False, getattr(response, "error", None) or f"code {response.code}"
