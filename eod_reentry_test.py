from strategy import Strategy
import execution_engine
from execution_engine import ExecutionEngine
from risk_manager import RiskManager
from trade_logger import TradeLogger
from websocket_feed import CandleBuilder
from datetime import datetime


class FakeDateTime:

    current_time = datetime(2026, 1, 1, 14, 58, 45)

    @classmethod
    def now(cls):
        return cls.current_time


execution_engine.datetime = FakeDateTime

class DummyBroker:

    def __init__(self):

        self.position = None

        self.order_count = 0

    def open_trade(self, symbol, direction, entry, target, stoploss):

        self.order_count += 1

        print("\n" + "=" * 60)
        print("🟢 OPEN_TRADE CALLED")
        print("ORDER NUMBER:", self.order_count)
        print("DIRECTION:", direction)
        print("ENTRY:", entry)
        print("=" * 60)

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss
        }

        return self.position

    def close_all(self, reason, exit_price):

        print("\n" + "=" * 60)
        print("🚨 CLOSE_ALL CALLED")
        print("REASON:", reason)
        print("POSITION BEFORE:", self.position)

        if not self.position:
            print("⚠️ NO POSITION — NO ORDER SENT")
            print("=" * 60)
            return None

        self.order_count += 1

        position = self.position.copy()

        exit_side = (
            "SELL"
            if position["direction"] == "BUY"
            else "BUY"
        )

        print("📤 SIMULATED ORDER SENT")
        print("ORDER NUMBER:", self.order_count)
        print("SIDE:", exit_side)

        if position["direction"] == "BUY":
            pnl = exit_price - position["entry"]
        else:
            pnl = position["entry"] - exit_price

        trade = {
            **position,
            "exit": exit_price,
            "reason": reason,
            "pnl": pnl
        }

        self.position = None

        print("POSITION AFTER:", self.position)
        print("=" * 60)

        return trade
    

broker = DummyBroker()

strategy = Strategy()

logger = TradeLogger()

risk = RiskManager()

engine = ExecutionEngine(
    broker,
    logger,
    risk,
    strategy
)


class SimulationFeed:

    def __init__(self, strategy, engine):
        self.strategy = strategy
        self.engine = engine
        self.candle_builder = CandleBuilder()

    def on_data(self, message):

        ltp = message["last_traded_price"] / 100
        ts = datetime.fromtimestamp(message["exchange_timestamp"] / 1000)

        print("\n🔥 SIMULATION TICK")
        print("LTP:", ltp)
        print("TIME:", ts)

        # Same pipeline as LiveFeed
        self.engine.on_tick(ltp)

        if self.engine.trading_done:
            print("🛑 Trading finished. Skipping strategy.")
            return

        candle = self.candle_builder.on_tick(ltp, ts)

        if candle:

            print("\n📊 CANDLE CLOSED")
            print(candle)

            signal = self.strategy.on_candle(candle)

            print("SIGNAL:", signal)

            if signal:

                if signal["type"] == "ENTRY":
                    self.engine.on_signal(signal)

                elif signal["type"] == "EXIT":
                    self.engine.on_exit_signal(
                        signal["reason"],
                        signal["price"]
                    )

feed = SimulationFeed(strategy, engine)

# Simulate bot already initialized on Day 1
strategy.reset()
engine.reset()
risk.reset()

strategy.set_levels(
    high_level=102,
    low_level=98,
    same_colour=True
)


def send_tick(price, timestamp):

    dt = datetime.fromtimestamp(timestamp / 1000)

    FakeDateTime.current_time = dt

    msg = {
        "last_traded_price": int(price * 100),
        "exchange_timestamp": timestamp,
        "volume_trade_for_the_day": 1000
    }

    print("\n===========================")
    print("SIMULATED TIME:", dt)
    print("PRICE:", price)
    print("===========================\n")

    feed.on_data(msg)

def make_timestamp(day, hour, minute, second):

    dt = datetime(2026, 1, day, hour, minute, second)

    return int(dt.timestamp() * 1000)


ticks = [

    # ==========================
    # DAY 1
    # ==========================

    (make_timestamp(1,10,0,0),100),
    (make_timestamp(1,10,5,0),101),
    (make_timestamp(1,10,10,0),103),
    (make_timestamp(1,10,14,55),104),

    # closes 10:00 candle
    (make_timestamp(1,10,15,0),105),

    # next candle
    (make_timestamp(1,10,20,0),106),

    # EOD
    (make_timestamp(1,14,59,0),106),

    # ==========================
    # DAY 2
    # ==========================

    (make_timestamp(2,10,0,0),106),
    (make_timestamp(2,10,5,0),107),
    (make_timestamp(2,10,10,0),109),
    (make_timestamp(2,10,14,55),111),

    # closes 10:00 candle
    (make_timestamp(2,10,15,0),112),

    # next candle
    (make_timestamp(2,10,20,0),113),
]

# ===========================================
# SIMULATE main_live.py
# ===========================================

levels_initialized = True
current_day = datetime.fromtimestamp(ticks[0][0] / 1000).date()


def start_new_day():

    print("🚀 start_new_day() CALLED")

    strategy.reset()
    engine.reset()
    risk.reset()

    strategy.set_levels(
        high_level=110,
        low_level=105,
        same_colour=True
    )


for t, p in ticks:

    ts = datetime.fromtimestamp(t / 1000)

    # -------------------------
    # SAME LOGIC AS main_live.py
    # -------------------------
    if ts.date() != current_day:

        print("\n🌅 NEW TRADING DAY DETECTED")

        current_day = ts.date()

        levels_initialized = False

        feed.candle_builder.reset()

    if (
        not levels_initialized
        and ts.hour >= 10
    ):

        start_new_day()

        levels_initialized = True

    send_tick(p, t)

    print("\nSTATE")
    print("Trading Done :", engine.trading_done)
    print("Trades Taken :", risk.trades_taken)
    print("Strategy Position :", strategy.position)
    print("Broker Position :", broker.position)