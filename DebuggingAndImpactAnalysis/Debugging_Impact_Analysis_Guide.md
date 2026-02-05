# Debugging & Impact Analysis Guide: Banking Architecture

**Context**: Unix OS, JBoss EAP, Oracle DB, Web Application.

This document outlines a standardized procedure to trace a feature's execution from the browser down to the database, enabling comprehensive impact analysis.

## 1. Identify Modified Application Logs

When a test is executed, JBoss writes to specific log files.

**Procedure**:
1.  **Locate Log Directory**: Typically `/app/jboss/standalone/log/` or `/var/log/jboss/`.
2.  **Find Recently Modified Files**:
    ```bash
    # List files modified in the last 60 minutes
    find /app/jboss/standalone/log -type f -mmin -60 -ls
    ```
3.  **Key Files**:
    *   `server.log`: Main application logs (Business logic, Exceptions).
    *   `access_log`: HTTP requests (URL hits, Status codes 200/404/500).
    *   `gc.log`: Garbage Collection (if performance is the issue).

## 2. Extract Logs by Time Window

Extract only the logs relevant to your specific test duration to reduce noise.

**Unix Command Strategy**:
Assuming `server.log` uses ISO timestamps (e.g., `2024-02-05 10:00:00`).

```bash
# Define Test Window
START_TIME="2024-02-05 10:00"
END_TIME="2024-02-05 10:15"

# 1. Create a specific directory for the test artifact
mkdir -p /tmp/debug_artifacts/test_run_001

# 2. Extract server logs falling within the window
# Note: This sed command assumes lines start with the date. 
# Adjust the regex based on your specific log4j pattern.
sed -n "/$START_TIME/,/$END_TIME/p" /app/jboss/log/server.log > /tmp/debug_artifacts/test_run_001/server_partial.log

# 3. Copy Access Logs (usually rotate daily, but valid for extraction)
cp /app/jboss/log/access_log /tmp/debug_artifacts/test_run_001/

# 4. Zip generic artifacts
tar -czf /tmp/test_run_001.tar.gz /tmp/debug_artifacts/test_run_001/
```

## 3. Identify Modified Database Tables (Oracle)

Determining which tables were touched requires querying metadata or relying on audit columns.

**Method A: Check `last_ddl_time` (Schema Changes)**
If the feature modified table structures:
```sql
SELECT object_name, object_type, last_ddl_time 
FROM user_objects 
WHERE last_ddl_time > TO_DATE('2024-02-05 10:00:00', 'YYYY-MM-DD HH24:MI:SS');
```

**Method B: Check Row Updates (Data Changes)**
Assuming tables have standard auditing columns (`UPDATE_TIMESTAMP` or `MODIFIED_DATE`):
```sql
-- Dynamic query to find tables with recent activity
-- (Requires a script to iterate all tables, here is the logic)
SELECT count(*) FROM ACCOUNTS 
WHERE MODIFIED_DATE BETWEEN TO_DATE('...', ...) AND TO_DATE('...', ...);
```

**Method C: Oracle Flashback Query (Advanced)**
See what data looked like before the test:
```sql
SELECT * FROM TRANSACTIONS AS OF TIMESTAMP TO_TIMESTAMP('2024-02-05 10:00:00', 'YYYY-MM-DD HH24:MI:SS')
MINUS
SELECT * FROM TRANSACTIONS;
```
> [!NOTE]
> **Permissions Required**: This method requires the user to have the `FLASHBACK` privilege on the specific table or the `FLASHBACK ANY TABLE` system privilege. It does **not** strictly require DBA/Admin rights, but standard users often lack this by default. Also, the DB must have Automatic Undo Management enabled with sufficient retention.

## 4. Derive End-to-End Flow

To map **Browser Action** -> **Server File** -> **DB Table**:

1.  **Step 1 (Browser)**: Identify the API call (e.g., `POST /api/transfer`).
2.  **Step 2 (Access Log)**: Confirm the hit in JBoss `access_log`.
    `10.0.0.1 - - [05/Feb/2024:10:05:00] "POST /api/transfer HTTP/1.1" 200`
3.  **Step 3 (Server Log)**: Correlate Thread ID.
    `INFO  [com.bank.Controller] (default task-12) Processing transfer...`
    *(Tip: Use "default task-12" to grep the entire thread usage).*
4.  **Step 4 (Code)**: Search the code for the Controller handling `/api/transfer`.
5.  **Step 5 (JPA/Hibernate)**: Look for `@Table` annotations in the Entities used by that Controller.

## 5. Automated Console Logs (No-Driver Approach)

Since Selenium is restricted, use the **Chrome DevTools Protocol (CDP)**. This works directly with the installed Chrome browser and **requires no separate driver binaries** to be managed.

**Method A: Python + CDP (Recommended)**
You interact directly with Chrome's debugging port using standard Python libraries (`requests`, `websocket-client`).

1.  **Launch Chrome with Debugging Port**:
    ```bash
    "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
    ```

2.  **Python Script to Capture Logs**:
    ```python
    import websocket # pip install websocket-client
    import json
    import requests

    def on_message(ws, message):
        data = json.loads(message)
        # Filter for Console API events
        if "method" in data and data["method"] == "Runtime.consoleAPICalled":
            log_type = data["params"]["type"]
            args = data["params"]["args"]
            content = " ".join([str(arg.get("value", "")) for arg in args])
            print(f"[{log_type.upper()}] {content}")

    # 1. Get the WebSocket URL for the active tab
    resp = requests.get("http://localhost:9222/json")
    tab_info = resp.json()[0]
    ws_url = tab_info["webSocketDebuggerUrl"]

    # 2. Connect and Enable Runtime events
    ws = websocket.WebSocketApp(ws_url, on_message=on_message)
    ws.on_open = lambda ws: ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
    ws.run_forever()
    ```

**Method B: JavaScript Log Forwarding (Monkey Patch)**
If you cannot run Python scripts, inject this JavaScript into the browser console (or page header) to send logs to your JBoss server (or any endpoint).

```javascript
(function(){
    var oldLog = console.log;
    console.log = function(message) {
        // 1. Send to server
        fetch('/api/log-client-error', {
            method: 'POST',
            body: JSON.stringify({ msg: message, time: new Date() })
        });
        // 2. Resume normal logging
        oldLog.apply(console, arguments);
    };
})();
```

## 6. FAQ: Physical Location of Browser Logs

**Q: Are console logs saved to a file on the client machine (like server.log)?**
**A: No.** By default, browsers (Chrome/Edge/Firefox) keep console logs **in-memory only**. They are lost when you close the tab or browser.

**How to force logging to a file (Chrome/Edge):**
You must start the browser with special flags.

1.  **Close all Chrome instances.**
2.  **Run from Command Line:**
    ```bash
    # Windows
    "C:\Program Files\Google\Chrome\Application\chrome.exe" --enable-logging --v=1

    # Unix/Mac
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --enable-logging --v=1
    ```
3.  **Location**:
    *   Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\chrome_debug.log`
    *   Linux: `~/.config/google-chrome/chrome_debug.log`

**Warning**: This captures *internal* browser debug info, which is very noisy. For application debugging, the **Selenium (Section 5)** approach is superior as it captures only the JS Console output.

## 7. Automated Impact Analysis Tool (`ImpactAnalyzer`)

We have built a custom Python tool (`C:\Python\ImpactAnalyzer`) to automate the collection of all the above artifacts (Logs, DB Changes, Browser Console).

**Features:**
*   **Multi-Market Support**: Works for SG, MY, TH, etc.
*   **Multi-App Support**: Customer vs Bank Admin.
*   **Unified Report**: Generates a ZIP file containing Server Logs, DB Report, and Browser Logs.

**Usage**:

1.  **Configure**: Update `config.json` with your credentials/hosts.
2.  **Run**:
    ```powershell
    # Syntax: python main.py --market <MARKET> --app <APP_TYPE> --duration <MINUTES>
    
    # Example: Debug SG Customer App for 10 minutes
    python main.py --market SG --app customer --duration 10
    ```
3.  **Result**: A consolidated report will be generated in `reports/`.
