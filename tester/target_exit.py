"""
=================================================================
🧪 TEST 22: IMMEDIATE TARGET EXIT ON LIVE TICK
=================================================================

22A - BUY target exit
22B - SELL target exit
22C - BUY target not reached
22D - SELL target not reached
"""

import sys
from pathlib import Path


# ================================================================
# PROJECT ROOT
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ================================================================
# PRODUCTION COMPONENTS
# ================================================================

from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from risk_manager import RiskManager
from strategy import Strategy


# ================================================================
# TEST LOGGER
# ================================================================

class TestLogger:

    def __init__(self):
        self.logs = []

    def log_trade(self, trade):

        print("📁 TRADE LOGGED")

        self.logs.append(trade)


# ================================================================
# TEST SESSION
# ================================================================

class TestSession:

    def __init__(self):

        self.ended = False
        self.reason = None

    def end(self, reason):

        print()
        print("🧪 TEST SESSION END CALLED")
        print("Reason:", reason)

        self.ended = True
        self.reason = reason

        # IMPORTANT:
        # Do NOT terminate the Python process.
        #
        # Real TradingSession.end() may shut down the application.
        # For this controlled test we only record the event.


# ================================================================
# ENGINE FACTORY
# ================================================================

def create_engine():

    broker = PaperBroker()

    logger = TestLogger()

    risk = RiskManager()

    strategy = Strategy()

    session = TestSession()

    engine = ExecutionEngine(
        broker,
        logger,
        risk,
        strategy,
        session
    )

    return (
        engine,
        broker,
        logger,
        risk,
        strategy,
        session
    )


# ================================================================
# HEADER
# ================================================================

print()
print("=" * 65)
print("🧪 TEST 22: IMMEDIATE TARGET EXIT ON LIVE TICK")
print("=" * 65)


# ================================================================
# 22A
# BUY TARGET EXIT
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 22A: BUY IMMEDIATE TARGET EXIT")
print("-" * 65)


(
    engine,
    broker,
    logger,
    risk,
    strategy,
    session
) = create_engine()


print()
print("🧪 Opening BUY position...")

trade = broker.open_trade(
    "BHARTIARTL-EQ",
    "BUY",
    101.0,
    101.707,
    100.596
)

assert trade is not None
assert broker.position is not None

print("Position:")
print(broker.position)

print(
    "🎯 BUY TARGET:",
    broker.position["target"]
)


print()
print("🧪 Sending tick BELOW target...")

engine.on_tick(101.50)

assert broker.position is not None

print(
    "Position after 101.50:",
    broker.position
)

print("✅ BUY REMAINED OPEN BELOW TARGET")


print()
print("🧪 Sending tick AT target...")

engine.on_tick(101.707)

assert broker.position is None

print(
    "Position after target tick:",
    broker.position
)

print("✅ BUY POSITION CLOSED IMMEDIATELY")


buy_trade = broker.trade_history[0]

assert buy_trade["reason"] == "TARGET_HIT"
assert buy_trade["exit"] == 101.707
assert buy_trade["pnl"] > 0

print("✅ BUY TARGET REASON PASSED")
print("✅ BUY TARGET EXIT PRICE PASSED")
print("BUY PnL:", buy_trade["pnl"])
print("✅ BUY POSITIVE PNL PASSED")

assert session.ended is True
assert session.reason == "TARGET_HIT"

print("✅ BUY SESSION END PASSED")


# ================================================================
# 22B
# SELL TARGET EXIT
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 22B: SELL IMMEDIATE TARGET EXIT")
print("-" * 65)


(
    engine,
    broker,
    logger,
    risk,
    strategy,
    session
) = create_engine()


print()
print("🧪 Opening SELL position...")

trade = broker.open_trade(
    "BHARTIARTL-EQ",
    "SELL",
    99.0,
    98.307,
    99.396
)

assert trade is not None
assert broker.position is not None

print("Position:")
print(broker.position)

print(
    "🎯 SELL TARGET:",
    broker.position["target"]
)


print()
print("🧪 Sending tick ABOVE target...")

engine.on_tick(98.50)

assert broker.position is not None

print(
    "Position after 98.50:",
    broker.position
)

print("✅ SELL REMAINED OPEN ABOVE TARGET")


print()
print("🧪 Sending tick AT target...")

engine.on_tick(98.307)

assert broker.position is None

print(
    "Position after target tick:",
    broker.position
)

print("✅ SELL POSITION CLOSED IMMEDIATELY")


sell_trade = broker.trade_history[0]

assert sell_trade["reason"] == "TARGET_HIT"
assert sell_trade["exit"] == 98.307
assert sell_trade["pnl"] > 0

print("✅ SELL TARGET REASON PASSED")
print("✅ SELL TARGET EXIT PRICE PASSED")
print("SELL PnL:", sell_trade["pnl"])
print("✅ SELL POSITIVE PNL PASSED")

assert session.ended is True
assert session.reason == "TARGET_HIT"

print("✅ SELL SESSION END PASSED")


# ================================================================
# 22C
# BUY TARGET NOT REACHED
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 22C: BUY TARGET NOT REACHED")
print("-" * 65)


(
    engine,
    broker,
    logger,
    risk,
    strategy,
    session
) = create_engine()


broker.open_trade(
    "BHARTIARTL-EQ",
    "BUY",
    101.0,
    101.707,
    100.596
)


print()
print("🧪 Sending BUY tick: 101.50")

engine.on_tick(101.50)


assert broker.position is not None
assert len(broker.trade_history) == 0
assert session.ended is False

print(
    "Position:",
    broker.position
)

print("✅ BUY TARGET NOT TRIGGERED")
print("✅ BUY TRADE REMAINED OPEN")
print("✅ BUY SESSION REMAINED ACTIVE")


# ================================================================
# 22D
# SELL TARGET NOT REACHED
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 22D: SELL TARGET NOT REACHED")
print("-" * 65)


(
    engine,
    broker,
    logger,
    risk,
    strategy,
    session
) = create_engine()


broker.open_trade(
    "BHARTIARTL-EQ",
    "SELL",
    99.0,
    98.307,
    99.396
)


print()
print("🧪 Sending SELL tick: 98.50")

engine.on_tick(98.50)


assert broker.position is not None
assert len(broker.trade_history) == 0
assert session.ended is False

print(
    "Position:",
    broker.position
)

print("✅ SELL TARGET NOT TRIGGERED")
print("✅ SELL TRADE REMAINED OPEN")
print("✅ SELL SESSION REMAINED ACTIVE")


# ================================================================
# FINAL RESULT
# ================================================================

print()
print("=" * 65)
print("🔥 TEST 22 PASSED")
print("=" * 65)

print(
    """
IMMEDIATE TARGET EXIT VERIFIED

22A
BUY target reached
        ↓
TARGET_HIT
        ↓
Position closed immediately
        ↓
No candle close required


22B
SELL target reached
        ↓
TARGET_HIT
        ↓
Position closed immediately
        ↓
No candle close required


22C
BUY target NOT reached
        ↓
Position remains open


22D
SELL target NOT reached
        ↓
Position remains open


LIVE TICK
    ↓
ExecutionEngine.on_tick()
    ↓
TARGET CHECK
    ↓
_close_trade()
    ↓
Broker.close_all()
    ↓
Risk update
    ↓
Trade logging
    ↓
Session end
"""
)

print("=" * 65)