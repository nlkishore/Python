import yfinance as yf
import pandas as pd

symbols = ["AAPL", "MSFT", "GOOGL"]
start_date = "2023-01-01"
end_date = "2023-12-31"

data = yf.download(symbols, start=start_date, end=end_date, auto_adjust=True)

print("Columns:", data.columns)
print(data.head())

if data.empty:
    print("No data downloaded. Please check the symbols and your internet connection.")
    exit()

# If MultiIndex, select 'Close'
if isinstance(data.columns, pd.MultiIndex):
    data = data['Close']

print("Columns after processing:", data.columns)