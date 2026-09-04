================================================================================
  AlertApp — Green API WhatsApp Stock Monitor + Command Listener
================================================================================

Folder:  C:\Investment\AlertApp
Script:  backgroundAlert1.py
Updated: 2026-08-19 (consolidated from AlertApp + AlertApp-IBKR)

WHAT IT DOES
------------
Two jobs in one process:

1. Price monitor
   Polls Yahoo Finance every CHECK_INTERVAL seconds (default 600s = 10 min).
   Sends a WhatsApp alert when a watchlist symbol moves beyond its configured
   up/down threshold.

2. Command listener
   Polls Green API every POLL_SECONDS (default 2s) for incoming WhatsApp
   messages. Responds to:

     STATUS              — confirm listener is online + list tracked symbols
     WATCHLIST           — show all symbols with reference prices and thresholds
     REBUY               — completely-sold names with avg buy / avg sell
     PRICE NVDA or Q NVDA — avg sold (all sells) + current Yahoo market
     SUPPORT AAPL        — 3 recent pivot support levels (6-month Yahoo history)
     SOLD  or  SEND      — run C:\Investment\CompletelySoldAlert\run-alert.bat
                           (sends the Completely Sold price digest to WhatsApp)
     RELOAD              — reload watchlists + Sells-sheet avg-sold cache
     HELP  or  ?         — list commands

   Full WhatsApp how-to: AlertApp\README.md

   The listener reacts to BOTH incoming messages AND your own OUTGOING messages
   (sent from the linked phone or the Green API web console). It never replies
   "unknown command" to outgoing messages (avoids reply loops).

EXTRAS
------
- Single-instance mutex (Windows): prevents two listeners racing on the same
  Green API instance (race causes 502 RMQ_ERROR / dropped commands).

- External heartbeat (dead-man's switch): listener pings a URL every 5 min
  so an external service (e.g. healthchecks.io) alerts your phone if the whole
  machine goes down. Configure via ONE of:
    - heartbeat_url.txt  (paste the ping URL, nothing else)
    - Env var: LISTENER_HEARTBEAT_URL
    - config.ini [monitoring] heartbeat_url = <url>

- Watchdog (watchdog.py): checks the mutex and restarts the listener if it died.
  Used by the Task Scheduler jobs (see AUTO-START below).

--------------------------------------------------------------------------------
CREDENTIALS (pick any — env vars override INI)
--------------------------------------------------------------------------------

  1. Environment variables:
       GREEN_API_ID_INSTANCE
       GREEN_API_TOKEN
       WHATSAPP_TARGET_PHONE   (no + sign)

  2. secrets.local.ini  (gitignored — copy from secrets.local.ini.example)
       [whatsapp]
       id_instance = YOUR_ID
       api_token   = YOUR_TOKEN
       target_phone = 1234567890

  3. config.ini [whatsapp]  (same keys — use for non-secret settings only)

--------------------------------------------------------------------------------
WATCHLIST
--------------------------------------------------------------------------------

  Edit config.ini [watchlist]:

    [watchlist]
    AAPL = 230.00, 2.0, 2.0    ; ref_price, up_%, down_%
    TSLA = 320.00, 5.0, 5.0

  Send WATCHLIST via WhatsApp to confirm what the running monitor sees.

  On-demand avg sold + market: send  PRICE NVDA   or   Q NVDA
  (see AlertApp\README.md).

--------------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------------

  Manual / foreground:
    cd C:\Investment\AlertApp
    python backgroundAlert1.py

  Via bat shortcut (same folder):
    run-green-api-listener.bat

  Via root launchers:
    C:\Investment\start_stock_alert.bat   <- start
    C:\Investment\stop_stock_alert.bat    <- stop (targets backgroundAlert1.py only)

  Dependencies:
    pip install yfinance whatsapp-api-client-python

--------------------------------------------------------------------------------
AUTO-START ON REBOOT + SELF-HEALING WATCHDOG
--------------------------------------------------------------------------------

  One-time install (creates Windows Task Scheduler jobs):

    Double-click, or run from CMD:
      install-scheduled-tasks.bat

  Creates two jobs (run only when you are logged on):
    AlertApp-Startup    -> runs watchdog.py at logon  (instant start)
    AlertApp-Watchdog   -> runs watchdog.py every 5 minutes

  watchdog.py:
    - Checks if the listener is running (via its single-instance mutex).
    - If DOWN: starts it detached (output appended to listener.log) and sends
      a WhatsApp message: "listener was DOWN and has been restarted".
    - If UP: does nothing.

  Remove the tasks:
    uninstall-scheduled-tasks.bat

  Check tasks:
    schtasks /Query /TN "AlertApp-Watchdog"
    schtasks /Query /TN "AlertApp-Startup"

  Note: tasks run only while you are logged on (per-user Python install).
  For background-without-login, install system-wide Python and recreate with
  "Run whether user is logged on or not".

--------------------------------------------------------------------------------
SINGLE INSTANCE GUARD
--------------------------------------------------------------------------------

  Green API allows only ONE active receiveNotification consumer per instance.
  Running two listeners causes 502 RMQ_ERROR and dropped / delayed commands.

  This listener holds a Windows named mutex. If you start a second copy it
  prints "[X] Another AlertApp listener is already running." and exits.

  Check what is running:
    Get-CimInstance Win32_Process |
      Where-Object { $_.Name -like 'python*' -and
                     $_.CommandLine -match 'backgroundAlert1' } |
      Select-Object ProcessId, CreationDate

--------------------------------------------------------------------------------
ARCHIVE
--------------------------------------------------------------------------------

  The original AlertApp-IBKR scripts (command-only listener) and the old
  backgroundAlert.py / personalInvestAlert.py are kept in their respective
  archive\ folders for reference. Do NOT run them alongside this script.
  See AlertApp-IBKR\README.md for the full merge history.

================================================================================
