PythonPath : C:\Users\nlaxm\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe
scriptPath:C:\Investment\AlertApp\backgroundAlert.py



The **Green API** is the ideal "background" choice because it operates via a cloud-based gateway. Unlike the previous method, this script does not need to open a browser window or keep a WhatsApp Web tab active; it sends messages directly through the Green API servers.

### 1. Setup (Free Tier)
To use this, you need a free developer account:
1.  Go to [Green-API.com](https://green-api.com/) and create a free **"Developer"** instance.
2.  Scan the QR code in the Green API console using your phone's WhatsApp (Linked Devices).
3.  Copy your **ID_INSTANCE** and **API_TOKEN_INSTANCE**.

### 2. The Python Script
You will need to install the Green API SDK and `yfinance`:
```bash
pip install whatsapp-api-client-python yfinance
```

```python
import yfinance as yf
from whatsapp_api_client_python import API
import time

# --- Configuration ---
ID_INSTANCE = "YOUR_ID_INSTANCE_HERE"
API_TOKEN_INSTANCE = "YOUR_API_TOKEN_HERE"
TARGET_PHONE = "1234567890"  # Your number with country code, NO '+' sign

# Symbols: [Reference_Price, Up_%, Down_%]
WATCHLIST = {
    "AAPL": [180.00, 2.0, 2.0],
    "TSLA": [200.00, 5.0, 5.0]
}

# Initialize Green API
greenAPI = API.GreenAPI(ID_INSTANCE, API_TOKEN_INSTANCE)

def send_whatsapp(text):
    # Green API format for individual chat is 'number@c.us'
    chat_id = f"{TARGET_PHONE}@c.us"
    response = greenAPI.sending.sendMessage(chat_id, text)
    if response.code == 200:
        print("✅ Alert sent successfully!")
    else:
        print(f"❌ Failed to send: {response.error}")

def monitor_stocks():
    print("Checking prices...")
    for symbol, config in WATCHLIST.items():
        ref_price, up_pct, down_pct = config
        
        # Fetch data
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if data.empty: continue
        
        current_price = data['Close'].iloc[-1]
        change = ((current_price - ref_price) / ref_price) * 100
        
        print(f"{symbol}: ${current_price:.2f} ({change:+.2f}%)")

        if change >= up_pct:
            msg = f"🚀 *STOCK UP ALERT*\n{symbol} is at ${current_price:.2f}\nChange: {change:.2f}%"
            send_whatsapp(msg)
        elif change <= -down_pct:
            msg = f"📉 *STOCK DOWN ALERT*\n{symbol} is at ${current_price:.2f}\nChange: {change:.2f}%"
            send_whatsapp(msg)

# Run loop every 10 minutes
if __name__ == "__main__":
    while True:
        try:
            monitor_stocks()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(600) 
```

---

### Why this is better for your use case:
* **Headless:** You can run this script on a cheap cloud VPS, a Raspberry Pi, or just leave it running in the background of your PC without any windows popping up.
* **Stability:** Since it doesn't rely on browser automation (DOM elements), it won't break if WhatsApp updates its website layout.
* **Formatting:** You can use WhatsApp Markdown (like `*bold*` or `_italics_`) easily in the string.

### Important Note on the Free Tier:
The Green API "Developer" (Free) plan allows you to send messages to up to **3 specific contacts**. Since you are only sending alerts to your own personal number, this fits perfectly within the free limits.

**Would you like me to show you how to wrap this script as a Windows Service or a Linux Cron Job so it starts automatically when your computer turns on?**


To wrap a Python script as a Windows Service, the most reliable way is using a utility called **NSSM (Non-Sucking Service Manager)**. While there are Python libraries like `pywin32` for this, they are notoriously difficult to debug. NSSM is the industry standard for turning any `.exe` or script into a background service.

### 1. Prerequisites
1.  **Download NSSM:** Get it from [nssm.cc](https://nssm.cc/download).
2.  **Extract:** Copy `nssm.exe` (the one in the `win64` folder) to a permanent folder, e.g., `C:\tools\nssm.exe`.
3.  **Refine your Script:** Ensure your script uses **absolute paths** for any files it reads/writes, as Services run in the `System32` directory by default.

---

### 2. Preparing the Python Executable
Since a service needs a stable environment, identify your Python path and script path:
* **Python Path:** Usually `C:\Users\<YourUser>\AppData\Local\Programs\Python\Python311\python.exe`
* **Script Path:** Wherever you saved your Green API script, e.g., `C:\Scripts\stock_alert.py`

---

### 3. Creating the Service
1.  Open **Command Prompt** or **PowerShell** as **Administrator**.
2.  Navigate to the folder where you placed `nssm.exe`.
3.  Run the following command:
    ```cmd
    nssm install StockAlertService
    ```
4.  A GUI window will pop up. Fill it out as follows:

| Field | Value |
| :--- | :--- |
| **Path** | Browse to your `python.exe` |
| **Startup directory** | Browse to the folder containing your script |
| **Arguments** | `C:\Scripts\stock_alert.py` (The full path to your script) |

5.  Go to the **Details** tab and set the **Display name** (e.g., "Python Stock Alert").
6.  Go to the **Exit Actions** tab and ensure "Restart" is selected so the service recovers if it crashes.
7.  Click **Install service**.

---

### 4. Managing the Service
You can now treat this like any other Windows background process:

* **Start it:** `nssm start StockAlertService` (or use the Windows **Services.msc** app).
* **Check Status:** `nssm status StockAlertService`.
* **Edit Settings:** `nssm edit StockAlertService`.
* **Remove it:** `nssm remove StockAlertService confirm`.

---

### 5. Essential Logging (Highly Recommended)
Because Services run in the background, you won't see "Print" statements. You should tell NSSM to capture your script's output to a file so you can troubleshoot:

1.  Run `nssm edit StockAlertService`.
2.  Go to the **I/O** tab.
3.  Set **Output (stdout)** and **Error (stderr)** to a log file path, e.g., `C:\Scripts\log.txt`.

---

### Why this is better for your Green API script:
* **Auto-Start:** The alerts will start monitoring as soon as you boot Windows, even before you log in.
* **Background:** No command prompt windows will be sitting on your taskbar.
* **Self-Healing:** If your internet drops and the script crashes, Windows will automatically restart it.

**Would you like me to add a small logging block to your Python script so it records exactly when it sends an alert to that log file?**


https://console.green-api.com/instanceList