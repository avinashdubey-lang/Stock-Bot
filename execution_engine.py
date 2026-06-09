from datetime import datetime, time


class ExecutionEngine:

    def __init__(self, broker, logger):
        self.broker = broker
        self.logger = logger

    # -----------------------
    # RESET
    # -----------------------
    def reset(self):
        pass  # placeholder for future risk/session state

    # -----------------------
    # ENTRY HANDLER
    # -----------------------
    def on_signal(self, signal):

        if self.broker.position:
            return  # only 1 trade at a time

        self.broker.open_trade(
            signal["symbol"],
            signal["action"],
            signal["entry"],
            signal["target"],
            signal["sl"]
        )

        print(f"🟢 TRADE OPENED: {signal['action']} @ {signal['entry']}")

        self.logger.log_trade({
            "symbol": signal["symbol"],
            "direction": signal["action"],
            "entry": signal["entry"],
            "exit": None,
            "target": signal["target"],
            "stoploss": signal["sl"],
            "reason": "OPEN",
            "pnl": 0
        })

    # -----------------------
    # EXIT HANDLER
    # -----------------------
    def on_tick(self, ltp):

        if not self.broker.position:
            return

        pos = self.broker.position

        now = datetime.now().time()

        # -----------------------
        # EOD EXIT (STRICT)
        # -----------------------
        if now >= time(14, 59):
            trade = self.broker.close_all("EOD_EXIT", ltp)
            self.logger.log_trade(trade)
            print("🔴 EOD EXIT")
            return

        direction = pos["direction"]
        sl = pos["stoploss"]
        target = pos["target"]

        # -----------------------
        # BUY LOGIC
        # -----------------------
        if direction == "BUY":

            if ltp <= sl:
                trade = self.broker.close_all("SL_HIT", ltp)
                self.logger.log_trade(trade)
                print("❌ SL HIT (BUY)")
                return

            if ltp >= target:
                trade = self.broker.close_all("TARGET_HIT", ltp)
                self.logger.log_trade(trade)
                print("🎯 TARGET HIT (BUY)")
                return

        # -----------------------
        # SELL LOGIC
        # -----------------------
        else:

            if ltp >= sl:
                trade = self.broker.close_all("SL_HIT", ltp)
                self.logger.log_trade(trade)
                print("❌ SL HIT (SELL)")
                return

            if ltp <= target:
                trade = self.broker.close_all("TARGET_HIT", ltp)
                self.logger.log_trade(trade)
                print("🎯 TARGET HIT (SELL)")
                return
            
        return None