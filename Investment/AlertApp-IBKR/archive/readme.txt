================================================================================
  AlertApp-IBKR — Green API WhatsApp Command Listener
================================================================================

Folder: C:\Investment\AlertApp-IBKR
Script: backgroundAlert.py

Listens for WhatsApp messages via Green API and responds to:
  STATUS              — confirms listener is online
  SUPPORT AAPL        — 3 recent pivot support levels (6-month Yahoo data)
  SOLD  or  SEND      — runs C:\Investment\CompletelySoldAlert\run-alert.bat,
                        which sends the "Completely Sold — Price Summary" digest

The listener reacts to BOTH incoming messages (from another phone) AND your own
OUTGOING messages (sent from the linked phone or the Green API web console), so
you can trigger commands from your own WhatsApp. It never replies "unknown
command" to outgoing messages, avoiding a reply loop.

Requires the Green API instance to be AUTHORIZED (scan QR at
https://console.green-api.com if state is notAuthorized).

--------------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------------

  cd C:\Investment\AlertApp-IBKR
  python backgroundAlert.py

  Or double-click / run:
  run-green-api-listener.bat

  Dependencies:
    pip install yfinance whatsapp-api-client-python pandas

--------------------------------------------------------------------------------
CREDENTIALS (pick one)
--------------------------------------------------------------------------------

  1. Environment variables:
       GREEN_API_ID_INSTANCE
       GREEN_API_TOKEN
       WHATSAPP_TARGET_PHONE   (no + sign)

  2. AutomatedTrading config (auto-loaded if present):
       C:\Investment\AutomatedTrading\config.ini
       [trading] whatsapp_id_instance, whatsapp_api_token_instance, whatsapp_target_phone

  3. Local config.ini in this folder with same keys.

--------------------------------------------------------------------------------
SINGLE INSTANCE ONLY (RACE-CONDITION GUARD)
--------------------------------------------------------------------------------

  Green API allows only ONE active receiveNotification consumer per instance.
  Running two listeners causes "consumer closed" (502 RMQ_ERROR) errors and
  dropped / delayed commands.

  This listener enforces a single instance using a Windows named mutex
  ("Global\AlertApp_IBKR_GreenAPI_Listener"). If you start it while another
  copy is already running, the new one prints:

    [X] Another AlertApp-IBKR listener is already running. Exiting...

  and exits immediately. The lock is released automatically by the OS when the
  running listener stops (no stale-lock cleanup needed).

  Check what is running:
    Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and
      $_.CommandLine -match 'backgroundAlert' } | Select-Object ProcessId, CreationDate

--------------------------------------------------------------------------------
AUTO-START ON REBOOT + SELF-HEALING WATCHDOG
--------------------------------------------------------------------------------

  Goal: keep the listener running after a PC restart and restart it if it dies.

  One-time install (creates Windows scheduled tasks):

    Double-click, or run from CMD:
      install-scheduled-tasks.bat

  This creates two Task Scheduler jobs (run only when you are logged on):
    AlertApp-IBKR-Startup    -> runs the watchdog at logon (instant start)
    AlertApp-IBKR-Watchdog   -> runs the watchdog every 5 minutes

  watchdog.py:
    - Checks if the listener is running (via its single-instance mutex).
    - If DOWN: starts it detached (no window; output appended to listener.log)
      and sends a WhatsApp message: "listener was DOWN and has been restarted".
    - If UP: does nothing (mutex prevents duplicates).

  Remove the tasks:
    uninstall-scheduled-tasks.bat

  Check tasks:
    schtasks /Query /TN "AlertApp-IBKR-Watchdog"
    schtasks /Query /TN "AlertApp-IBKR-Startup"

  Note: tasks run only while you are logged on (this PC uses a per-user Python).
  If you need it to run without logging in, install a real (all-users) Python
  and recreate the tasks with "Run whether user is logged on or not".

--------------------------------------------------------------------------------
NOTIFY IF THE MACHINE ITSELF IS DOWN (EXTERNAL HEARTBEAT)
--------------------------------------------------------------------------------

  IMPORTANT: A watchdog can only recover the process while the PC is ON. If the
  whole machine is down (power loss, no internet, OS crash), it cannot warn you
  — a down machine cannot notify itself. The reliable pattern is an EXTERNAL
  "dead-man's switch": the listener pings an outside service on a schedule, and
  that service alerts your phone when the pings STOP.

  Recommended: https://healthchecks.io (free)
    1. Create an account and a new "Check".
       Set Period = 10 minutes, Grace = 10 minutes.
    2. Add a notification integration to your PHONE:
       - healthchecks.io mobile app (push), or
       - Telegram / Pushover / Signal / email / etc.
    3. Copy the check's ping URL, e.g.:
         https://hc-ping.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    4. Save it so the listener can find it (any ONE of these):
       - Create file:  heartbeat_url.txt   (paste the URL, nothing else)
       - OR set env var:  LISTENER_HEARTBEAT_URL
       - OR config.ini [monitoring] heartbeat_url = <url>
    5. Restart the listener. It logs "Heartbeat: enabled" and pings every 5 min.

  Now: if the listener stops pinging (machine down, no net, process dead and not
  restarted), healthchecks.io notifies your phone after the grace period.

  This complements STATUS: send STATUS anytime to actively confirm it's alive.

--------------------------------------------------------------------------------
STOP THE LISTENER
--------------------------------------------------------------------------------

  Close the CMD window, or Ctrl+C, or end the python.exe / pythonw.exe process.
  If the watchdog tasks are installed, they will restart it within 5 minutes;
  run uninstall-scheduled-tasks.bat first if you want it to stay stopped.

================================================================================
