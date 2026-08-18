# Automated Trading Scripts - Program Reference

This document summarizes the Python programs in `C:\Investment\AutomatedTrading`: four that use Yahoo Finance for history, plus `ChartSupportAndSignals_IBKR.py`, which loads intraday history from Interactive Brokers. It explains how they differ and how they share configuration.

**Shared configuration file:** `config.ini` (sections `[trading]` for symbols and shared options; `[ibkr]` only for the IBKR chart script)

**Shared foundation:** `averagePriceFetcher.py` supplies Yahoo Finance history loading, symbol lists, CSV writing helpers, and EMA history rules reused by the other scripts.

---

## 1. `averagePriceFetcher.py`

**Role:** Core library and fixed-percentage target generator (not investment advice).

**What it does**

- Pulls daily OHLCV via `yfinance` (`Ticker.history`), choosing the shortest Yahoo `period` among `100d`, `6mo`, `1y`, `2y`, `max` that yields at least recommended bar count for stable EMA tail values.
- **Recommended bars** rule: `max(3 x EMA span, EMA span)` - with default span 52, this is 156 bars.
- If no period meets recommended bars, keeps the longest period that still has at least 52 bars; otherwise returns an error payload.
- Computes 52-EMA reference on close price.
- Computes fixed targets: buy at -5% and sell at +7% from EMA reference.

**Main API (importable)**

- `load_price_history_for_ema(symbol)` -> `(DataFrame, meta dict)`
- `get_trading_targets(symbol)` -> strategy payload or error payload
- `load_symbols_from_config(..., output_csv_key=..., output_csv_fallback=...)`
- `meta_summary_for_exports(meta)`, `write_csv_dicts(...)`, `write_targets_csv(...)`

**CLI behavior**

- Reads `symbols` and `output_csv` from `config.ini`.
- Writes one row per symbol to CSV.
- Prints symbol-level failures to stderr and exits with code 1 if any symbol fails.

**Default output CSV columns**

`Symbol`, `Period Used`, `Bars Loaded`, `Meet Recommended bar count`, `Recommended Mn Bars`, `Current Price`, `Referance price (52 EMA)`, `Buy Traget (-5%)`, `Sell Traget (+7%)`, `Distance to Buy`  
*(Column spellings intentionally match requested CSV format.)*

---

## 2. `AdaptiveAItrader.py`

**Role:** Volatility-adaptive target bands around the same 52-EMA reference using ATR.

**What it does**

- Reuses `load_price_history_for_ema` and `meta_summary_for_exports` from `averagePriceFetcher.py`.
- Computes ATR(14) from High/Low/Close.
- Builds adaptive levels at `EMA +/- (2 x ATR)` instead of fixed percentages.
- Adds `Implied Buy %` for quick interpretation of band width relative to EMA.

**Main API**

- `get_adaptive_targets(symbol)` -> payload with EMA, ATR, adaptive levels, and shared period metadata.

**CLI behavior**

- Uses common `symbols` from config.
- Writes to `output_csv_adaptive_ai` (fallback `adaptive_ai_targets.csv`).
- Exits with code 1 if any symbol fails.

**Output CSV columns**

`Symbol`, `Period Used`, `Bars Loaded`, `Meet Recommended bar count`, `Recommended Mn Bars`, `Current Price`, `Reference (52 EMA)`, `Daily Volatility (ATR)`, `Adaptive Buy Target`, `Adaptive Sell Target`, `Implied Buy %`

---

## 3. `AdaptiveTraderWithVolume.py`

**Role:** ATR adaptive bands plus volume confirmation, returning decision labels.

**What it does**

- Same EMA + ATR setup as `AdaptiveAItrader.py`.
- Adds 20-day average volume and volume ratio.
- Uses decision engine: `BUY`, `SELL`, `HOLD`, or `WAIT`.
- Supports stricter mode using config value `volume_filter_enabled`:
  - buy/sell signal requires volume confirmation when enabled,
  - otherwise signal can trigger without volume confirmation.

**Main API**

- `get_ai_trade_decision(symbol, volume_filter_enabled=True)` -> payload with decision and reason.

**CLI behavior**

- Reads `volume_filter_enabled` from config.
- Writes to `output_csv_adaptive_volume` (fallback `adaptive_trader_volume.csv`).
- Exits with code 1 if any symbol fails.

**Output CSV columns**

`Symbol`, `Period Used`, `Bars Loaded`, `Meet Recommended bar count`, `Recommended Mn Bars`, `Decision`, `Reason`, `Current Price`, `Ref Price (EMA)`, `Volume Status`, `Volume Ratio`

---

## 4. `ChartSupportAndSignals.py`

**Role:** Chart-structure + candlestick heuristic scanner with optional WhatsApp notifications.

**What it does**

- Reuses shared history selection and metadata from `averagePriceFetcher.py`.
- Detects swing pivot lows/highs using left/right window parameters:
  - `chart_pivot_left`
  - `chart_pivot_right`
- Computes nearest support below and nearest resistance above current close.
- Computes ATR(14) and checks if price is close to support/resistance within:
  - `chart_atr_proximity_mult x ATR`
- Classifies latest candle pattern heuristically:
  - `HAMMER_LIKE`, `STAR_LIKE_TOP`, `BULLISH_ENGULFING`, `BEARISH_ENGULFING`, or `NONE`.
- Generates conservative signal:
  - `BUY_HEURISTIC` only when bullish pattern + near support,
  - `SELL_HEURISTIC` only when bearish pattern + near resistance,
  - otherwise `HOLD`.

**WhatsApp integration (Green API)**

- Optional config switch:
  - `whatsapp_enabled = true|false`
- Credentials and recipient (all from config):
  - `whatsapp_id_instance`
  - `whatsapp_api_token_instance`
  - `whatsapp_target_phone` (country code, no `+`)
- Signal filter:
  - `whatsapp_notify_signals = BUY_HEURISTIC, SELL_HEURISTIC` (comma-separated)
- **Dedupe layers:**
  1. cooldown gate by symbol+signal using:
     - `whatsapp_notify_cooldown_minutes`
  2. price-bucket gate by symbol+signal+price-band using:
     - `whatsapp_notify_price_bucket_pct`
- State persisted in JSON file:
  - `whatsapp_notify_state_file`

**Main API**

- `get_support_chart_signal(symbol, pivot_left, pivot_right, atr_proximity_mult)`

**CLI behavior**

- Writes CSV to `output_csv_chart_support` (fallback `chart_support_signals.csv`).
- When WhatsApp is enabled and dependency is installed, sends notifications for filtered signals.
- Exits with code 1 if any symbol fails.

**Output CSV columns**

`Symbol`, `Period Used`, `Bars Loaded`, `Meet Recommended bar count`, `Recommended Mn Bars`, `Current Price`, `ATR14`, `Nearest Support`, `Distance To Support %`, `Nearest Resistance`, `Distance To Resistance %`, `Pivot Lows Detected`, `Pivot Highs Detected`, `Candle Pattern`, `Signal`, `Signal Reason`

---

## 5. `ChartSupportAndSignals_IBKR.py`

**Role:** Same pivot / ATR-proximity / candle heuristics and optional WhatsApp flow as `ChartSupportAndSignals.py`, but **OHLCV comes from Interactive Brokers** instead of Yahoo Finance.

**Data sources (`ibkr_data_source` in `[ibkr]`)**

| Mode | What runs | How bars are fetched |
|------|-----------|----------------------|
| **`client_portal`** (default) | **Client Portal Gateway** on your machine (HTTPS, typically port **5000**) | REST: `/v1/api/iserver/secdef/search` for contract id, `/v1/api/iserver/marketdata/history` for bars. Uses Python **stdlib** only (no `ib_insync` for HTTP). |
| **`tws_socket`** | **TWS** or **IB Gateway** with the **socket API** enabled (classic ports e.g. **7497** paper / **7496** live) | `ib_insync` + `reqHistoricalData` after contract qualification. Requires `pip install ib-insync`. |

**Important:** Client Portal Gateway is **not** the same process as the IB Gateway you use only for socket trading. For CP mode you must start the **Client Portal Gateway**, open `https://127.0.0.1:<cp_gateway_port>` in a browser, **log in**, and leave the gateway running. Port **5000** is the usual CP listen port (override with `cp_gateway_port` if your `conf.yaml` uses another).

Socket mode does **not** require the browser login; it needs a live API connection to TWS/IB Gateway at `host` / `port`.

**Config**

- Reuses **`[trading]`**: `symbols`, and the same WhatsApp keys as `ChartSupportAndSignals.py` when you want alerts.
- Adds **`[ibkr]`** (see below). Chart-specific overrides include `pivot_left`, `pivot_right`, `atr_proximity_mult`, `min_bars_recommended`, `output_csv`, and `whatsapp_notify_state_file` (defaults to a separate JSON file so Yahoo and IBKR runs do not share dedupe state unless you point both at the same path).

**CLI behavior**

- Reads `config.ini` from the script directory.
- Writes chart CSV using `CHART_SIGNALS_CSV_FIELDNAMES` (same columns as section 4). The period column is still labeled **`Period Used`** in the CSV; internally the script may fill **`Period used (yfinance)`** with tags like `CP 5min/5d` or `Socket 5 mins/5 D` for traceability (name kept for export compatibility).

**Dependencies**

- Always: `pandas` (and shared helpers).
- **Client Portal mode:** no extra IBKR Python package.
- **Socket mode:** `ib_insync`.

---

## Quick comparison

| Aspect | averagePriceFetcher | AdaptiveAItrader | AdaptiveTraderWithVolume | ChartSupportAndSignals | ChartSupportAndSignals_IBKR |
|--------|---------------------|------------------|---------------------------|------------------------|----------------------------|
| Core reference | 52 EMA | 52 EMA | 52 EMA | Price structure + candles (uses shared bars/meta) | Same heuristics; **IBKR** bars |
| Band style | Fixed -5%/+7% | +/-2 x ATR | +/-2 x ATR | ATR-proximity to support/resistance | Same |
| Volume logic | No | No | Yes (20-day avg) | No | No |
| Decision output | Targets only | Adaptive targets | BUY/SELL/HOLD/WAIT | BUY_HEURISTIC/SELL_HEURISTIC/HOLD | Same |
| Notifications | No | No | No | Optional WhatsApp (Green API) | Optional WhatsApp (same `[trading]` keys) |
| CSV key in config | `output_csv` | `output_csv_adaptive_ai` | `output_csv_adaptive_volume` | `output_csv_chart_support` | `output_csv` under **`[ibkr]`** |
| History source | Yahoo | Yahoo | Yahoo | Yahoo | **Client Portal REST** or **TWS socket** |

---

## `config.ini` keys summary

**Common**

- `symbols`
- `output_csv`
- `output_csv_adaptive_ai`
- `output_csv_adaptive_volume`
- `output_csv_chart_support`

**AdaptiveTraderWithVolume only**

- `volume_filter_enabled`

**ChartSupportAndSignals only**

- `chart_pivot_left`
- `chart_pivot_right`
- `chart_atr_proximity_mult`
- `whatsapp_enabled`
- `whatsapp_id_instance`
- `whatsapp_api_token_instance`
- `whatsapp_target_phone`
- `whatsapp_notify_signals`
- `whatsapp_notify_cooldown_minutes`
- `whatsapp_notify_price_bucket_pct`
- `whatsapp_notify_state_file`

**`ChartSupportAndSignals_IBKR.py` — section `[ibkr]`**

- **`ibkr_data_source`** — `client_portal` (default) or `tws_socket`.
- **Client Portal Gateway**
  - **`cp_gateway_host`** — default `127.0.0.1`
  - **`cp_gateway_port`** — default `5000`
  - **`cp_request_timeout_seconds`** — HTTP timeout (default `60`)
  - **`cp_period`**, **`cp_bar`** — optional; if set, override the mapping from `duration` / `bar_size` for the CP history request
  - **`sec_type`** — e.g. `STK` for stock search
- **Shared by both modes (bar semantics / labels / pivots)**
  - **`bar_size`**, **`duration`** — used to derive CP `cp_bar` / `cp_period` when overrides are blank; also used as-is in socket mode
  - **`what_to_show`** — e.g. `TRADES`; mapped to Client Portal source where applicable
  - **`use_rth`** — regular trading hours vs extended (CP uses inverted flag `outsideRth` internally)
  - **`exchange`**, **`currency`** — contract context (CP history passes exchange)
  - **`pivot_left`**, **`pivot_right`**, **`atr_proximity_mult`**, **`min_bars_recommended`**
  - **`request_pause_seconds`** — delay between symbols (pacing / courtesy)
  - **`output_csv`** — output path for this script’s chart CSV
  - **`whatsapp_notify_state_file`** — optional override for dedupe state path (under `[ibkr]`)
- **Socket mode only (`tws_socket`)**
  - **`host`**, **`port`**, **`client_id`**, **`readonly`**

---

## Running

From `C:\Investment\AutomatedTrading`:

```bash
python averagePriceFetcher.py
python AdaptiveAItrader.py
python AdaptiveTraderWithVolume.py
python ChartSupportAndSignals.py
python ChartSupportAndSignals_IBKR.py
```

Dependencies: `pandas`, `yfinance` for the Yahoo-based scripts; optionally `whatsapp_api_client_python` for WhatsApp. For `ChartSupportAndSignals_IBKR.py` in **socket** mode, also `ib-insync`. **Client Portal** mode uses no extra IBKR package beyond a running gateway and browser login.

---

## Disclaimer

These scripts produce quantitative heuristics only. They are not financial advice and do not account for transaction costs, slippage, liquidity, fundamentals, portfolio context, or individual risk profile.
