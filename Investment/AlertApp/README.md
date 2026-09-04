# AlertApp — WhatsApp commands

Send a **plain text** message from the WhatsApp account linked to Green API (your phone). The listener on this PC polls every ~2 seconds and replies in the same chat.

You can also send the command **from the same phone** (outgoing). The listener still picks it up.

Casual chat is ignored. There is no reply unless the message matches a command below.

---

## Before you start

1. Green API credentials in `AlertApp\secrets.local.ini` (`id_instance`, `api_token`, `target_phone`).
2. Listener running (only **one** copy):

```cmd
C:\Investment\start_stock_alert.bat
```

Or `AlertApp\run-green-api-listener.bat`. Auto-start: `AlertApp\install-scheduled-tasks.bat`.

3. Confirm it is alive — send:

```
STATUS
```

You should get *AlertApp Online* plus the command list.

After code changes, **restart** the listener (`stop_stock_alert.bat`, then start again). Send `RELOAD` only to refresh Excel watchlists, not to load new Python.

---

## Avg sold + current market (`PRICE` / `Q`)

This is the on-demand quote.

**Send either:**

```
PRICE NVDA
```

or the short form:

```
Q NVDA
```

Replace `NVDA` with any ticker (case does not matter: `price aapl` works).

**Example reply:**

```
*NVDA*
Avg Sold:    $142.18   (26 sh)
Market:      $216.09   (Yahoo last 2026-09-02 15:32)
vs Avg Sold: +51.9%
Last sold:   2024-10-18
```

| Field | Meaning |
|--------|---------|
| **Avg Sold** | Weighted average of **all** your IBKR sells for that symbol (`Sell proceeds ÷ sell qty`), from the **Sells** sheet in `C:\Investment\reports\IBKR_BuySell_Since_2020.xlsx`. Works for names you still hold, not only completely sold. |
| **Market** | Yahoo Finance last regular-session close (same source as the rest of AlertApp). After hours this is the last print, not a live bid/ask. |
| **vs Avg Sold** | `(market − avg sold) / avg sold`. Positive means the market is **above** what you sold at. |
| **Last sold** | Date of your most recent sell of that symbol. |

If you never sold the name, you still get the market price and a “no sells” note. Delisted tickers (for example SKLZ) may have avg sold but no Yahoo quote.

**Do not** send a bare ticker unless it is one you already traded or have on the watchlist (`NVDA` alone works for those). Unknown words are ignored so normal chat does not fire lookups. Prefer `PRICE NVDA`.

Avg sold is only as fresh as the BuySell Excel. After you regenerate IBKR reports, send `RELOAD` (or restart the listener).

---

## All commands

Send **exactly** these (extra words after a one-word command are not required).

| Message you send | What you get back |
|------------------|-------------------|
| `HELP` or `?` | Command list |
| `STATUS` | Listener is online; watchlist counts |
| `WATCHLIST` | Manual price-alert symbols and thresholds |
| `REBUY` | Completely-sold names with avg buy / avg sell / rebuy trigger |
| `PRICE NVDA` or `Q NVDA` | **Avg sold + current market** for that symbol |
| `SUPPORT AAPL` | Three recent pivot support levels (6-month Yahoo history) |
| `SOLD` or `SEND` | Runs the Completely Sold digest (can take a minute) |
| `RELOAD` | Reloads watchlists and the Sells-sheet cache from Excel |

---

## What “real time” means

- WhatsApp → PC: typically **2–5 seconds** (journal poll every `command_poll_seconds`, default 2).
- Market print: Yahoo last close, often delayed up to ~15 minutes during the session; last close when the market is shut.
- Avg sold: local Excel, not live Flex. Regenerate BuySell reports, then `RELOAD`.

---

## Green API free (Developer) plan

AlertApp is designed to work on the **free Developer** instance. Limits that matter:

| Limit | Effect |
|--------|--------|
| **3 chats per month** | Send and receive via API only for **three** contacts/groups. Stay on **one** alert chat (`target_phone`). A 4th chat can return error **466** / `quotaExceeded` until the 1st of the month. |
| **1 instance** | Run **one** listener only (the mutex already enforces this). |
| **Unlimited `sendMessage`** | No monthly cap on PRICE / REBUY texts to that one chat. |
| **Rate limits** | `sendMessage` 50/s (fine). `lastIncomingMessages` and `lastOutgoingMessages` are **1 request/second** each — do not poll faster than ~2s. |
| **Phone must stay linked** | If Green API WhatsApp logs out or this PC sleeps, nothing is immediate. |

The free plan does **not** add a 10-minute delay to outbound texts. Upgrade to **Business** only if you need more than three chats.

### Immediate vs delayed (this app)

**On-demand commands** (you type, bot answers) — usually **2–8 seconds**:

| Command | Typical wait |
|---------|----------------|
| `PRICE` / `Q` / known ticker | ~3–8 s (journal + one Yahoo quote) |
| `STATUS`, `HELP`, `WATCHLIST`, `RELOAD`, `REBUY` (list) | ~2–4 s |
| `SUPPORT AAPL` | ~5–15 s (6-month Yahoo history) |
| `SOLD` / `SEND` | up to a few minutes (runs CompletelySoldAlert) |

**Push alerts** (bot talks first) — **not** immediate:

| Alert | Typical wait | Why |
|--------|----------------|-----|
| `REBUY CANDIDATE` | Up to **10 minutes**, then several bubbles | Yahoo scan every `check_interval_seconds` (default **600**). Each qualifying symbol is a separate WhatsApp send (Green API may space them). |
| Same symbol again | **1 hour** | Cooldown so CLNE is not spammed every cycle. |
| UP/DOWN watchlist | Same 10-minute scan | Same loop as rebuy. |

REBUY CANDIDATE arriving late or one-after-another is the 10-minute job plus a burst of sends — not a Developer-plan quota.

### Adding more commands

New commands do **not** need a paid plan if they still reply in the **same one chat**.

| Kind | Timing | Guidance |
|------|--------|----------|
| Lookup (`PRICE`, P&L, last sold) | Seconds | Same journal poll. Keep Yahoo to **one ticker**. |
| List (`WATCHLIST`, rebuy digest) | Seconds | Prefer **one** WhatsApp message, not one bubble per symbol. |
| Heavy job (Flex, Excel rebuild) | Delayed | Send `⏳` first; do not block the 2s poll for minutes. |
| Push (price drop, rebuy) | Your scan interval | Optional shorter `check_interval_seconds`. Prefer one digest over many `REBUY CANDIDATE` texts. |

Avoid extra destination numbers (burns the 3-chat quota), a second listener, or journal polling faster than ~1s.

---

## Message housekeeping (older than 1 day)

The listener **automatically deletes WhatsApp messages in the alert chat** (`target_phone`) that are **older than 24 hours**.

- First run: about **2 minutes** after start (so `PRICE` is not blocked).
- After that: **once per 24 hours**.
- Each run scans the last `history_count` messages (default 100) and deletes at most `max_delete_per_run` (default 50). Older leftovers are picked up on the next run.

Configure in `config.ini`:

```ini
[housekeeping]
enabled = true
max_age_hours = 24
history_count = 100
max_delete_per_run = 50
```

Set `enabled = false` to turn this off. Only the Green API alert chat is cleaned, not other WhatsApp threads.

---

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| No reply at all | Type the command **on the WhatsApp that is linked to Green API** (the same one that received REBUY alerts). The listener now reads that chat journal. Restart: `stop_stock_alert.bat` then `run-green-api-listener.bat /background`. Check `AlertApp\listener.log` for `journal out … text='PRICE NVDA'`. |
| `STATUS` works, `PRICE NVDA` does not | Old listener still running — restart so it loads this command. |
| Avg sold missing | Symbol has no rows on the **Sells** sheet. Regenerate `IBKR_BuySell_Since_2020.xlsx`. |
| No market price | Yahoo has no quote (delisted / bad ticker). |
| Reply is stale avg sold | Send `RELOAD` after regenerating reports. |

Credentials and watchdog details: `AlertApp\readme.txt`.
