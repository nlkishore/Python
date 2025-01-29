import pandas as pd
import yfinance as yf

class StockTrading:
    def __init__(self):
        self.batches = []  # Stores tuples of (ticker, buy_price, quantity)
        self.cash = 0  # Track profit/loss in cash
    
    def buy(self, ticker, price, quantity):
        self.batches.append((ticker, price, quantity))
        print(f"Bought {quantity} shares of {ticker} at {price}")
    
    def sell(self, current_prices):
        new_batches = []
        for ticker, buy_price, quantity in self.batches:
            target_price = buy_price * 1.1  # 10% increase
            if ticker in current_prices and current_prices[ticker] >= target_price:
                self.cash += quantity * (current_prices[ticker] - buy_price)
                print(f"Sold {quantity} shares of {ticker} bought at {buy_price} for {current_prices[ticker]}")
            else:
                new_batches.append((ticker, buy_price, quantity))
        self.batches = new_batches
    
    def buy_back(self, current_prices):
        if self.cash > 0:
            for ticker, buy_price, quantity in self.batches:
                target_price = buy_price * 0.9  # 10% decrease
                if ticker in current_prices and current_prices[ticker] <= target_price:
                    cost = quantity * current_prices[ticker]
                    if self.cash >= cost:
                        self.cash -= cost
                        self.batches.append((ticker, current_prices[ticker], quantity))
                        print(f"Bought back {quantity} shares of {ticker} at {current_prices[ticker]}")
    
    def status(self):
        print(f"Current Holdings: {self.batches}")
        print(f"Cash Balance: {self.cash}")

    def load_from_excel(self, file_path):
        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            self.buy(row['Ticker'], row['Buy_Price'], row['Quantity'])
    
    def get_current_prices(self, tickers):
        prices = {}
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            prices[ticker] = stock.history(period='1d')['Close'].iloc[-1]
        return prices


# Example Usage
trader = StockTrading()
trader.load_from_excel('/Users/yaswitha/k8s/python/Python/Python/Investment-Automation/stock_data.xlsx')  # Load buy transactions from an Excel file

tickers = [batch[0] for batch in trader.batches]
current_prices = trader.get_current_prices(tickers)  # Fetch real-time prices for stocks

trader.sell(current_prices)
trader.buy_back(current_prices)
trader.status()