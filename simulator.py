import time
from strategy import Strategy
from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from trade_logger import TradeLogger

# 1. create dependencies
broker = PaperBroker()
logger = TradeLogger()

# 2. create execution engine
execution_engine = ExecutionEngine(broker, logger)


# fake price movement
prices = [
    1800, 1801, 1802, 1803, 1804,  # breakout
    1803, 1802, 1801, 1790,        # SL hit zone
]

for p in prices:
    print("TICK:", p)

    candle = {"close": p}  # simple fake candle for testing

    # 1. generate signal
    strategy = Strategy()
    signal = strategy.on_candle(candle)

    # 2. execute entry
    if signal:
        execution_engine.on_signal(signal)

    # 3. manage open position
    execution_engine.on_tick(p)

    time.sleep(0.5)