from ib_insync import *
import pandas as pd
from datetime import datetime, timedelta

# Replace with your IBKR Account ID (Find it in IBKR Client Portal or TWS)
IBKR_ACCOUNT_ID = "U3831357"  # Replace with your actual IBKR account ID

# Connect to IBKR TWS or IB Gateway
ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)  # Use 7496 for Live Trading

# Get the start date (last 7 days) in correct IBKR format: 'YYYYMMDD HH:MM:SS'
start_date = (datetime.utcnow() - timedelta(days=360)).strftime('%Y%m%d %H:%M:%S')

# Define execution filter with Account ID and Time filter
exec_filter = ExecutionFilter()
exec_filter.acctCode = IBKR_ACCOUNT_ID  # Set the account ID to fetch trades for this account
exec_filter.time = start_date  # Time format must be 'YYYYMMDD HH:MM:SS'

# Fetch executions based on filter
trades = ib.reqExecutions(exec_filter)

# Debugging: Check if any trades are returned
if not trades:
    print(f"❌ No trade executions found for Account {IBKR_ACCOUNT_ID} in the past 7 days.")
    ib.disconnect()
    exit()

# Extract relevant trade data
trade_data = []
for trade in trades:
    trade_data.append({
        'Account': trade.execution.acctNumber,
        'Symbol': trade.contract.symbol,
        'Action': trade.execution.side,  # BUY / SELL
        'Quantity': trade.execution.shares,
        'Price': trade.execution.price,
        'Date': trade.execution.time.strftime('%Y-%m-%d %H:%M:%S')
    })

# Convert to DataFrame
df = pd.DataFrame(trade_data)

# Save to CSV
csv_filename = f"IBKR_Trades_{IBKR_ACCOUNT_ID}.csv"
df.to_csv(csv_filename, index=False)

print(f"✅ Trade data saved as '{csv_filename}' for Account {IBKR_ACCOUNT_ID}")
ib.disconnect()
