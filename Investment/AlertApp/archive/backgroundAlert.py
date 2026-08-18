import yfinance as yf
from whatsapp_api_client_python import API
import time
from pathlib import Path
import configparser

# ARCHIVED — do not run. Use ../backgroundAlert1.py instead.
# Credentials were removed; configure via AlertApp/config.ini if restoring.

ID_INSTANCE = ""
API_TOKEN_INSTANCE = ""
TARGET_PHONE = ""


def _load_watchlist_from_config(cfg_path: Path | None = None) -> dict:
    candidates = []
    if cfg_path is not None:
        candidates.append(Path(cfg_path))
    candidates.extend([
        Path(__file__).resolve().parents[1] / "config.ini",  # C:\Investment\config.ini
        Path(__file__).resolve().parent / "config.ini",      # C:\Investment\AlertApp\config.ini
    ])

    seen = set()
    for cfg_file in candidates:
        if str(cfg_file) in seen:
            continue
        seen.add(str(cfg_file))
        cfg_file = cfg_file.resolve()
        if not cfg_file.is_file():
            continue
        parser = configparser.ConfigParser()
        parser.read(cfg_file)
        if not parser.has_section("watchlist"):
            continue
        out: dict = {}
        for sym, val in parser.items("watchlist"):
            parts = [p.strip() for p in val.split(",")]
            try:
                ref = float(parts[0]) if len(parts) > 0 and parts[0] else 0.0
                up = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
                down = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0
                out[sym.strip().upper()] = [ref, up, down]
            except Exception:
                continue
        if out:
            return out

    return {"AAPL": [180.00, 2.0, 2.0], "TSLA": [200.00, 5.0, 5.0]}


# Symbols: [Reference_Price, Up_%, Down_%] — loaded from config file
WATCHLIST = _load_watchlist_from_config()

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