class StockTrading:
    def __init__(self):
        self.batches = []  # List to store batches of stocks
        self.cash = 100000  # Initial cash (example amount)
        self.portfolio = {}  # Dictionary to track owned stocks

    def buy_batch(self, stock_symbol, price, quantity):
        """Buy a batch of stocks."""
        cost = price * quantity
        if self.cash >= cost:
            self.cash -= cost
            batch = {
                "symbol": stock_symbol,
                "buy_price": price,
                "quantity": quantity,
                "status": "owned"  # Track if the batch is owned or sold
            }
            self.batches.append(batch)
            print(f"Bought {quantity} shares of {stock_symbol} at ${price} per share.")
        else:
            print("Not enough cash to buy this batch.")

    def sell_batch(self, batch_index, price):
        """Sell a batch of stocks."""
        batch = self.batches[batch_index]
        if batch["status"] == "owned":
            revenue = price * batch["quantity"]
            self.cash += revenue
            batch["status"] = "sold"
            batch["sell_price"] = price
            print(f"Sold {batch['quantity']} shares of {batch['symbol']} at ${price} per share.")
        else:
            print("This batch has already been sold.")

    def check_price_movement(self, current_prices):
        """Check price movements and execute buy/sell logic."""
        for i, batch in enumerate(self.batches):
            symbol = batch["symbol"]
            current_price = current_prices.get(symbol, batch["buy_price"])  # Default to buy price if symbol not found

            if batch["status"] == "owned":
                # Check if price is up by 10%
                if current_price >= batch["buy_price"] * 1.10:
                    self.sell_batch(i, current_price)
            elif batch["status"] == "sold":
                # Check if price is down by 10% from the sell price
                if current_price <= batch["sell_price"] * 0.90:
                    self.buy_batch(symbol, current_price, batch["quantity"])

    def portfolio_summary(self):
        """Print a summary of the portfolio."""
        print("\nPortfolio Summary:")
        print(f"Available Cash: ${self.cash:.2f}")
        for batch in self.batches:
            status = batch["status"]
            symbol = batch["symbol"]
            quantity = batch["quantity"]
            buy_price = batch["buy_price"]
            if status == "owned":
                print(f"Owned: {quantity} shares of {symbol} bought at ${buy_price:.2f}")
            else:
                sell_price = batch["sell_price"]
                print(f"Sold: {quantity} shares of {symbol} sold at ${sell_price:.2f}")


# Example usage
trader = StockTrading()

# Buy initial batches
trader.buy_batch("AAPL", 150, 100)  # Buy 100 shares of AAPL at $150
trader.buy_batch("GOOGL", 2800, 10)  # Buy 10 shares of GOOGL at $2800

# Simulate price movements
price_updates = [
    {"AAPL": 165, "GOOGL": 3080},  # Prices up by 10%
    {"AAPL": 140, "GOOGL": 2772},  # Prices down by 10%
]

for prices in price_updates:
    print("\nChecking price movements...")
    trader.check_price_movement(prices)
    trader.portfolio_summary()