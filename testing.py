from datetime import datetime, time

from strategy import Strategy
from execution_engine import ExecutionEngine
from websocket_feed import CandleBuilder


# ============================================================
# FAKE LOGGER
# ============================================================

class Logger:

    def log_trade(self, trade):
        print("LOGGER:", trade["reason"])


# ============================================================
# FAKE RISK
# ============================================================

class Risk:

    def can_take_trade(self):
        return True

    def record_trade(self):
        print("Risk Recorded")

    def update_pnl(self, pnl):
        pass


# ============================================================
# FAKE BROKER
# ============================================================

class Broker:

    def __init__(self):

        self.position = {
            "symbol": "TEST",
            "direction": "BUY",
            "entry": 100,
            "target": 101,
            "stoploss": 99
        }

    def open_trade(self,
                   symbol,
                   direction,
                   entry,
                   target,
                   sl):

        print("\n🟢 OPEN TRADE CALLED")

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": sl
        }

        return self.position

    def close_all(self,
                  reason,
                  exit_price):

        print("\n🔴 CLOSE ALL CALLED")

        trade = {
            **self.position,
            "exit": exit_price,
            "reason": reason,
            "pnl": 0
        }

        self.position = None

        return trade


# ============================================================
# INITIALIZE
# ============================================================

broker = Broker()

strategy = Strategy()

strategy.set_levels(
    105,
    95,
    False
)

engine = ExecutionEngine(
    broker,
    Logger(),
    Risk(),
    strategy
)

builder = CandleBuilder()


# ============================================================
# BUILD CURRENT 14:45 CANDLE
# ============================================================

builder.on_tick(
    100,
    datetime(2026,7,9,14,45,5)
)

builder.on_tick(
    106,
    datetime(2026,7,9,14,50,0)
)

builder.on_tick(
    107,
    datetime(2026,7,9,14,55,0)
)


print("\n")
print("="*80)
print("FIRST TICK")
print("="*80)

engine.test_time = time(14, 59, 0)

ltp = 103

engine.on_tick(ltp)

print("\nPosition :",broker.position)
print("Trading Done :",engine.trading_done)


print("\n")
print("="*80)
print("SECOND TICK (Immediately After)")
print("="*80)

engine.test_time = time(14, 59, 1)

ltp = 110

engine.on_tick(ltp)

print("\nPosition :",broker.position)
print("Trading Done :",engine.trading_done)


print("\n")
print("="*80)
print("CANDLE BUILDER")
print("="*80)

candle = builder.on_tick(
    110,
    datetime(2026,7,9,15,0,1)
)

print(candle)

if candle:

    signal = strategy.on_candle(candle)

    print("\nSignal Generated:")
    print(signal)

    if signal:

        engine.on_signal(signal)


print("\n")
print("="*80)
print("FINAL STATE")
print("="*80)

print("Trading Done :",engine.trading_done)

print("Broker Position :",broker.position)

