#paper_brokker.py
class PaperBroker:

    def __init__(self):

        self.position = None
        self.trade_history = []

    # ==========================
    # BUY
    # ==========================
    def buy(self, symbol, price, sl, target):
        return self.open_trade(
            symbol,
            "BUY",
            price,
            target,
            sl
        )

    # ==========================
    # SELL
    # ==========================
    def sell(self, symbol, price, sl, target):
        return self.open_trade(
            symbol,
            "SELL",
            price,
            target,
            sl
        )

    # ==========================
    # OPEN TRADE
    # ==========================
    def open_trade(
        self,
        symbol,
        direction,
        entry,
        target,
        stoploss
    ):

        if self.position:
            return None

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss
        }

        print(
            f"OPEN {direction} "
            f"{symbol} @ {entry}"
        )

        return self.position

    # ==========================
    # EXIT LOGIC
    # ==========================
    def check_exit(self, current_price):

        if not self.position:
            return None

        direction = self.position["direction"]
        entry = self.position["entry"]
        target = self.position["target"]
        stoploss = self.position["stoploss"]

        # BUY POSITION
        if direction == "BUY":

            if current_price >= target:

                pnl = target - entry

                trade = {
                    **self.position,
                    "exit": target,
                    "reason": "TARGET",
                    "pnl": pnl
                }

                self.trade_history.append(trade)

                print("🎯 BUY TARGET HIT")

                self.position = None

                return trade

            if current_price <= stoploss:

                pnl = stoploss - entry

                trade = {
                    **self.position,
                    "exit": stoploss,
                    "reason": "STOPLOSS",
                    "pnl": pnl
                }

                self.trade_history.append(trade)

                print("🛑 BUY STOPLOSS HIT")

                self.position = None

                return trade

        # SELL POSITION
        else:

            if current_price <= target:

                pnl = entry - target

                trade = {
                    **self.position,
                    "exit": target,
                    "reason": "TARGET",
                    "pnl": pnl
                }

                self.trade_history.append(trade)

                print("🎯 SELL TARGET HIT")

                self.position = None

                return trade

            if current_price >= stoploss:

                pnl = entry - stoploss

                trade = {
                    **self.position,
                    "exit": stoploss,
                    "reason": "STOPLOSS",
                    "pnl": pnl
                }

                self.trade_history.append(trade)

                print("🛑 SELL STOPLOSS HIT")

                self.position = None

                return trade

        return None

    # ==========================
    # CLOSE ALL
    # ==========================
    def close_all(self, reason, exit_price):

        if self.position:

            print(f"CLOSED {reason}")

            self.position = None