# Investment — stock WhatsApp monitor

**IBKR Excel reports (Buy/Sell, Trade history, Withholding):** see [`IBKR-REPORTS-GUIDE.md`](IBKR-REPORTS-GUIDE.md) and folder [`reports\`](reports/).

**Full folder reference (all programs):** see [`INVESTMENT-PROGRAMS-REFERENCE.md`](INVESTMENT-PROGRAMS-REFERENCE.md)

**Cleanup / tidy backlog (do one item at a time):** see [`CLEANUP-AND-TIDY-PLAN.md`](CLEANUP-AND-TIDY-PLAN.md)

Python tool to watch Yahoo Finance symbols against up/down percentage thresholds and send alerts to WhatsApp (CallMeBot or Twilio). Configuration is in `config.ini` (copy from `config.ini.example` or `config.ini.example-fixed-ref`).

**Supported Green API alert path:** `start_stock_alert.bat` → `AlertApp\backgroundAlert1.py` (credentials in `AlertApp\config.ini` + optional `secrets.local.ini`; see `AlertApp\config.ini.example`).

**Secrets:** never commit `config.ini`, `secrets.local.ini`, or API keys in source. Copy `*.example` templates and fill locally.

## Python virtual environment

Use a virtual environment so dependencies stay isolated from your system Python.

### Windows (PowerShell)

From `C:\Investment`:

```powershell
# Create a venv in the folder .venv
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# If execution policy blocks activation, run once (current user):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt
```

Deactivate when finished:

```powershell
deactivate
```

### Windows (Command Prompt)

```cmd
cd C:\Investment
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### macOS / Linux

```bash
cd /path/to/Investment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. Copy an example to `config.ini`:

   ```powershell
   copy config.ini.example config.ini
   ```

   For **fixed reference prices per symbol**, start from `config.ini.example-fixed-ref` instead.

2. Edit `config.ini`: symbols, thresholds, WhatsApp `phone` / `apikey` (or Twilio fields).

3. **Do not commit** `config.ini` if it contains secrets (it is listed in `.gitignore`).

## Run

With the venv **activated**:

```powershell
# Continuous monitoring
python stock_whatsapp_monitor.py

# One check, then exit (good for testing)
python stock_whatsapp_monitor.py --once

# Use a specific config file
python stock_whatsapp_monitor.py --config .\my-config.ini
```

## Requirements

- Python 3.10+ recommended (uses modern type hints).
- Packages: see `requirements.txt` (`yfinance`, `requests`).

## More detail

- **CallMeBot setup:** [CallMeBot WhatsApp API](https://www.callmebot.com/blog/free-api-whatsapp-messages/)
- **Multi-symbol** and **fixed reference prices:** comments in `config.ini.example` and `config.ini.example-fixed-ref`
