from strategy import Strategy
from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from trade_logger import TradeLogger


# ===================================
# SETUP REAL COMPONENTS
# ===================================

strategy = Strategy()

broker = PaperBroker()

logger = TradeLogger("integration_log.csv")

execution_engine = ExecutionEngine(
    broker,
    logger
)


# ===================================
# SET OPENING LEVELS
# ===================================

strategy.set_levels(
    high_level=100,
    low_level=90
)


# ===================================
# SCENARIO 1
# BUY BREAKOUT → TARGET HIT
# ===================================

print("\n========== SCENARIO 1 ==========")
print("BUY → TARGET\n")


buy_candle = {
    "close": 101
}

signal = strategy.on_candle(buy_candle)

if signal:
    execution_engine.on_signal(signal)


# Simulate live ticks after entry
ticks = [
    101.2,
    101.4,
    101.6,
    101.8,
    102.0
]

for tick in ticks:
    print("TICK:", tick)

    execution_engine.on_tick(tick)


# ===================================
# SCENARIO 2
# BUY BREAKOUT → SL HIT
# ===================================

print("\n========== SCENARIO 2 ==========")
print("BUY → STOPLOSS\n")

strategy.reset()

broker.position = None

execution_engine.trading_done = False

strategy.set_levels(
    high_level=100,
    low_level=90
)

buy_candle = {
    "close": 101
}

signal = strategy.on_candle(buy_candle)

if signal:
    execution_engine.on_signal(signal)


ticks = [
    100.8,
    100.5,
    100.0,
    99.8,
    99.0
]

for tick in ticks:
    print("TICK:", tick)

    execution_engine.on_tick(tick)


# ===================================
# SCENARIO 3
# SELL BREAKOUT → TARGET HIT
# ===================================

print("\n========== SCENARIO 3 ==========")
print("SELL → TARGET\n")

strategy.reset()

broker.position = None

execution_engine.trading_done = False

strategy.set_levels(
    high_level=100,
    low_level=90
)

sell_candle = {
    "close": 89
}

signal = strategy.on_candle(sell_candle)

if signal:
    execution_engine.on_signal(signal)


ticks = [
    88.8,
    88.6,
    88.4,
    88.2,
    88.0
]

for tick in ticks:
    print("TICK:", tick)

    execution_engine.on_tick(tick)


# ===================================
# SCENARIO 4
# SELL BREAKOUT → SL HIT
# ===================================

print("\n========== SCENARIO 4 ==========")
print("SELL → STOPLOSS\n")

strategy.reset()

broker.position = None

execution_engine.trading_done = False

strategy.set_levels(
    high_level=100,
    low_level=90
)

sell_candle = {
    "close": 89
}

signal = strategy.on_candle(sell_candle)

if signal:
    execution_engine.on_signal(signal)


ticks = [
    89.2,
    89.4,
    89.6,
    89.8,
    90.0
]

for tick in ticks:
    print("TICK:", tick)

    execution_engine.on_tick(tick)


print("\n✅ INTEGRATION TEST COMPLETE")