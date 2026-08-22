from datetime import datetime, time


class ExecutionEngine:

    def __init__(
        self,
        broker,
        logger,
        risk_manager,
        strategy,
        session
    ):
        self.broker = broker
        self.logger = logger
        self.risk = risk_manager
        self.strategy = strategy
        self.session = session

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

        print(
            f"🟢 TRADE OPENED: "
            f"{signal['action']} @ {signal['entry']}"
        )

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
    # CLOSE TRADE
    # -----------------------
    def _close_trade(self, reason, exit_price):

        trade = self.broker.close_all(
            reason,
            exit_price
        )

        if not trade:
            print("❌ TRADE CLOSE FAILED")
            return None

        self.risk.update_pnl(
            trade["pnl"]
        )

        self.logger.log_trade(
            trade
        )

        self.strategy.clear_position()

        print(
            f"🔴 TRADE CLOSED : {reason}"
        )

        # The trade is finished.
        # Therefore today's session is finished.
        self.session.end(reason)

        return trade

    # -----------------------
    # EXIT HANDLER
    # -----------------------
    def on_exit_signal(self, reason, exit_price):

        if not self.broker.position:
            return

        self._close_trade(
            reason,
            exit_price
        )

    # -----------------------
    # LIVE TICK HANDLER
    # -----------------------
    def on_tick(self, ltp):

        print(
            "🧠 ENGINE RECEIVED LIVE TICK:",
            ltp
        )

        print(
            "ENGINE ON_TICK CALLED:",
            ltp
        )

        print(
            "BROKER POSITION =",
            self.broker.position
        )

        now = datetime.now().time()

        # -----------------------
        # NO TRADE EOD
        # -----------------------
        #
        # IMPORTANT:
        # This must happen BEFORE
        # checking broker.position.
        #
        # If there was no trade today,
        # the bot must still shut down
        # at 3:15 PM.
        # -----------------------

        if now >= time(15, 15):

            if not self.broker.position:

                print(
                    "🕒 3:15 PM REACHED"
                )

                print(
                    "📭 NO TRADE TODAY"
                )

                self.session.end(
                    "NO_TRADE"
                )

                return

        # -----------------------
        # NO OPEN POSITION
        # -----------------------

        if not self.broker.position:
            return

        pos = self.broker.position.copy()

        direction = pos["direction"]
        sl = pos["stoploss"]
        target = pos["target"]
        # -----------------------
        # EOD EXIT
        # -----------------------

        if now >= time(14, 59):

            print(
                "🚨 EOD CONDITION TRIGGERED"
            )

            print(
                "CURRENT TIME:",
                now
            )

            print(
                "CURRENT POSITION:",
                self.broker.position
            )

            print(
                "CURRENT LTP:",
                ltp
            )

            trade = self._close_trade(
                "EOD_EXIT",
                ltp
            )

            print(
                "CLOSE_ALL RETURN:",
                trade
            )

            return

        # -----------------------
        # IMMEDIATE TARGET EXIT
        # -----------------------

        if direction == "BUY":

            if float(ltp) >= float(target):

                print(
                    "🎯 BUY TARGET HIT"
                )

                self._close_trade(
                    "TARGET_HIT",
                    ltp
                )

                return

        else:

            if float(ltp) <= float(target):

                print(
                    "🎯 SELL TARGET HIT"
                )

                self._close_trade(
                    "TARGET_HIT",
                    ltp
                )

                return

        # -----------------------
        # STRICT STOP LOSS
        # -----------------------

        if direction == "BUY":

            if float(ltp) <= float(sl):

                print(
                    "❌ BUY STOP LOSS HIT"
                )

                self._close_trade(
                    "SL_HIT",
                    ltp
                )

                return

        else:

            if float(ltp) >= float(sl):

                print(
                    "❌ SELL STOP LOSS HIT"
                )

                self._close_trade(
                    "SL_HIT",
                    ltp
                )

                return