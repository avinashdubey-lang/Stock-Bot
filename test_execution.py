from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from risk_manager import RiskManager
from trade_logger import TradeLogger

broker = PaperBroker()
engine = ExecutionEngine(broker, TradeLogger(), RiskManager())

# fake short trade
broker.position = {
    "symbol": "TEST",
    "direction": "SELL",
    "entry": 1869,
    "target": 1867.131,
    "stoploss": 1870
}

# simulate price drop
engine.on_tick(1867.0)

print("POSITION AFTER:", broker.position)