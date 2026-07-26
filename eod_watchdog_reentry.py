from strategy import Strategy
import execution_engine
from execution_engine import ExecutionEngine
from risk_manager import RiskManager
from trade_logger import TradeLogger
from websocket_feed import CandleBuilder
from datetime import datetime
import threading
import time


class FakeDateTime:

    current_time = datetime(2026, 1, 1, 14, 58, 45)

    @classmethod
    def now(cls):
        return cls.current_time


execution_engine.datetime = FakeDateTime

class DummyBroker:

    def __init__(self):

        self.position = {
            "symbol": "TEST",
            "direction": "BUY",
            "entry": 100,
            "target": 110,
            "stoploss": 90
        }

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
        print("THREAD:", threading.current_thread().name)
        print("REASON:", reason)
        print("POSITION BEFORE:", self.position)

        if not self.position:
            print("⚠️ NO POSITION — NO ORDER SENT")
            print("=" * 60)
            return None

        # Both threads can potentially read the position
        # before either one clears it.
        position = self.position.copy()

        print("⏳ Simulating broker/API delay...")
        time.sleep(0.2)

        self.order_count += 1

        exit_side = (
            "SELL"
            if position["direction"] == "BUY"
            else "BUY"
        )

        print("\n📤 SIMULATED ORDER SENT")
        print("THREAD:", threading.current_thread().name)
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

strategy.reset()
engine.reset()

strategy.set_levels(102, 98, True)

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

last_price = None


def simulated_watchdog():

    global last_price

    print("🐕 WATCHDOG STARTED")

    # Wait until our simulated clock reaches EOD
    while FakeDateTime.current_time.time() < datetime.strptime(
        "14:59:00", "%H:%M:%S"
    ).time():
        time.sleep(0.001)

    print("\n🔥 WATCHDOG EOD TRIGGERED")
    print("WATCHDOG POSITION:", broker.position)

    if broker.position and last_price is not None:

        print("🚨 WATCHDOG CALLING CLOSE_ALL")

        trade = broker.close_all(
            "EOD_EXIT",
            last_price
        )

        if trade:
            logger.log_trade(trade)
            risk.update_pnl(trade["pnl"])
            strategy.clear_position()

        engine.trading_done = True

    print("🐕 WATCHDOG FINISHED")


def send_tick(price, timestamp):

    global last_price

    last_price = price

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

def make_timestamp(hour, minute, second):
    dt = datetime(2026, 1, 1, hour, minute, second)
    return int(dt.timestamp() * 1000)


ticks = [

    (make_timestamp(14, 58, 45), 100),
    (make_timestamp(14, 58, 50), 101),
    (make_timestamp(14, 58, 55), 102),
    (make_timestamp(14, 59,  0), 103),
    (make_timestamp(14, 59,  5), 104),
    (make_timestamp(14, 59, 10), 105),

    (make_timestamp(15, 0, 0),106),

]

watchdog_thread = threading.Thread(
    target=simulated_watchdog,
    name="EOD-WATCHDOG"
)

watchdog_thread.start()

for t,p in ticks:

    send_tick(p,t)
    time.sleep(0.05)


watchdog_thread.join()