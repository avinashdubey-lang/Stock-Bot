from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from risk_manager import RiskManager
from trade_logger import TradeLogger


broker = PaperBroker()
logger = TradeLogger()
risk = RiskManager()

engine = ExecutionEngine(broker, logger, risk)

signal = {
    "symbol": "TEST",
    "action": "BUY",
    "entry": 100,
    "target": 110,
    "sl": 95
}

engine.on_signal(signal)

ticks = [101, 102, 105, 109, 110, 111]

for t in ticks:
    print("\nTICK:", t)
    engine.on_tick(t)