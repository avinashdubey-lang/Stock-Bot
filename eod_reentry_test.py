from datetime import datetime
from execution_engine import ExecutionEngine


# ==========================
# FAKE BROKER
# ==========================

class FakeBroker:

    def __init__(self):

        self.position = {
            "symbol": "TEST",
            "direction": "BUY",
            "entry": 100,
            "target": 101,
            "stoploss": 99
        }

    def open_trade(self, symbol, direction, entry, target, sl):

        print("\n🟢 OPEN TRADE CALLED")
        print(direction, entry)

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": sl
        }

        return self.position

    def close_all(self, reason, price):

        print("\n🔴 CLOSE ALL CALLED")
        print(reason)

        trade = {
            **self.position,
            "exit": price,
            "reason": reason,
            "pnl": 0
        }

        self.position = None

        return trade


# ==========================
# FAKE LOGGER
# ==========================

class FakeLogger:

    def log_trade(self, trade):
        print("LOGGER:", trade["reason"])


# ==========================
# FAKE RISK
# ==========================

class FakeRisk:

    def can_take_trade(self):
        return True

    def record_trade(self):
        print("RISK RECORDED")

    def update_pnl(self, pnl):
        pass


# ==========================
# FAKE STRATEGY
# ==========================

class FakeStrategy:

    def clear_position(self):
        print("POSITION CLEARED")

    def on_candle(self, candle):

        print("\n📊 STRATEGY GENERATED ENTRY")

        return {
            "type": "ENTRY",
            "symbol": "TEST",
            "action": "SELL",
            "entry": 100,
            "target": 99,
            "sl": 101
        }


# ==========================
# ENGINE
# ==========================

engine = ExecutionEngine(
    FakeBroker(),
    FakeLogger(),
    FakeRisk(),
    FakeStrategy()
)

# ==========================================
# SIMULATE ONE WEBSOCKET TICK AT 2:59 PM
# ==========================================

print("\n==============================")
print("SIMULATING ONE WEBSOCKET TICK")
print("==============================")

# -----------------------
# STEP 1 : ENGINE RECEIVES TICK
# -----------------------

print("\nSTEP 1 -> on_tick()")

engine.on_tick(100)

print("\ntrading_done =", engine.trading_done)
print("position =", engine.broker.position)

# -----------------------
# STEP 2 : SAME TICK CLOSES CANDLE
# -----------------------

print("\nSTEP 2 -> Strategy receives candle")

signal = engine.strategy.on_candle({
    "close": 100,
    "time": datetime.now()
})

print("\nSignal Returned:")
print(signal)

# -----------------------
# STEP 3 : ENGINE RECEIVES SIGNAL
# -----------------------

if signal:

    print("\nSTEP 3 -> on_signal()")

    engine.on_signal(signal)

print("\n==============================")
print("FINAL RESULT")
print("==============================")

print("Trading Done :", engine.trading_done)
print("Current Position :", engine.broker.position)