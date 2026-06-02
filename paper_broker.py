class PaperBroker:

    def __init__(self, capital=10000):

        self.initial_capital = capital
        self.capital = capital

        self.position = None

        self.trade_history = []

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

        if self.position is not None:
            return False

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss
        }

        print(
            f"OPENED {direction} | "
            f"{symbol} | "
            f"Entry={entry:.2f}"
        )

        return True

    # ==========================
    # CHECK EXIT
    # ==========================

    def check_exit(self, current_price):

        if self.position is None:
            return None

        direction = self.position["direction"]

        entry = self.position["entry"]

        target = self.position["target"]

        stoploss = self.position["stoploss"]

        # BUY TRADE
        if direction == "BUY":

            if current_price >= target:

                pnl = target - entry

                self.close_trade(
                    target,
                    pnl,
                    "TARGET"
                )

                return "TARGET"

            elif current_price <= stoploss:

                pnl = stoploss - entry

                self.close_trade(
                    stoploss,
                    pnl,
                    "STOPLOSS"
                )

                return "STOPLOSS"

        # SELL TRADE
        else:

            if current_price <= target:

                pnl = entry - target

                self.close_trade(
                    target,
                    pnl,
                    "TARGET"
                )

                return "TARGET"

            elif current_price >= stoploss:

                pnl = entry - stoploss

                self.close_trade(
                    stoploss,
                    pnl,
                    "STOPLOSS"
                )

                return "STOPLOSS"

        return None

    # ==========================
    # CLOSE TRADE
    # ==========================

    def close_trade(
        self,
        exit_price,
        pnl,
        reason
    ):

        trade = self.position.copy()

        trade["exit"] = exit_price

        trade["pnl"] = pnl

        trade["reason"] = reason

        self.trade_history.append(trade)

        self.capital += pnl

        print(
            f"CLOSED | "
            f"{reason} | "
            f"PnL={pnl:.2f}"
        )

        self.position = None

    # ==========================
    # SUMMARY
    # ==========================

    def summary(self):

        total_trades = len(
            self.trade_history
        )

        wins = len([
            t
            for t in self.trade_history
            if t["pnl"] > 0
        ])

        losses = total_trades - wins

        total_pnl = sum(
            t["pnl"]
            for t in self.trade_history
        )

        print("\n===== SUMMARY =====")

        print(
            f"Trades: {total_trades}"
        )

        print(
            f"Wins: {wins}"
        )

        print(
            f"Losses: {losses}"
        )

        print(
            f"PnL: {total_pnl:.2f}"
        )

        print(
            f"Capital: {self.capital:.2f}"
        )