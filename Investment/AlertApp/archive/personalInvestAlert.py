import yfinance as yf
import time
from pathlib import Path
import configparser

try:
    import pywhatkit as kit
except ImportError:  # pragma: no cover - optional runtime dependency
    kit = None

# --- Configuration ---
# Format: { "Symbol": [Reference_Price, Up_%, Down_%] }


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

    return {"AAPL": [180.00, 5.0, 3.0], "TSLA": [200.00, 10.0, 5.0]}


WATCHLIST = _load_watchlist_from_config()
WHATSAPP_NUMBER = "+1234567890"  # Include country code


def check_prices():
    for symbol, config in WATCHLIST.items():
        ref_price, up_threshold, down_threshold = config

        # Get current price
        ticker = yf.Ticker(symbol)
        current_price = ticker.history(period="1d")['Close'].iloc[-1]

        # Calculate change
        pct_change = ((current_price - ref_price) / ref_price) * 100

        print(f"{symbol}: ${current_price:.2f} ({pct_change:+.2f}%)")

        # Check thresholds
        if pct_change >= up_threshold:
            msg = f"🚀 ALERT: {symbol} is UP {pct_change:.2f}% (Price: ${current_price:.2f})"
            send_alert(msg)
        elif pct_change <= -down_threshold:
            msg = f"⚠️ ALERT: {symbol} is DOWN {pct_change:.2f}% (Price: ${current_price:.2f})"
            send_alert(msg)


def send_alert(message):
    print(f"Sending WhatsApp: {message}")
    if kit is not None:
        # sendwhatmsg_instantly opens browser, types message, and sends it
        # wait_time=15 gives the page 15 seconds to load before hitting enter
        kit.sendwhatmsg_instantly(WHATSAPP_NUMBER, message, wait_time=15, tab_close=True)
    else:
        print("pywhatkit is not installed. Install it with: pip install pywhatkit")


def main():
    while True:
        try:
            check_prices()
        except Exception as exc:  # pragma: no cover - runtime safety
            print(f"Error: {exc}")
        time.sleep(900)


if __name__ == "__main__":
    if kit is None:
        print("pywhatkit is missing. Run: pip install pywhatkit")
        raise SystemExit(1)
    main()