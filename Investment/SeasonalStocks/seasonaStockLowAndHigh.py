import pandas as pd
import requests
import urllib3
from collections import Counter

# Standard IBKR Gateway Setup
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BASE_URL = "https://localhost:5000/v1/api"


def check_api_session():
    try:
        response = requests.post(
            f"{BASE_URL}/iserver/auth/status", verify=False, timeout=20
        )
        if response.status_code != 200:
            return False, f"auth/status HTTP {response.status_code}"
        payload = response.json()
        if not isinstance(payload, dict):
            return False, "auth/status returned non-JSON object"
        authenticated = bool(payload.get("authenticated"))
        connected = bool(payload.get("connected"))
        if authenticated and connected:
            return True, None
        return (
            False,
            "IBKR session not connected (login required in Client Portal).",
        )
    except requests.RequestException as exc:
        return False, f"auth/status request failed: {exc}"
    except (ValueError, TypeError) as exc:
        return False, f"auth/status parse failed: {exc}"

def get_conid(symbol):
    endpoint = f"/iserver/secdef/search"
    payload = {"symbol": symbol, "name": False, "secType": "STK"}
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}", json=payload, verify=False, timeout=20
        )
        if response.status_code != 200:
            return None, f"secdef HTTP {response.status_code}"
        data = response.json()
        if not isinstance(data, list) or not data:
            return None, "secdef empty response"
        conid = data[0].get("conid")
        if not conid:
            return None, "secdef missing conid"
        return conid, None
    except requests.RequestException as exc:
        return None, f"secdef request failed: {exc}"
    except (ValueError, TypeError) as exc:
        return None, f"secdef parse failed: {exc}"

def get_historical_data(conid):
    endpoint = f"/iserver/marketdata/history"
    # Period 5y, Bar 1m to get 60 monthly data points
    params = {"conid": conid, "period": "5y", "bar": "1m"}
    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}", params=params, verify=False, timeout=30
        )
        if response.status_code != 200:
            return [], f"history HTTP {response.status_code}"
        payload = response.json()
        bars = payload.get("data", []) if isinstance(payload, dict) else []
        if not bars:
            return [], "history empty response"
        return bars, None
    except requests.RequestException as exc:
        return [], f"history request failed: {exc}"
    except (ValueError, TypeError) as exc:
        return [], f"history parse failed: {exc}"

def analyze_seasonal_consistency(csv_file):
    session_ok, session_error = check_api_session()
    if not session_ok:
        print(f"Cannot run analysis: {session_error}")
        print("Open https://localhost:5000, login, then run this script again.")
        return

    df_stocks = pd.read_csv(csv_file)
    final_report = []
    skip_reasons = Counter()

    for symbol in df_stocks['Symbol']:
        print(f"Processing {symbol}...")
        conid, conid_error = get_conid(symbol)
        if not conid:
            skip_reasons[conid_error or "unknown conid error"] += 1
            continue

        bars, history_error = get_historical_data(conid)
        if not bars:
            skip_reasons[history_error or "unknown history error"] += 1
            continue

        df = pd.DataFrame(bars)
        if "t" not in df.columns or "c" not in df.columns:
            skip_reasons["history missing required columns t/c"] += 1
            continue

        df['date'] = pd.to_datetime(df['t'], unit='ms')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month_name()

        # Group by year to find the specific month each year that was the high/low
        annual_high_months = []
        annual_low_months = []

        for year, group in df.groupby('year'):
            if len(group) < 10: continue # Skip partial years
            high_month = group.loc[group['c'].idxmax()]['month']
            low_month = group.loc[group['c'].idxmin()]['month']
            annual_high_months.append(high_month)
            annual_low_months.append(low_month)

        if not annual_high_months or not annual_low_months:
            skip_reasons["insufficient full-year monthly bars"] += 1
            continue

        # Determine the most frequent month for highs and lows
        most_common_high = Counter(annual_high_months).most_common(1)[0]
        most_common_low = Counter(annual_low_months).most_common(1)[0]

        final_report.append({
            "Symbol": symbol,
            "Common_Peak_Month": most_common_high[0],
            "Peak_Frequency": f"{most_common_high[1]}/5 years",
            "Common_Trough_Month": most_common_low[0],
            "Trough_Frequency": f"{most_common_low[1]}/5 years"
        })
        print(
            f"  -> OK ({most_common_high[0]} peak, {most_common_low[0]} trough)"
        )

    # Save Results
    report_columns = [
        "Symbol",
        "Common_Peak_Month",
        "Peak_Frequency",
        "Common_Trough_Month",
        "Trough_Frequency",
    ]
    report_df = pd.DataFrame(final_report, columns=report_columns)
    report_df.to_csv("seasonal_consistency_report.csv", index=False)

    if report_df.empty:
        print("No result rows generated.")
        print("Most common skip reasons:")
        for reason, count in skip_reasons.most_common():
            print(f" - {reason}: {count}")
        print(
            "Tip: confirm you are logged in at https://localhost:5000 and the API session is active."
        )
    else:
        print(f"Analysis complete with {len(report_df)} result row(s).")
        print("Check seasonal_consistency_report.csv")

if __name__ == "__main__":
    analyze_seasonal_consistency("SeasonalStocks/seasonal_stocks_list.csv")