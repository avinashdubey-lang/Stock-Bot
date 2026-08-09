from datetime import datetime
import os

import live_feed

from live_feed import LiveFeed
from strategy import Strategy
from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from risk_manager import RiskManager
from trade_logger import TradeLogger
from trading_session import TradingSession


# ============================================================
# FAKE WEBSOCKET
# ============================================================

class FakeWebSocket:

    def __init__(
        self,
        auth_token,
        api_key,
        client_code,
        feed_token
    ):

        print("🧪 FAKE WEBSOCKET: CREATED")

        self.auth_token = auth_token
        self.api_key = api_key
        self.client_code = client_code
        self.feed_token = feed_token

        self.on_open = None
        self.on_data = None
        self.on_error = None
        self.on_close = None
        self.on_message = None

        self.closed = False

    def close_connection(self):

        print("🧪 FAKE WEBSOCKET: close_connection() CALLED")

        self.closed = True


# ============================================================
# REPLACE REAL ANGEL WEBSOCKET WITH FAKE WEBSOCKET
# ============================================================

live_feed.SmartWebSocketV2 = FakeWebSocket


# ============================================================
# FAKE INSTRUMENT LOOKUP
# ============================================================

class FakeLookup:

    def get_token(self, symbol):

        return "12345"


# ============================================================
# MAIN TICK CALLBACK
# ============================================================

received_ticks = []


def on_tick(price):

    print("🧪 MAIN TICK CALLBACK:", price)

    received_ticks.append(price)


# ============================================================
# ANGEL-STYLE TICK CREATOR
# ============================================================

def make_tick(price, timestamp):

    return {
        "last_traded_price": int(
            round(price * 100)
        ),

        "exchange_timestamp": int(
            timestamp.timestamp() * 1000
        ),

        "volume_trade_for_the_day": 50000
    }


# ============================================================
# TEST HEADER
# ============================================================

print("\n")
print("=" * 65)
print("🧪 TEST 15: FULL PAPER TRADING PIPELINE")
print("=" * 65)


# ============================================================
# CREATE REAL COMPONENTS
# ============================================================

print("\n🧪 Creating REAL trading components...")

broker = PaperBroker()

risk = RiskManager()

strategy = Strategy()


# ============================================================
# TEST-ONLY TRADE LOG
# ============================================================

test_log_file = "test_trade_log.csv"

if os.path.exists(test_log_file):

    os.remove(test_log_file)


logger = TradeLogger(
    filename=test_log_file
)

session = TradingSession()


# ============================================================
# CREATE REAL EXECUTION ENGINE
# ============================================================

engine = ExecutionEngine(
    broker,
    logger,
    risk,
    strategy,
    session
)


# ============================================================
# CREATE REAL LIVE FEED
# ============================================================

feed = LiveFeed(
    client_code="TEST_CLIENT",
    api_key="TEST_API_KEY",
    auth_token="TEST_AUTH_TOKEN",
    feed_token="TEST_FEED_TOKEN",
    on_tick=on_tick,
    lookup=FakeLookup(),
    strategy=strategy,
    engine=engine
)


# ============================================================
# ATTACH FEED TO SESSION
# ============================================================

session.attach_feed(feed)


# ============================================================
# SET STRATEGY LEVELS
# ============================================================

print("\n🧪 Setting opening range...")

strategy.set_levels(
    high_level=100.0,
    low_level=95.0,
    same_colour=True
)


# ============================================================
# SIMULATED TRADING DAY
# ============================================================

print("\n🧪 Simulated trading day: 2026-08-10")


# ============================================================
# TICK 1
#
# 10:00
#
# Starts the 10:00 candle.
#
# O = 99
# H = 99
# L = 99
# C = 99
# ============================================================

print("\n" + "-" * 65)
print("🧪 TICK 1")
print("Time  : 10:00:00")
print("Price : 99.00")
print("-" * 65)


feed.on_data(
    feed.ws,
    make_tick(
        99.00,
        datetime(2026, 8, 10, 10, 0, 0)
    )
)


# ============================================================
# TICK 2
#
# 10:05
#
# Same candle.
#
# Price = 101
# ============================================================

print("\n" + "-" * 65)
print("🧪 TICK 2")
print("Time  : 10:05:00")
print("Price : 101.00")
print("-" * 65)


feed.on_data(
    feed.ws,
    make_tick(
        101.00,
        datetime(2026, 8, 10, 10, 5, 0)
    )
)


# ============================================================
# TICK 3
#
# 10:14
#
# Same candle.
#
# Price = 101
# ============================================================

print("\n" + "-" * 65)
print("🧪 TICK 3")
print("Time  : 10:14:00")
print("Price : 101.00")
print("-" * 65)


feed.on_data(
    feed.ws,
    make_tick(
        101.00,
        datetime(2026, 8, 10, 10, 14, 0)
    )
)


# ============================================================
# TICK 4
#
# 10:15
#
# NEW BUCKET.
#
# This closes the 10:00 candle:
#
# O = 99
# H = 101
# L = 99
# C = 101
#
# 101 > opening high 100
#
# Therefore:
#
# Strategy → BUY ENTRY
# Engine   → PaperBroker.open_trade()
# ============================================================

print("\n" + "-" * 65)
print("🧪 TICK 4")
print("Time  : 10:15:00")
print("Price : 101.00")
print("-" * 65)


feed.on_data(
    feed.ws,
    make_tick(
        101.00,
        datetime(2026, 8, 10, 10, 15, 0)
    )
)


# ============================================================
# VERIFY ENTRY
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING PAPER ENTRY")
print("=" * 65)

print("\nPaper position:")
print(broker.position)


entry_passed = (
    broker.position is not None
    and broker.position["symbol"] == "BHARTIARTL-EQ"
    and broker.position["direction"] == "BUY"
    and broker.position["entry"] == 101.00
)


if entry_passed:

    print("✅ PAPER ENTRY PASSED")

else:

    print("❌ PAPER ENTRY FAILED")


# ============================================================
# READ REAL TARGET
# ============================================================

if broker.position:

    target = broker.position["target"]

else:

    target = None


print("\nReal Strategy Target:", target)


# ============================================================
# TARGET TEST PRICE
#
# Strategy target is:
#
# 101.707
#
# Angel-style feed uses 2 decimal precision in this test.
#
# Therefore:
#
# 101.71 >= 101.707
#
# ============================================================

target_test_price = 101.71


print(
    "Target test price    :",
    target_test_price
)


# ============================================================
# TICK 5
#
# 10:16
#
# IMPORTANT:
#
# This is INSIDE the 10:15 candle.
#
# Price reaches 101.71.
#
# The Strategy does NOT receive a candle yet.
#
# This proves that the target remains pending until
# the candle closes in the current architecture.
# ============================================================

print("\n" + "-" * 65)
print("🧪 TICK 5 — TARGET REACHED INSIDE CANDLE")
print("Time  : 10:16:00")
print("Price : 101.71")
print("-" * 65)


feed.on_data(
    feed.ws,
    make_tick(
        target_test_price,
        datetime(2026, 8, 10, 10, 16, 0)
    )
)


# ============================================================
# VERIFY POSITION STILL OPEN
# ============================================================

print("\n🧪 Verifying position remains open before candle close...")

print("Position:", broker.position)


position_still_open = (
    broker.position is not None
)


if position_still_open:

    print("✅ POSITION STILL OPEN")

else:

    print("❌ POSITION CLOSED TOO EARLY")


# ============================================================
# TICK 6
#
# 10:30
#
# NEW BUCKET.
#
# This closes the 10:15 candle.
#
# 10:15 candle:
#
# O = 101
# H = 101.71
# L = 101
# C = 101.71
#
# Strategy:
#
# close >= target
#        ↓
# TARGET_HIT
#
# Then:
#
# Strategy
#     ↓
# ExecutionEngine
#     ↓
# PaperBroker.close_all()
#     ↓
# RiskManager.update_pnl()
#     ↓
# TradeLogger.log_trade()
#     ↓
# Strategy.clear_position()
#     ↓
# TradingSession.end()
#     ↓
# LiveFeed.stop()
# ============================================================

print("\n" + "-" * 65)
print("🧪 TICK 6 — CANDLE CLOSE / TARGET EXIT")
print("Time  : 10:30:00")
print("Price : 101.71")
print("-" * 65)


session_shutdown_triggered = False


try:

    feed.on_data(
        feed.ws,
        make_tick(
            target_test_price,
            datetime(2026, 8, 10, 10, 30, 0)
        )
    )

except SystemExit as e:

    session_shutdown_triggered = True

    print("\n🧪 TEST CAUGHT SYSTEM EXIT")
    print("Exit code:", e.code)


# ============================================================
# VERIFY PAPER EXIT
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING PAPER EXIT")
print("=" * 65)

print("\nPaper position:")
print(broker.position)

print("\nTrade history:")
print(broker.trade_history)


exit_passed = (
    broker.position is None
    and len(broker.trade_history) == 1
)


if exit_passed:

    trade = broker.trade_history[0]

    print("\n✅ PAPER EXIT PASSED")

    print("Entry :", trade["entry"])
    print("Exit  :", trade["exit"])
    print("Reason:", trade["reason"])
    print("PnL   :", trade["pnl"])

else:

    print("\n❌ PAPER EXIT FAILED")


# ============================================================
# VERIFY RISK MANAGER
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING RISK MANAGER")
print("=" * 65)

print("Trades taken:", risk.trades_taken)
print("Daily PnL   :", risk.daily_pnl)


risk_passed = (
    risk.trades_taken == 1
    and risk.daily_pnl > 0
)


if risk_passed:

    print("✅ RISK MANAGER PASSED")

else:

    print("❌ RISK MANAGER FAILED")


# ============================================================
# VERIFY STRATEGY POSITION
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING STRATEGY POSITION")
print("=" * 65)

print("Strategy position:", strategy.position)


strategy_passed = (
    strategy.position is None
)


if strategy_passed:

    print("✅ STRATEGY POSITION CLEARED")

else:

    print("❌ STRATEGY POSITION NOT CLEARED")


# ============================================================
# VERIFY SESSION
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING TRADING SESSION")
print("=" * 65)

print("Session ended :", session.ended)
print("End reason    :", session.end_reason)


session_passed = (
    session.ended
    and session.end_reason == "TARGET_HIT"
)


if session_passed:

    print("✅ TRADING SESSION PASSED")

else:

    print("❌ TRADING SESSION FAILED")


# ============================================================
# VERIFY FEED SHUTDOWN
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING LIVE FEED SHUTDOWN")
print("=" * 65)

print("WebSocket closed:", feed.ws.closed)


feed_passed = (
    feed.ws.closed
)


if feed_passed:

    print("✅ LIVE FEED SHUTDOWN PASSED")

else:

    print("❌ LIVE FEED SHUTDOWN FAILED")


# ============================================================
# VERIFY LOGGER
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING TRADE LOGGER")
print("=" * 65)

print("Log file exists:", os.path.exists(test_log_file))


logger_passed = (
    os.path.exists(test_log_file)
    and os.path.getsize(test_log_file) > 0
)


if logger_passed:

    print("✅ TRADE LOGGER PASSED")

else:

    print("❌ TRADE LOGGER FAILED")


# ============================================================
# VERIFY MAIN TICK CALLBACK
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING TICK CALLBACK")
print("=" * 65)

print("Ticks received:")
print(received_ticks)


tick_passed = (
    len(received_ticks) == 6
    and received_ticks[0] == 99.00
    and received_ticks[1] == 101.00
    and received_ticks[2] == 101.00
    and received_ticks[3] == 101.00
    and received_ticks[4] == 101.71
    and received_ticks[5] == 101.71
)


if tick_passed:

    print("✅ TICK PIPELINE PASSED")

else:

    print("❌ TICK PIPELINE FAILED")


# ============================================================
# VERIFY COMPLETE TRADE
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING COMPLETE TRADE")
print("=" * 65)


if len(broker.trade_history) == 1:

    trade = broker.trade_history[0]

    complete_trade_passed = (
        trade["symbol"] == "BHARTIARTL-EQ"
        and trade["direction"] == "BUY"
        and trade["entry"] == 101.00
        and trade["exit"] == target_test_price
        and trade["reason"] == "TARGET_HIT"
        and trade["pnl"] > 0
    )

else:

    complete_trade_passed = False


if complete_trade_passed:

    print("✅ COMPLETE TRADE PASSED")

else:

    print("❌ COMPLETE TRADE FAILED")


# ============================================================
# VERIFY SESSION SHUTDOWN
# ============================================================

print("\n" + "=" * 65)
print("🧪 VERIFYING COMPLETE SHUTDOWN")
print("=" * 65)

print(
    "SystemExit triggered:",
    session_shutdown_triggered
)


shutdown_passed = (
    session_shutdown_triggered
)


if shutdown_passed:

    print("✅ SESSION SHUTDOWN PASSED")

else:

    print("❌ SESSION SHUTDOWN FAILED")


# ============================================================
# FINAL RESULT
# ============================================================

all_passed = (
    entry_passed
    and position_still_open
    and exit_passed
    and risk_passed
    and strategy_passed
    and session_passed
    and feed_passed
    and logger_passed
    and tick_passed
    and complete_trade_passed
    and shutdown_passed
)


if all_passed:

    print("\n" + "=" * 65)
    print("🔥 TEST 15 PASSED")
    print("=" * 65)

    print("""
FULL PAPER TRADING PIPELINE WORKS

TICK
  ↓
LiveFeed
  ↓
CandleBuilder
  ↓
Strategy
  ↓
ExecutionEngine
  ↓
PaperBroker
  ↓
RiskManager
  ↓
TradeLogger
  ↓
TradingSession
  ↓
LiveFeed shutdown
""")

    print("=" * 65)

else:

    print("\n" + "=" * 65)
    print("❌ TEST 15 FAILED")
    print("=" * 65)


# ============================================================
# CLEAN TEST LOG
# ============================================================

if os.path.exists(test_log_file):

    os.remove(test_log_file)

    print("\n🧹 Test trade log removed.")