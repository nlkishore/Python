# IBKR Client Portal: snapshot & chart scripts — quick reference

Two programs under `AutomatedTrading\` share the same **Client Portal Gateway** flow (browser login, `POST /tickle`, brokerage session) and the same **WhatsApp (Green API)** settings in `config.ini`.

| Script | Primary purpose | WhatsApp message content |
|--------|-----------------|---------------------------|
| `ClientPortalMarketSnapshot.py` | Live **quote snapshot** (last, bid/ask, volume, etc.) | **Quote digest** only |
| `ChartSupportResistanceWhatsApp_IBKR.py` | **Candle history** → nearest support / resistance + heuristic signal | **Chart S/R digest** only |

`whatsapp_enabled` in config does **not** auto-send for either script. You must pass **`--send-whatsapp`** to trigger Green API (except where noted below).

---

## Shared configuration (`config.ini`)

- **`[trading]`** — symbols list, WhatsApp:
  - `whatsapp_enabled` — must be `true` for sends to be allowed
  - `whatsapp_id_instance`, `whatsapp_api_token_instance`, `whatsapp_target_phone` — Green API
- **`[ibkr]`** — CP host/port, timeouts, `md_snapshot_fields` (snapshot), `cp_period` / `cp_bar` / `request_pause_seconds` (history pacing for chart / `--chart-support`)

**Dependency for WhatsApp:** `pip install whatsapp_api_client_python`

---

## 1. `ClientPortalMarketSnapshot.py`

**What it does:** `GET /iserver/accounts` → `GET /iserver/marketdata/snapshot` for symbols in `[trading] symbols`. Optional `--chart-support` adds `GET /iserver/marketdata/history` and fills `chart_signals` (S/R in **JSON only** for that run).

### Command-line switches

| Flag | Effect |
|------|--------|
| *(none)* | Full JSON to stdout; ASCII quote table unless `--no-table`. |
| `--json-out` | JSON only on stdout; suppresses session / accounts / table status lines. |
| `--fields "31,84,86,..."` | Override IBKR tick field ids for snapshot (else `[ibkr] md_snapshot_fields` or built-in default). |
| `--no-table` | Skip printing the quotes table; JSON unchanged. |
| `--drop-raw-snapshot` | Omit raw `snapshot` (numeric keys); keep `quotes`, `snapshot_labeled`, etc. |
| `--chart-support` | After snapshot, fetch bars and add **`chart_signals`** (S/R, signal). Adds **time** (history + optional `progress` not used here by default). |
| `--no-snapshot` | Skip snapshot + accounts. **Only valid with** `--chart-support` (chart-only run). |
| `--whatsapp-only` | After run, print **`whatsapp_friendly_text`** (quote digest) only; **no JSON**. Exits before JSON print. If `--send-whatsapp` is also set, send runs **first**, then digest prints. |
| `--send-whatsapp` | Send **`whatsapp_friendly_text`** via Green API. Content is the **quote digest**, **not** chart S/R (even if `--chart-support` was used). |

### WhatsApp / JSON fields

- **`whatsapp_friendly_text`** — human-readable **quotes** (built from `quotes`).
- **`whatsapp_delivery`** — present after `--send-whatsapp`: `success`, `detail` on failure.
- **`chart_signals`** — only if `--chart-support`; **not** included in the WhatsApp body for this script.

### Typical commands

```bash
# Quotes JSON only (no extra stdout chatter)
python ClientPortalMarketSnapshot.py --json-out

# Quotes + chart S/R in JSON (no WhatsApp)
python ClientPortalMarketSnapshot.py --chart-support

# WhatsApp: live quote digest only
python ClientPortalMarketSnapshot.py --send-whatsapp

# Quote digest to console only (no JSON), optionally also send
python ClientPortalMarketSnapshot.py --whatsapp-only
python ClientPortalMarketSnapshot.py --whatsapp-only --send-whatsapp
```

---

## 2. `ChartSupportResistanceWhatsApp_IBKR.py`

**What it does:** No snapshot. Resolves conids, pulls **history** for each symbol (with **`request_pause_seconds`** between requests — often several minutes for long lists), computes **`chart_signals`**, builds **`whatsapp_friendly_text`** (S/R + signals).

Requires **`[ibkr] ibkr_data_source = client_portal`**.

### Command-line switches

| Flag | Effect |
|------|--------|
| *(none)* | Full JSON (`chart_signals`, `whatsapp_friendly_text`). Stderr: session line + per-symbol **progress** unless `--quiet`. |
| `--config PATH` | Alternate `config.ini` (default: next to script). |
| `--send-whatsapp` | **Required to send** — posts **`whatsapp_friendly_text`** (chart digest) via Green API. |
| `--json-out` | Suppresses session status line on stdout; JSON unchanged; stderr may still show WhatsApp result when `--send-whatsapp`. |
| `--text-only` | Prints **chart digest** text only (stdout); **no JSON**. If paired with `--send-whatsapp`, send runs then digest prints. |
| `--quiet` | No per-symbol progress on stderr (run looks idle until finish). |

If `whatsapp_enabled` is true but **`--send-whatsapp`** is omitted, stderr reminds you and JSON includes **`whatsapp_delivery`** with `"attempted": false`.

### Typical commands

```bash
# JSON only, progress on stderr
python ChartSupportResistanceWhatsApp_IBKR.py

# Quiet + chart digest WhatsApp
python ChartSupportResistanceWhatsApp_IBKR.py --quiet --send-whatsapp

# Plain text digest to terminal + WhatsApp
python ChartSupportResistanceWhatsApp_IBKR.py --text-only --send-whatsapp
```

---

## Which program should I use?

| Goal | Use |
|------|-----|
| WhatsApp last/bid/ask/volume snapshot | `ClientPortalMarketSnapshot.py --send-whatsapp` |
| WhatsApp support/resistance from candles | `ChartSupportResistanceWhatsApp_IBKR.py --send-whatsapp` |
| JSON only, quotes + optional chart array | `ClientPortalMarketSnapshot.py` (+ `--chart-support` if you want `chart_signals` in same JSON) |
| Long runs / IB pacing | Chart script; use **`--quiet`** if you do not want stderr progress |

---

## Troubleshooting (short)

- **No WhatsApp:** Confirm **`--send-whatsapp`** and **`whatsapp_enabled = true`** plus Green API credentials.
- **Wrong content:** Snapshot script never puts chart S/R into WhatsApp; use the chart script for that.
- **Chart script slow:** Expected — pacing × symbol count; **`--quiet`** hides progress but does not speed IB.
- **HTTP / chart unavailable for one symbol:** Run continues; that ticker appears under **`error`** in `chart_signals` and in the digest line.

---

*Heuristic signals and levels are illustrative only — not financial advice.*


python AutomatedTrading\ChartSupportResistanceWhatsApp_IBKR.py --config AutomatedTrading\config_longterm.ini --send-whatsapp
