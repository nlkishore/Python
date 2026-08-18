# IBKR Client Portal Gateway — Quick Reference

Local install for the **Interactive Brokers Client Portal Web API** (REST on HTTPS port **5000**).

Used by scripts such as:

- `C:\Investment\SeasonalStocks\seasonaStockLowAndHigh.py`
- `C:\Investment\AutomatedTrading\ChartSupportAndSignals_IBKR.py`

---

## Install layout

```text
C:\Investment\IBKR-Client-GateWay\
  Start-IBKR-Gateway.bat      ← recommended (CMD)
  Start-IBKR-Gateway.ps1      ← PowerShell (if allowed)
  clientportal.gw\
    bin\run.bat               ← IBKR launcher (do not run alone without config)
    root\conf.yaml            ← listenPort: 5000, SSL on
    dist\                     ← gateway JAR
    build\                    ← runtime libraries
    logs\                     ← gateway logs (gw.YYYY-MM-DD.log)
    doc\GettingStarted.md     ← official IBKR guide
```

**Important:** The gateway must be started from the **`clientportal.gw`** folder with config path **`root\conf.yaml`**. Starting `run.bat` from `bin` without the correct working directory causes `ClassNotFoundException`.

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Java** | 8 update 192+ or **Java 11/17** (tested with Java 17) |
| **Network** | Outbound HTTPS to `api.ibkr.com` |
| **IBKR account** | Paper or live login credentials |

Check Java:

```cmd
java -version
```

---

## Start the gateway (recommended)

### Option A — CMD (no PowerShell)

Double-click or run:

```cmd
C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.bat
```

### Option B — Manual (same as IBKR docs)

```cmd
cd C:\Investment\IBKR-Client-GateWay\clientportal.gw
bin\run.bat root\conf.yaml
```

### Option C — PowerShell

```powershell
PowerShell -ExecutionPolicy Bypass -File "C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.ps1"
```

**Keep the gateway window open** while using any API scripts.

When startup succeeds, the console/log shows the gateway listening on **port 5000** (see `clientportal.gw\logs\gw.<date>.log`).

---

## Log in (required once per session)

1. Open in a browser: **https://localhost:5000**
2. Log in with your IBKR username and password.
3. Complete 2FA if prompted.
4. When authentication succeeds, you may close the browser tab (gateway keeps running).

---

## Verify API is ready

### Browser

Open: https://localhost:5000

### Command line (after login)

```cmd
curl -k -X POST https://localhost:5000/v1/api/iserver/auth/status
```

### Python (same check as seasonal script)

```cmd
python -c "import requests,urllib3; urllib3.disable_warnings(); r=requests.post('https://localhost:5000/v1/api/iserver/auth/status', verify=False); print(r.status_code, r.text)"
```

Expected after login (example):

```json
{"authenticated": true, "connected": true, ...}
```

Before login you may see **401** or `authenticated: false` — that means the gateway is running but you still need to log in.

---

## Run dependent scripts

Example — seasonal stocks analysis:

```cmd
cd C:\Investment
python SeasonalStocks\seasonaStockLowAndHigh.py
```

---

## Configuration

Main settings: `clientportal.gw\root\conf.yaml`

| Setting | Default | Purpose |
|---------|---------|---------|
| `listenPort` | `5000` | Local HTTPS port |
| `listenSsl` | `true` | HTTPS (scripts use `verify=False` for self-signed cert) |
| `proxyRemoteHost` | `https://api.ibkr.com` | IBKR backend |

If you change the port, update scripts that use `https://localhost:5000/v1/api`.

---

## Optional environment variables

Set once (User environment variables) so start scripts find the install:

| Variable | Example value |
|----------|----------------|
| `IBKR_GATEWAY_ROOT` | `C:\Investment\IBKR-Client-GateWay\clientportal.gw` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|--------|-----|
| `WinError 10061` / connection refused | Gateway not running | Run `Start-IBKR-Gateway.bat` |
| `ClassNotFoundException: GatewayStart` | Wrong working directory | Use `Start-IBKR-Gateway.bat` or start from `clientportal.gw` |
| HTTP **401** on auth/status | Gateway up, not logged in | Open https://localhost:5000 and login |
| `authenticated: false` | Session expired | Re-login in browser |
| Port 5000 in use | Another app on 5000 | Stop conflicting process or change `listenPort` in `conf.yaml` |

**Logs:** `clientportal.gw\logs\gw.YYYY-MM-DD.log`

---

## Client Portal vs TWS / IB Gateway (socket)

| Product | Port | Used by these scripts? |
|---------|------|-------------------------|
| **Client Portal Gateway** (this install) | 5000 (HTTPS REST) | **Yes** |
| TWS / IB Gateway (socket API) | 7496 / 7497 | No — different API |

---

## Daily workflow (summary)

1. Run `Start-IBKR-Gateway.bat`
2. Login at https://localhost:5000
3. Verify auth/status shows authenticated
4. Run your Python scripts
5. Close gateway window when finished

---

## References

- IBKR local guide: `clientportal.gw\doc\GettingStarted.md`
- IBKR API: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/
