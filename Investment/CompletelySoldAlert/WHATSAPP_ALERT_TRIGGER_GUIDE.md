# WhatsApp On-Demand Alert Trigger — Consolidated Guide

Reference for the "Completely Sold" price-summary system and its WhatsApp
command trigger. Covers both projects under `C:\Investment` and how they work
together.

- **`CompletelySoldAlert/`** — builds and sends the price digest (LangGraph).
- **`AlertApp-IBKR/`** — Green API listener that runs the digest on a WhatsApp
  command (`SOLD` / `SEND`).

Last updated: 2026-07-03

---

## 1. What the system does

1. Reads the IBKR **Completely_Sold** report (fully closed stock positions).
2. Compares **last sold price** vs **current market price** (Yahoo Finance).
3. Sends **one WhatsApp digest**:
   - **Default** (`notify_all_positions: true`): every completely sold symbol
     with prices — title *"Completely Sold — Price Summary"*.
   - **Threshold mode** (`notify_all_positions: false`): only symbols where
     `Change_Since_Last_Sold_Pct <= price_drop_threshold_pct` (e.g. `-5.0`) —
     title *"Completely Sold — Price Drop Alert"*.

You can trigger a run **on demand from your phone** by sending `SOLD` (or
`SEND`) over WhatsApp.

---

## 2. Architecture

```
                WhatsApp (your phone / Green API web)
                          |  "SOLD" / "SEND" / "STATUS" / "SUPPORT AAPL"
                          v
        +-------------------------------------------+
        |  AlertApp-IBKR / backgroundAlert.py       |
        |  - single-instance mutex guard            |
        |  - polls Green API receiveNotification    |
        |  - reacts to incoming AND outgoing msgs   |
        +-------------------------------------------+
                          |  on SOLD/SEND: launches
                          v
        +-------------------------------------------+
        |  CompletelySoldAlert / run-alert.bat      |
        |     python -m completely_sold_alert run   |
        |     (--force-market-day when triggered)   |
        +-------------------------------------------+
                          |  LangGraph workflow
                          v
      market-day check -> freshness -> load Excel ->
      evaluate rows -> format digest -> send WhatsApp
                          |
                          v
                WhatsApp digest back to your phone
```

Both components share the **same Green API instance** and credentials from
`C:\Investment\AutomatedTrading\config.ini` `[trading]`.

---

## 3. WhatsApp commands

| Command | Action |
|---------|--------|
| `STATUS` | Replies "AlertApp-IBKR Online" |
| `SOLD` / `SEND` | Runs the Completely Sold price summary and sends the digest |
| `SUPPORT AAPL` | Returns 3 recent pivot support levels (6-month Yahoo data) |

The listener reacts to **both** incoming messages (from another phone) and your
own **outgoing** messages (sent from the linked phone or the Green API web
console), so you can trigger commands from your own WhatsApp. It never replies
"unknown command" to outgoing messages, avoiding a reply loop.

On-demand `SOLD` / `SEND` runs with `--force-market-day`, so it returns the
price summary **even on weekends / NYSE holidays**.

---

## 4. Running the listener

```cmd
C:\Investment\AlertApp-IBKR\run-green-api-listener.bat
```

Keep the window open. Expected output:

```
[*] AlertApp-IBKR Green API listener started.
    Instance: <id>  Target: <phone>
    WhatsApp commands: STATUS | SUPPORT SYMBOL | SOLD | SEND
    Single-instance lock acquired.
```

### Single instance only (race-condition guard)

Green API allows only **one** active `receiveNotification` consumer per
instance. Two listeners cause `502 RMQ_ERROR: consumer closed` and
dropped / delayed commands.

The listener enforces a single instance with a **Windows named mutex**
(`Global\AlertApp_IBKR_GreenAPI_Listener`). A second copy refuses to start:

```
[X] Another AlertApp-IBKR listener is already running. Exiting to avoid a
    Green API race condition (only one consumer per instance).
```

The lock is released automatically by the OS when the running listener stops.

Check what is running (PowerShell):

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -like 'python*' -and $_.CommandLine -match 'backgroundAlert' } |
  Select-Object ProcessId, CreationDate
```

---

## 5. Running the alert directly (without WhatsApp)

```cmd
cd C:\Investment\CompletelySoldAlert
run-alert.bat                 REM defaults to "run"
run-alert.bat run             REM explicit
run-alert.bat --dry-run       REM build digest, do not send
run-alert.bat status          REM last export + cooldown
run-alert.bat refresh-only    REM rebuild IBKR Excel only
```

The batch wrapper passes arguments straight through; the CLI defaults to the
`run` command. Do **not** pass `run` twice.

---

## 6. Green API authorization

The instance must be **authorized** (linked to WhatsApp). Green API returns
HTTP 200 with an `idMessage` even when the instance is **not** linked, so a
message silently disappears. The sender checks instance state first and reports:

```
Green API instance not authorized (state='notAuthorized').
```

Re-link: open <https://console.green-api.com>, select the instance, scan the QR
under **Linked Devices**, wait for `state=authorized`.

Quick state check:

```cmd
cd C:\Investment\CompletelySoldAlert
.venv\Scripts\python.exe -c "from completely_sold_alert.config import load_settings; from whatsapp_api_client_python import API; s=load_settings(); w=s.whatsapp; print(API.GreenAPI(w.id_instance, w.api_token).account.getStateInstance().data)"
```

---

## 6a. Keeping it running (auto-start, watchdog, machine-down alerts)

Three layers, because a fully-down machine cannot notify you itself:

| Layer | Handles | Mechanism |
|-------|---------|-----------|
| **Auto-start** | PC reboot | Task Scheduler runs the watchdog at logon |
| **Watchdog** | Process crash while PC is up | Task Scheduler runs `watchdog.py` every 5 min; restarts the listener (mutex-based check) and sends a WhatsApp "restarted" notice |
| **External heartbeat** | Machine down / power loss / no internet | Listener pings an external dead-man's-switch (e.g. healthchecks.io); if pings stop, that service alerts your phone |

**Install auto-start + watchdog (one time):**

```cmd
C:\Investment\AlertApp-IBKR\install-scheduled-tasks.bat
```

Creates `AlertApp-IBKR-Startup` (at logon) and `AlertApp-IBKR-Watchdog`
(every 5 minutes). Remove with `uninstall-scheduled-tasks.bat`.

Tasks run only while the user is logged on (this PC uses a per-user Python). For
run-without-login, install an all-users Python and recreate the tasks with "Run
whether user is logged on or not".

**Enable machine-down alerts (external heartbeat):**

1. Create a free check at <https://healthchecks.io> (Period 10 min, Grace 10 min).
2. Add a phone notification (healthchecks.io app / Telegram / Pushover / email).
3. Copy the ping URL (`https://hc-ping.com/<uuid>`).
4. Save it for the listener — any one of:
   - `C:\Investment\AlertApp-IBKR\heartbeat_url.txt` (URL only), or
   - env var `LISTENER_HEARTBEAT_URL`, or
   - `config.ini` `[monitoring] heartbeat_url = <url>`.
5. Restart the listener — it logs `Heartbeat: enabled` and pings every 5 minutes.

If the pings stop (machine off, no internet, process dead and not restarted),
healthchecks.io notifies your phone after the grace period. Send `STATUS`
anytime to actively confirm the listener is alive.

Watchdog / heartbeat artifacts (`listener.log`, `heartbeat_url.txt`) are local
and git-ignored.

---

## 7. Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| Run says `Sent: True` but nothing arrives | Instance `notAuthorized` — re-scan QR (Section 6). |
| No response to `SOLD`; late/failed reply hours later | Two listeners racing (`502 consumer closed`). Keep only one (Section 4). |
| `Skipped: non_trading_day` | Weekend / NYSE holiday. On-demand `SOLD` uses `--force-market-day`. |
| `unrecognized arguments: run` | Fixed — don't pass `run` twice; batch defaults to `run`. |
| `WhatsApp credentials missing` | Auto-loaded from `AutomatedTrading\config.ini` `[trading]`; or set `GREEN_API_*` env vars. |
| Permission denied writing IBKR xlsx | Close Excel, or write to `CompletelySoldAlert\data\` via `--output`. |

---

## 8. Files

**`AlertApp-IBKR/`**
- `backgroundAlert.py` — Green API listener + single-instance guard + command handling + heartbeat.
- `watchdog.py` — restarts the listener if it is down; notifies via WhatsApp.
- `run-green-api-listener.bat` — manual start script (console).
- `install-scheduled-tasks.bat` / `uninstall-scheduled-tasks.bat` — auto-start + watchdog tasks.
- `readme.txt` — listener reference.
- (local, git-ignored) `listener.log`, `heartbeat_url.txt`, `config.ini`.

**`CompletelySoldAlert/`**
- `completely_sold_alert/` — LangGraph package (config, graph, services, adapters).
- `run-alert.bat` — batch wrapper.
- `config/settings.yaml` — local config (not in git).
- `readme.txt` — full future reference.

**Design / plan**
- `docs/COMPLETELY_SOLD_PRICE_ALERT_PLAN.md`
- `docs/review/COMPLETELY_SOLD_PRICE_ALERT_DESIGN.md`

---

## 9. Daily use checklist

1. Ensure **one** listener is running (`run-green-api-listener.bat`).
2. Ensure the Green API instance is **authorized**.
3. From WhatsApp, send **`SOLD`** — the price summary returns in ~30 seconds.
