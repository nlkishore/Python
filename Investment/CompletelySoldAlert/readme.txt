================================================================================
  COMPLETELY SOLD PRICE ALERT — Future Reference (C:\Investment)
================================================================================

Last updated: 2026-07-02

This document describes how to run the Python program that:
  1. Reads the IBKR "Completely_Sold" report (fully closed stock positions)
  2. Compares last sold price vs current market price (Yahoo Finance)
  3. Sends ONE WhatsApp digest — by default ALL completely sold stocks with
     their current prices (no -5% threshold). Threshold mode is optional.

You can trigger a run ON DEMAND from your phone by sending "SOLD" (or "SEND")
over WhatsApp — see Section 12 (WhatsApp mobile trigger).

Git copy (same code):  MyGeneratedProjects\GitRepoPlan\repo-consolidated\CompletelySoldAlert\
Design document:      MyGeneratedProjects\GitRepoPlan\repo-consolidated\docs\review\
                      COMPLETELY_SOLD_PRICE_ALERT_DESIGN.md


--------------------------------------------------------------------------------
1. PROGRAMS UNDER C:\Investment (WHAT DOES WHAT)
--------------------------------------------------------------------------------

  A) DATA — Build / refresh the Completely_Sold Excel sheet
     Folder:  C:\Investment\IBKR-Flex-BuySell\
     Script:  flex_buysell_report.py
     Output:  reports\IBKR_BuySell_Since_2020.xlsx  (sheet: Completely_Sold)

     This sheet includes:
       - Symbol, Last_Sold_Price, Last_Sold_Date, Profit, Profit_Pct
       - Current_Market_Price, Price_As_Of (from Yahoo Finance)
       - Change_Since_Last_Sold_Pct = (Current / Last_Sold - 1) x 100

     The alert program does NOT rebuild trades itself; it reads this workbook
     (or triggers flex_buysell_report.py when data is older than 24 hours).

  B) ALERT — Compare prices and send WhatsApp (THIS PROGRAM)
     Folder:  C:\Investment\CompletelySoldAlert\
     Package: completely_sold_alert  (LangGraph workflow)
     Command: python -m completely_sold_alert run

  C) RELATED — Support / resistance report (NOT WhatsApp alerts)
     Folder:  C:\Investment\IBKR-Flex-BuySell\
     Script:  completely_sold_support_report.py
     Output:  reports\Completely_Sold_Support_Resistance.xlsx
     Use for chart levels only; do not confuse with the price-drop alert.


--------------------------------------------------------------------------------
2. NOTIFICATION MODE (CONFIGURABLE)
--------------------------------------------------------------------------------

  Setting file:  config\settings.yaml

  DEFAULT (current):  alert.notify_all_positions: true
    Sends ONE digest listing ALL completely sold symbols that have prices:
      - Symbol, last sold price, current market price, % change vs sold

  OPTIONAL threshold mode:  alert.notify_all_positions: false
    Key: alert.price_drop_threshold_pct  (e.g. -5.0)
    Sends only symbols where Change_Since_Last_Sold_Pct <= threshold


--------------------------------------------------------------------------------
3. ONE-TIME SETUP
--------------------------------------------------------------------------------

  Step 1 — Open CMD and go to the alert project:

    cd C:\Investment\CompletelySoldAlert

  Step 2 — Create virtual environment and install packages:

    python -m venv .venv
    .venv\Scripts\activate.bat
    pip install -r requirements.txt
    pip install whatsapp-api-client-python

  Step 3 — Create config from template:

    copy config\settings.example.yaml config\settings.yaml

  Step 4 — Edit config\settings.yaml:

    alert.notify_all_positions         true = all sold stocks (default)
    alert.price_drop_threshold_pct     only if notify_all_positions is false
    data.report_path                   path to Excel Completely_Sold sheet
    data.flex_project_dir              C:/Investment/IBKR-Flex-BuySell
    data.refresh_mode                  from_downloads  (fast, uses cache)
                                       or download     (calls IBKR API)

  Step 5 — WhatsApp (Green API) — automatic (default):

    If settings.yaml whatsapp fields are empty, credentials are loaded automatically from:
      C:\Investment\AutomatedTrading\config.ini   [trading] whatsapp_id_instance, etc.
    (Same keys used by AlertApp / ChartSupportResistanceWhatsApp_IBKR.)

    Optional overrides:
      Method A — Environment variables: GREEN_API_ID_INSTANCE, GREEN_API_TOKEN,
                 WHATSAPP_TARGET_PHONE
      Method B — Put values in config\settings.yaml under whatsapp:
      Method C — config\whatsapp.ini with [whatsapp] or [trading] section

  Step 6 — Ensure IBKR report exists (first time):

    cd C:\Investment\IBKR-Flex-BuySell
    python flex_buysell_report.py --from-downloads

    If that fails with "Permission denied" on the xlsx file, close Excel and
    retry, OR write to the alert data folder:

    python flex_buysell_report.py --from-downloads ^
      --output C:\Investment\CompletelySoldAlert\data\IBKR_BuySell_Since_2020.xlsx

    Then set data.report_path in settings.yaml to that output path.


--------------------------------------------------------------------------------
4. HOW TO EXECUTE — QUICK REFERENCE
--------------------------------------------------------------------------------

  Always activate venv first:

    cd C:\Investment\CompletelySoldAlert
    .venv\Scripts\activate.bat

  --- Production run (NYSE market days only; sends WhatsApp) ---

    python -m completely_sold_alert run

  Or use the batch wrapper (all of these work; "run" is the default command):

    run-alert.bat
    run-alert.bat run
    run-alert.bat --dry-run
    run-alert.bat status

  --- Preview without sending WhatsApp ---

    python -m completely_sold_alert run --dry-run --print-digest

  --- Run on weekend / holiday for testing ---

    python -m completely_sold_alert run --dry-run --force-market-day --print-digest

  --- Test with sample data (no IBKR file needed) ---

    python -m completely_sold_alert run --fixture fixtures\completely_sold_sample.json ^
      --dry-run --force-market-day --print-digest

  --- Check last export time and cooldown symbols ---

    python -m completely_sold_alert status

  --- Refresh IBKR Excel only (no alert) ---

    python -m completely_sold_alert refresh-only

  --- Refresh IBKR manually (alternative) ---

    cd C:\Investment\IBKR-Flex-BuySell
    python flex_buysell_report.py --from-downloads


--------------------------------------------------------------------------------
5. WHAT HAPPENS WHEN YOU RUN "run" (WORKFLOW)
--------------------------------------------------------------------------------

  1. check_market_day
     - Skips Saturdays, Sundays, and NYSE holidays (if run_market_days_only: true)
     - On skip: exits quietly (no error, no WhatsApp)

  2. check_freshness
     - If Excel report / last export is older than 24 hours (data.max_age_hours):
       runs flex_buysell_report.py in IBKR-Flex-BuySell

  3. load_completely_sold
     - Reads sheet "Completely_Sold" from the Excel file

  4. evaluate_alerts
     - Default: all completely sold rows with last sold / current price
     - Threshold mode: only rows <= price_drop_threshold_pct
     - Per-symbol cooldown applies only in threshold mode

  5. format_digest + send_digest
     - Builds ONE readable WhatsApp message (all qualifying symbols)
     - Sends via Green API

  If no symbols qualify: ends with "Done. No alerts triggered."


--------------------------------------------------------------------------------
6. SAMPLE WHATSAPP DIGEST FORMAT
--------------------------------------------------------------------------------

  DEFAULT (notify_all_positions: true) — title "Completely Sold — Price Summary":

    *Completely Sold — Price Summary*
    Date | N symbol(s) with prices

    Per symbol:
      Last sold: $X  (sold date)
      Now:       $Y  (as of quote date)
      Change:    +/-Z% vs last sold
      P&L when sold: $... (...%)

    Footer: total completely sold, "no price data" count, data source.

  THRESHOLD mode (notify_all_positions: false) — title "Price Drop Alert":

    *Completely Sold — Price Drop Alert*
    Date | N symbol(s) (<= -5.0% vs last sold)
    Same per-symbol block; only symbols at/below threshold are listed.

  Note: digest_max_symbols (default 15) caps how many symbols appear in ONE
  message; extras are summarized as an overflow count. Raise it in settings.yaml
  if you want all symbols in a single message.


--------------------------------------------------------------------------------
7. WINDOWS TASK SCHEDULER (OPTIONAL AUTOMATION)
--------------------------------------------------------------------------------

  Program:   C:\Investment\CompletelySoldAlert\run-alert.bat
  Arguments: run
  Start in:  C:\Investment\CompletelySoldAlert
  Trigger:   Daily ~4:30 PM Eastern (after US market close)
  Note:      Graph still skips non-trading days even if task runs daily.


--------------------------------------------------------------------------------
8. CONFIGURATION REFERENCE (settings.yaml)
--------------------------------------------------------------------------------

  alert:
    notify_all_positions: true        # all sold stocks + prices (default)
    price_drop_threshold_pct: -5.0     # only when notify_all_positions: false

  data:
    max_age_hours: 24                  # re-run flex report if older
    flex_project_dir: C:/Investment/IBKR-Flex-BuySell
    report_path: ...\IBKR_BuySell_Since_2020.xlsx
    flex_python: python
    refresh_mode: from_downloads       # or download

  schedule:
    run_market_days_only: true
    market_calendar: NYSE
    timezone: America/New_York

  notify:
    mode: digest                       # single message (fixed in v1)
    cooldown_hours: 24
    digest_max_symbols: 15

  whatsapp:
    provider: green_api
    (id_instance, api_token, target_phone — or use env vars)


--------------------------------------------------------------------------------
9. FILES AND FOLDERS (LOCAL — NOT IN GIT)
--------------------------------------------------------------------------------

  config\settings.yaml          Your secrets and paths (create from .example)
  data\last_export.json         Last successful load timestamp
  data\alert_cooldown.json      Per-symbol last alert time
  data\IBKR_BuySell_Since_2020.xlsx   Optional copy of report if main file locked
  .venv\                        Python virtual environment


--------------------------------------------------------------------------------
10. TROUBLESHOOTING
--------------------------------------------------------------------------------

  Problem: Permission denied writing IBKR xlsx
  Fix:     Close Excel file in reports\ folder, or use --output to data\ folder

  Problem: Skipped: non_trading_day
  Fix:     Normal on weekends/holidays; use --force-market-day for testing

  Problem: WhatsApp credentials missing
  Fix:     Set GREEN_API_* env vars or fill settings.yaml whatsapp section.
           By default they auto-load from AutomatedTrading\config.ini [trading].

  Problem: Run says "Sent: True" but no WhatsApp message arrives
  Fix:     The Green API instance is likely NOT AUTHORIZED. Green API returns
           HTTP 200 even when the phone link is lost. The app now checks the
           instance state before sending and will report:
             "Green API instance not authorized (state='notAuthorized')".
           Re-link: open https://console.green-api.com, select the instance,
           scan the QR under Linked Devices, wait for state=authorized.
           Verify state quickly:
             .venv\Scripts\python.exe -c "from completely_sold_alert.config import load_settings; from whatsapp_api_client_python import API; s=load_settings(); w=s.whatsapp; print(API.GreenAPI(w.id_instance, w.api_token).account.getStateInstance().data)"

  Problem: "unrecognized arguments: run" from run-alert.bat
  Fix:     Fixed. The batch wrapper passes args straight through and the CLI
           defaults to the "run" command; do not pass "run" twice.

  Problem: No alerts but stocks dropped a lot
  Fix:     Run flex report to refresh prices; check threshold sign (must be negative)
           Check cooldown: python -m completely_sold_alert status

  Problem: flex_buysell_report fails
  Fix:     Ensure config.ini exists in IBKR-Flex-BuySell; use --from-downloads first

  Problem: SIVB / delisted symbol warnings during flex report
  Fix:     Expected; other symbols still process. Row may lack Current_Market_Price.


--------------------------------------------------------------------------------
11. RELATED DOCUMENTATION
--------------------------------------------------------------------------------

  C:\Investment\CompletelySoldAlert\README.md          (Markdown quick start)
  C:\Investment\INVESTMENT-PROGRAMS-REFERENCE.md     Section 9 — CompletelySoldAlert
  C:\Investment\IBKR-Flex-BuySell\Readme.md            Completely_Sold sheet columns
  C:\Investment\AlertApp\readme.txt                    Green API setup notes
  C:\Investment\AlertApp-IBKR\readme.txt               WhatsApp command listener (SOLD/SEND)

  Prompts / design (repo-consolidated):
    docs\COMPLETELY_SOLD_PRICE_ALERT_PLAN.md
    docs\review\COMPLETELY_SOLD_PRICE_ALERT_DESIGN.md


--------------------------------------------------------------------------------
12. WHATSAPP MOBILE TRIGGER (RUN ON DEMAND FROM YOUR PHONE)
--------------------------------------------------------------------------------

  You cannot run this .bat directly from the Cursor mobile app (Cursor cloud
  agents run in a remote sandbox and have no access to your PC / C:\Investment).
  Instead, trigger it over WhatsApp using the Green API command listener.

  Listener program:
    Folder:  C:\Investment\AlertApp-IBKR
    Script:  backgroundAlert.py
    Start:   run-green-api-listener.bat     (keep the window open)

  Commands (send as a WhatsApp message to the Green API number):
    STATUS          -> replies "AlertApp-IBKR Online"
    SOLD  or  SEND  -> runs CompletelySoldAlert (sends the price summary digest)
    SUPPORT AAPL    -> pivot support levels for a symbol

  How the trigger works:
    - The listener polls Green API for message notifications every ~2 seconds.
    - On SOLD/SEND it launches C:\Investment\CompletelySoldAlert\run-alert.bat,
      which sends its own WhatsApp digest.
    - It reacts to BOTH incoming messages (from another phone) AND your own
      OUTGOING messages (sent from the linked phone or the Green API web
      console). This is why sending "SOLD" from your own linked phone works.
    - Loop protection: the listener never replies "unknown command" to outgoing
      messages, so it will not react to its own replies.

  Requirements for the trigger to work:
    1. The listener (backgroundAlert.py) must be running on the PC.
    2. The Green API instance must be AUTHORIZED (see Troubleshooting).
    3. The PC must be powered on and online.

  Check whether the listener is running (PowerShell):
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -match 'backgroundAlert' } |
      Select-Object ProcessId, CommandLine

  Stop the listener:
    Close the CMD window, Ctrl+C, or end the python.exe process.

  Note: The listener and the alert share the SAME Green API instance and
  credentials (AutomatedTrading\config.ini [trading]).

  SINGLE INSTANCE ONLY: Green API permits only one receiveNotification consumer
  per instance. The listener enforces this with a Windows named mutex, so a
  second copy refuses to start ("Another AlertApp-IBKR listener is already
  running"). Running two would cause 502 "consumer closed" errors and
  dropped / delayed SOLD commands. See AlertApp-IBKR\readme.txt.

  The on-demand SOLD/SEND run uses --force-market-day, so it returns the price
  summary even on weekends / NYSE holidays.


================================================================================
  END OF readme.txt
================================================================================
