from datetime import datetime

from strategy import Strategy
from execution_engine import ExecutionEngine
from websocket_feed import CandleBuilder


# =====================================================
# FAKE LOGGER
# =====================================================

class FakeLogger:

    def log_trade(self, trade):
        print("LOGGER:", trade["reason"])


# =====================================================
# FAKE RISK
# =====================================================

class FakeRisk:

    def can_take_trade(self):
        print("RISK CHECK")
        return True

    def record_trade(self):
        print("TRADE RECORDED")

    def update_pnl(self, pnl):
        pass


# =====================================================
# FAKE BROKER
# =====================================================

class FakeBroker:

    def __init__(self):

        self.position = {
            "symbol": "TEST",
            "direction": "BUY",
            "entry": 100,
            "target": 100.7,
            "stoploss": 99.6
        }

    def open_trade(self, symbol, direction, entry, target, sl):

        print("\n🟢 OPEN TRADE")

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": sl
        }

        return self.position

    def close_all(self, reason, exit_price):

        print("\n🔴 CLOSE ALL")

        trade = {
            **self.position,
            "exit": exit_price,
            "reason": reason,
            "pnl": 0
        }

        self.position = None

        return trade


# =====================================================
# INITIALIZE
# =====================================================

broker = FakeBroker()

strategy = Strategy()

strategy.set_levels(
    high_level=105,
    low_level=95,
    same_colour=False       # reverse strategy
)

engine = ExecutionEngine(
    broker,
    FakeLogger(),
    FakeRisk(),
    strategy
)

builder = CandleBuilder()


# =====================================================
# SIMULATOR
# =====================================================

def simulate_tick(price, ts):

    print("\n")
    print("=" * 70)
    print("TICK :", price)
    print("TIME :", ts)
    print("=" * 70)

    print("\nSTEP 1 : ENGINE")

    engine.on_tick(price)

    print("\nBroker Position :", broker.position)
    print("Trading Done    :", engine.trading_done)

    print("\nSTEP 2 : CANDLE BUILDER")

    candle = builder.on_tick(price, ts)

    print("Returned Candle :", candle)

    if candle is None:
        print("No candle closed.")
        return

    print("\nSTEP 3 : STRATEGY")

    signal = strategy.on_candle(candle)

    print("Signal :", signal)

    if signal:

        print("\nSTEP 4 : ENGINE SIGNAL")

        engine.on_signal(signal)

    print("\nFINAL POSITION :", broker.position)

    print("=" * 70)


# =====================================================
# PRELOAD CURRENT CANDLE
# (simulate ticks from 14:45 bucket)
# =====================================================

builder.on_tick(
    100,
    datetime(2026, 7, 9, 14, 45, 5)
)

builder.on_tick(
    101,
    datetime(2026, 7, 9, 14, 50, 0)
)

builder.on_tick(
    102,
    datetime(2026, 7, 9, 14, 55, 0)
)


# =====================================================
# TEST 1
# 14:59
# Should NOT close candle
# =====================================================

print("\n\n############### TEST 1 ################")

simulate_tick(
    103,
    datetime(2026, 7, 9, 14, 59, 30)
)


# =====================================================
# RESET POSITION
# =====================================================

broker.position = {
    "symbol": "TEST",
    "direction": "BUY",
    "entry": 100,
    "target": 100.7,
    "stoploss": 99.6
}

engine.trading_done = False


# =====================================================
# TEST 2
# First 15:00 tick
# Should close 14:45 candle
# =====================================================

print("\n\n############### TEST 2 ################")

simulate_tick(
    110,
    datetime(2026, 7, 9, 15, 0, 1)
)


# =====================================================
# RESET POSITION
# =====================================================

broker.position = {
    "symbol": "TEST",
    "direction": "BUY",
    "entry": 100,
    "target": 100.7,
    "stoploss": 99.6
}

engine.trading_done = False


# =====================================================
# RESET STRATEGY
# =====================================================

strategy.reset()

strategy.set_levels(
    high_level=105,
    low_level=95,
    same_colour=False
)


# =====================================================
# TEST 3
# Breakout after EOD
# =====================================================

print("\n\n############### TEST 3 ################")

builder.current_bucket = datetime(
    2026,
    7,
    9,
    14,
    45
)

builder.current_candle = {
    "time": builder.current_bucket,
    "open": 100,
    "high": 106,
    "low": 99,
    "close": 106
}

simulate_tick(
    110,
    datetime(2026, 7, 9, 15, 0, 1)
)


# =====================================================
# RESET
# =====================================================

broker.position = {
    "symbol": "TEST",
    "direction": "BUY",
    "entry": 100,
    "target": 100.7,
    "stoploss": 99.6
}

engine.trading_done = False

strategy.reset()

strategy.set_levels(
    high_level=105,
    low_level=95,
    same_colour=False
)


# =====================================================
# TEST 4
# 15:00 without breakout
# =====================================================

print("\n\n############### TEST 4 ################")

builder.current_bucket = datetime(
    2026,
    7,
    9,
    14,
    45
)

builder.current_candle = {
    "time": builder.current_bucket,
    "open": 100,
    "high": 104,
    "low": 96,
    "close": 100
}

simulate_tick(
    101,
    datetime(2026, 7, 9, 15, 0, 1)
)