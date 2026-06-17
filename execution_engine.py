#execution_engine
from datetime import datetime, time


class ExecutionEngine:

    def __init__(self, broker, logger, risk_manager):
        self.broker = broker
        self.logger = logger
        self.risk = risk_manager
        self.trading_done = False

    # -----------------------
    # RESET
    # -----------------------
    def reset(self):
       self.trading_done = False

    # -----------------------
    # ENTRY HANDLER
    # -----------------------
    def on_signal(self, signal):

        print("ENGINE RECEIVED SIGNAL:", signal)

        # 🛡 RISK CHECK FIRST
        if not self.risk.can_take_trade():
            print("⛔ TRADE BLOCKED BY RISK MANAGER")
            return

        if self.broker.position:
            return  # only 1 trade at a time

        trade = self.broker.open_trade(
            signal["symbol"],
            signal["action"],
            signal["entry"],
            signal["target"],
            signal["sl"]
        )

        if not trade:
            print("❌ ORDER REJECTED")
            return

        self.risk.record_trade()

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

        if self.trading_done:
            return

        if not self.broker.position:
            return

        pos = self.broker.position

        now = datetime.now().time()

        # -----------------------
        # EOD EXIT (STRICT)
        # -----------------------
        # if now >= time(14, 59):

        #     trade = self.broker.close_all("EOD_EXIT", ltp)

        #     if trade:
        #         self.risk.update_pnl(trade["pnl"])
        #         self.logger.log_trade(trade)

        #     self.trading_done = True
        #     print("🔴 EOD EXIT")
        #     return

        direction = pos["direction"]
        sl = pos["stoploss"]
        target = pos["target"]

        # -----------------------
        # BUY LOGIC
        # -----------------------
        if direction == "BUY":

            if ltp <= sl:

                trade = self.broker.close_all("SL_HIT", ltp)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("❌ SL HIT (BUY)")
                return


            if ltp >= target:

                trade = self.broker.close_all("TARGET_HIT", ltp)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("🎯 TARGET HIT (BUY)")
                return

        # -----------------------
        # SELL LOGIC
        # -----------------------
        else:
            if ltp >= sl:

                trade = self.broker.close_all("SL_HIT", ltp)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("❌ SL HIT (SELL)")
                return


            if ltp <= target:

                trade = self.broker.close_all("TARGET_HIT", ltp)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("🎯 TARGET HIT (SELL)")
                return  
            
        return None