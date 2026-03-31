import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# Define your portfolio symbols
symbols = ["AAPL", "MSFT", "GOOGL"]
start_date = "2023-01-01"
end_date = "2023-12-31"

# Download daily adjusted close prices for all symbols
#data = yf.download(symbols, start=start_date, end=end_date)['Adj Close']
data = yf.download(symbols, start=start_date, end=end_date, auto_adjust=True)


# Drop rows with missing values
data = data.dropna()

# Calculate daily returns
returns = data.pct_change().dropna()

# Example: Predict AAPL's next-day return using other stocks' returns
returns['AAPL_next'] = returns['AAPL'].shift(-1)
returns = returns.dropna()

# Features: today's returns of all stocks except AAPL_next
X = returns[['AAPL', 'MSFT', 'GOOGL']]
y = returns['AAPL_next']

# Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Train a linear regression model
model = LinearRegression()
model.fit(X_train, y_train)

# Predict and evaluate
predictions = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, predictions))

print("Test RMSE for predicting AAPL next-day return:", rmse)

# Show a few predictions vs actual
results = pd.DataFrame({'Actual': y_test, 'Predicted': predictions}, index=y_test.index)
print(results.head())