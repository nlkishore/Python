import yfinance as yf
import pandas as pd

symbol = "AAPL"
start_date = "2023-01-01"
end_date = "2023-12-31"

try:
    # Download daily data for the specified year
    data = yf.download(symbol, start=start_date, end=end_date, interval='1d')
    if data.empty:
        print("No data downloaded. Check the symbol or try again later.")
    else:
        print("Daily data for", symbol)
        print(data)
except Exception as e:
    print("Error downloading data:", e)