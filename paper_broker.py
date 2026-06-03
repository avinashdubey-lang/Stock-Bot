from datetime import datetime


class PaperBroker:

    def __init__(self, capital=10000):
        self.initial_capital = capital
        self.capital = capital
        self.position = None
        self.trade_history = []

    # ==========================
    # OPEN TRADE
    # ==========================
    def open_trade(self, symbol, direction, entry, target, stoploss):

        if self.position is not None:
            return False

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss,
            "entry_candle_time": None
        }

        print(f"OPENED {direction} | {symbol} | Entry={entry:.2f}")

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

        if direction == "BUY":

            if current_price >= target:
                pnl = target - entry
                self.close_trade(target, pnl, "TARGET")
                return "TARGET"

            elif current_price <= stoploss:
                pnl = stoploss - entry
                self.close_trade(stoploss, pnl, "STOPLOSS")
                return "STOPLOSS"

        else:

            if current_price <= target:
                pnl = entry - target
                self.close_trade(target, pnl, "TARGET")
                return "TARGET"

            elif current_price >= stoploss:
                pnl = entry - stoploss
                self.close_trade(stoploss, pnl, "STOPLOSS")
                return "STOPLOSS"

        return None

    # ==========================
    # CLOSE TRADE (FIXED WITH EXIT TRACE)
    # ==========================
    def close_trade(self, exit_price, pnl, reason):

        trade = self.position.copy()
        trade["exit"] = exit_price
        trade["pnl"] = pnl
        trade["reason"] = reason
        trade["exit_time"] = datetime.now()

        self.trade_history.append(trade)
        self.capital += pnl

        # 🔥 IMPORTANT: CLEAR EXIT TRACE
        print(
            f"EXIT TRADE | {trade['symbol']} | "
            f"Exit={exit_price:.2f} | "
            f"Reason={reason} | "
            f"PnL={pnl:.2f}"
        )

        self.position = None
