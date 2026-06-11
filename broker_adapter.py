class BrokerAdapter:

    def __init__(self, api_client):
        self.api = api_client
        self.position = None

    # ======================
    # PLACE ORDER (ENTRY)
    # ======================
    def open_trade(self, symbol, direction, entry, target, stoploss):

        order_type = "BUY" if direction == "BUY" else "SELL"

        response = self.api.place_order(
            symbol=symbol,
            transaction_type=order_type,
            quantity=1,  # we will improve later
            price=entry,
            order_type="MARKET"
        )

        if response is None:
            print("❌ ORDER FAILED")
            return None

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss,
            "order_id": response.get("order_id")
        }

        print(f"🟢 LIVE ORDER PLACED: {direction} {symbol} @ {entry}")

        return self.position

    # ======================
    # CLOSE ORDER (EXIT)
    # ======================
    def close_all(self, reason, exit_price):

        if not self.position:
            return None

        symbol = self.position["symbol"]
        direction = self.position["direction"]

        close_type = "SELL" if direction == "BUY" else "BUY"

        response = self.api.place_order(
            symbol=symbol,
            transaction_type=close_type,
            quantity=1,
            price=exit_price,
            order_type="MARKET"
        )

        pnl = (
            exit_price - self.position["entry"]
            if direction == "BUY"
            else self.position["entry"] - exit_price
        )

        trade = {
            **self.position,
            "exit": exit_price,
            "reason": reason,
            "pnl": pnl,
            "exit_order_id": response.get("order_id") if response else None
        }

        self.position = None

        print(f"🔴 LIVE CLOSED: {reason} @ {exit_price}")

        return trade