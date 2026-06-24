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
    # EXIT HANDLER
    # -----------------------
    def on_tick(self, ltp):

        print("🧠 ENGINE RECEIVED LIVE TICK:", ltp)

        print("ENGINE ON_TICK CALLED:", ltp)
        print("TRADING_DONE =", self.trading_done)
        print("BROKER POSITION =", self.broker.position)

        if self.trading_done:
            return

        pos = self.broker.position
        if not pos:
            return
        pos = pos.copy()

        
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

            self.trading_done = True
            print("🔴 EOD EXIT")
            return

        direction = pos["direction"]
        sl = pos["stoploss"]
        target = pos["target"]

        print(
            f"DEBUG | POS={direction} "
            f"LTP={ltp} "
            f"SL={sl} "
            f"TARGET={target}"
        )

        # -----------------------
        # BUY LOGIC
        # -----------------------
        if direction == "BUY":

            if float(ltp) <= float(sl):

                print("🔥 ENTERED BUY SL BLOCK")
                print(f"LTP={ltp} SL={sl}")

                print("SL BLOCK START")

                trade = self.broker.close_all("SL_HIT", ltp)

                print("SL BLOCK END")
                print("TRADE =", trade)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("❌ SL HIT (BUY)")
                return


            if float(ltp) >= float(target):

                print("🎯 ENTERED BUY TARGET BLOCK")
                print(f"LTP={ltp} TARGET={target}")

                print("TARGET BLOCK START")

                trade = self.broker.close_all("TARGET_HIT", ltp)

                print("TARGET BLOCK END")
                print("TRADE =", trade)


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
            if float(ltp) >= float(sl):

                print("🔥 ENTERED SELL SL BLOCK")
                print(f"LTP={ltp} SL={sl}")

                print("SELL SL BLOCK START")

                trade = self.broker.close_all("SL_HIT", ltp)

                print("SELL SL BLOCK END")
                print("TRADE =", trade)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("❌ SL HIT (SELL)")
                return


            if float(ltp) <= float(target):

                print("🎯 ENTERED SELL TARGET BLOCK")
                print(f"LTP={ltp} TARGET={target}")

                print("SELL TARGET BLOCK START")

                trade = self.broker.close_all("TARGET_HIT", ltp)

                print("SELL TARGET BLOCK END")
                print("TRADE =", trade)

                if trade:
                    self.risk.update_pnl(trade["pnl"])
                    self.logger.log_trade(trade)

                self.trading_done = True
                print("🎯 TARGET HIT (SELL)")
                return  
            
        return None