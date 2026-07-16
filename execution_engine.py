#execution_engine
from datetime import datetime, time


class ExecutionEngine:

    def __init__(self, broker, logger, risk_manager, strategy):
        self.broker = broker
        self.logger = logger
        self.risk = risk_manager
        self.strategy = strategy
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

        # ==========================
        # TRADING DAY FINISHED
        # ==========================
        if self.trading_done:
            print("🚫 Trading already finished. Ignoring entry signal.")
            return

        # 🛡 RISK CHECK FIRST
        if not self.risk.can_take_trade():
            print("⛔ TRADE BLOCKED BY RISK MANAGER")
            return

        if isinstance(self.broker.position, dict):
            return

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
    # EXIT HANDLER (CANDLE CLOSE)
    # -----------------------
    def on_exit_signal(self, reason, exit_price):

        if not self.broker.position:
            return
        

        trade = self.broker.close_all(reason, exit_price)

        if trade:
            self.risk.update_pnl(trade["pnl"])
            self.logger.log_trade(trade)
            self.strategy.clear_position()

        self.trading_done = True

        print(f"🔴 TRADE CLOSED : {reason}")

    # -----------------------
    # EXIT HANDLER
    # -----------------------
    def on_tick(self, ltp):

        print("🧠 ENGINE RECEIVED LIVE TICK:", ltp)

        print("ENGINE ON_TICK CALLED:", ltp)
        print("TRADING_DONE =", self.trading_done)
        print("BROKER POSITION =", self.broker.position)

        if self.trading_done:
            return

        if not self.broker.position:
            return
        
        pos = self.broker.position.copy()

        direction = pos["direction"]
        sl = pos["stoploss"]

        
        now = datetime.now().time()

        # -----------------------
        # EOD EXIT (STRICT)
        # -----------------------
        if now >= time(14, 59):

            print("🚨 EOD CONDITION TRIGGERED")
            print("CURRENT TIME:", now)
            print("CURRENT POSITION:", self.broker.position)
            print("CURRENT LTP:", ltp)

            trade = self.broker.close_all("EOD_EXIT", ltp)

            print("CLOSE_ALL RETURN:", trade)

            if trade:
                self.risk.update_pnl(trade["pnl"])
                self.logger.log_trade(trade)
                self.strategy.clear_position()

            self.trading_done = True
            print("🔴 EOD EXIT")
            return
        

        # -----------------------
        # STRICT STOP LOSS
        # -----------------------

        if direction == "BUY":

            if float(ltp) <= float(sl):

                print("❌ BUY STOP LOSS HIT")

                trade = self.broker.close_all("SL_HIT", ltp)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)
                    self.strategy.clear_position()

                self.trading_done = True
                return

        else:

            if float(ltp) >= float(sl):

                print("❌ SELL STOP LOSS HIT")

                trade = self.broker.close_all("SL_HIT", ltp)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)
                    self.strategy.clear_position()

                self.trading_done = True
                return

        return 