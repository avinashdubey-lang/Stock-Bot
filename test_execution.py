from strategy import Strategy
from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from trade_logger import TradeLogger
from risk_manager import RiskManager

strategy = Strategy()
strategy.set_levels(1855, 1847)

broker = PaperBroker()
engine = ExecutionEngine(broker, TradeLogger(), RiskManager())

signal = strategy.on_candle({"close": 1865.5})

print(signal)

if signal:
    engine.on_signal(signal)

print(broker.position)

engine.on_tick(1875)
print("POSITION:", broker.position)
print("HISTORY:", broker.trade_history)