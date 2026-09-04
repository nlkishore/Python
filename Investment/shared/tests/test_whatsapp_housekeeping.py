"""Tests for WhatsApp message age selection (housekeeping)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.whatsapp_housekeeping import old_message_ids  # noqa: E402


def test_old_message_ids_filters_by_cutoff():
    items = [
        {"idMessage": "new", "timestamp": 2_000_000_000},
        {"idMessage": "old", "timestamp": 1_000_000_000},
        {"idMessage": "also_old", "timestamp": 1_000_000_100},
        {"idMessage": "", "timestamp": 1},
        {"timestamp": 1_000_000_000},
    ]
    got = old_message_ids(items, cutoff_ts=1_500_000_000)
    assert got == ["old", "also_old"]


def test_old_message_ids_accepts_millis():
    items = [{"idMessage": "m", "timestamp": 1_000_000_000_000}]
    got = old_message_ids(items, cutoff_ts=1_000_000_001)
    assert got == ["m"]
