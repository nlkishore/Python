"""US market session day check (NYSE)."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger("completely_sold_alert")


def is_market_day(calendar_name: str = "NYSE", tz: str = "America/New_York") -> bool:
    try:
        import exchange_calendars as xcals
        import pandas as pd

        cal = xcals.get_calendar("XNYS")
        session_date = pd.Timestamp.now(tz=tz).normalize().tz_localize(None)
        return bool(cal.is_session(session_date))
    except Exception as exc:
        logger.warning("exchange_calendars unavailable (%s); using weekday fallback", exc)
        now = datetime.now(ZoneInfo(tz))
        return now.weekday() < 5
