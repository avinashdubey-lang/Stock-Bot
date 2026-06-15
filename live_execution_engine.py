from datetime import datetime, time

class LiveExecutionEngine:

    def __init__(self, broker_api, logger, risk_manager):
        self.broker = broker_api
        self.logger = logger
        self.risk = risk_manager
        self.position = None
        self.trading_done = False

    # -----------------------
    # ENTRY
    # -----------------------
    def on_signal(self, signal):

        if self.trading_done:
            return

        if not self.risk.can_take_trade():
            print("🛑 TRADE BLOCKED BY RISK MANAGER")
            return

        order = self.broker.place_order(
            symbol=signal["symbol"],
            side=signal["action"],
            quantity=signal.get("qty", 1),
            price=signal["entry"]
        )

        self.position = signal
        self.risk.record_trade()

        print(f"🟢 LIVE TRADE OPENED: {signal['action']}")

        self.logger.log_trade({
            **signal,
            "reason": "OPEN",
            "exit": None,
            "pnl": 0
        })

    # -----------------------
    # EXIT
    # -----------------------
    def on_tick(self, ltp):

        if self.trading_done or not self.position:
            return

        sl = self.position["sl"]
        target = self.position["target"]
        direction = self.position["action"]

        exit_reason = None

        if direction == "BUY":

            if ltp <= sl:
                exit_reason = "SL_HIT"

            elif ltp >= target:
                exit_reason = "TARGET_HIT"

        else:

            if ltp >= sl:
                exit_reason = "SL_HIT"

            elif ltp <= target:
                exit_reason = "TARGET_HIT"

        if exit_reason:

            trade = self.broker.close_position()

            pnl = trade.get("pnl", 0)
            self.risk.update_pnl(pnl)

            self.logger.log_trade({
                **self.position,
                "exit": ltp,
                "reason": exit_reason,
                "pnl": pnl
            })

            print(f"🔴 LIVE EXIT: {exit_reason}")

            self.position = None
            self.trading_done = True