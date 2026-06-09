#my main
from datetime import datetime
import time
from datetime import time as dtime

from login import login_user
from market_data import get_opening_levels, get_token
from websocket_feed import start_websocket
from strategy import Strategy
from execution_engine import ExecutionEngine
from paper_broker import PaperBroker
from trade_logger import TradeLogger


class TradingBot:

    def __init__(self):

        self.strategy = Strategy()
        self.broker = PaperBroker()
        self.logger = TradeLogger()

        self.execution_engine = ExecutionEngine(self.broker, self.logger)

        self.smartApi = None
        self.feed_token = None
        self.client_code = None
        self.api_key = None
        self.jwt_token = None

        self.current_day = None

    # ==========================
    # LOGIN
    # ==========================
    def login(self):

        (
            self.smartApi,
            self.feed_token,
            self.client_code,
            self.api_key,
            self.jwt_token
        ) = login_user()

        print("✅ LOGIN SUCCESSFUL")

    # ==========================
    # RESET DAY
    # ==========================
    def reset_day(self):

        self.strategy.reset()
        self.execution_engine.reset()

        print("\n🔄 NEW DAY RESET DONE")

    # ==========================
    # ON CANDLE
    # ==========================
    def on_candle(self, candle):

        today = datetime.now().date()


        # reset daily state
        if self.current_day != today:
            self.current_day = today
            self.reset_day()

        # build opening range
        if not self.strategy.levels_set:
            return

        # generate signal
        signal = self.strategy.on_candle(candle)

        if signal:
            self.execution_engine.on_signal(signal)


    # ==========================
    # RUN
    # ==========================
    def run(self):

        self.login()
        self.current_day = datetime.now().date()

        time.sleep(2)

        symbol = "BHARTIARTL-EQ"
        symboltoken = get_token(symbol)

        print("⏳ Waiting for 10:00 AM to fetch opening levels...")

        while datetime.now().time() < dtime(10, 0):
            time.sleep(1)

        while True:

            try:

                high_level, low_level = get_opening_levels(
                    self.smartApi,
                    symbol
                )

                self.strategy.set_levels(
                    high_level,
                    low_level
                )

                break

            except Exception as e:

                print(f"\n⚠️ OPENING LEVEL FETCH FAILED: {e}")
                print("⏳ Retrying in 10 seconds...")

                time.sleep(10)

        print("✅ Opening levels set at 10:00 AM")

        print(f"📡 Starting WebSocket for {symbol}")

        wait = 5

        while True:
            try:
                print("\n🚀 Starting WebSocket...")

                start_websocket(
                    self.smartApi,
                    self.feed_token,
                    self.client_code,
                    self.api_key,
                    symboltoken,
                    self.on_candle,
                    self.execution_engine
                )

                wait = 5

            except Exception as e:
                print(f"\n❌ WebSocket Crashed: {e}")
                print(f"🔄 Reconnecting in {wait} seconds...")

                time.sleep(wait)
                wait = min(wait * 2, 60)


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()