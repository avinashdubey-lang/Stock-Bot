from datetime import datetime, time
import time as sleep_time

from login import login_user
from market_data import get_candles, get_latest_candle_stream
from strategy import Strategy
from paper_broker import PaperBroker
from trade_logger import TradeLogger


class TradingBot:

    def __init__(self):

        self.strategy = Strategy()
        self.broker = PaperBroker()
        self.logger = TradeLogger()

        self.smartApi = None

        self.current_day = None
        self.trade_taken_today = False
        self.levels_loaded = False

    # ==========================
    # LOGIN
    # ==========================
    def login(self):
        self.smartApi, _ = login_user()
        print("Login Successful")

    # ==========================
    # RESET DAY
    # ==========================
    def reset_day(self):
        self.strategy.reset()
        self.trade_taken_today = False
        self.levels_loaded = False
        print("\n🔄 NEW DAY RESET DONE")

    # ==========================
    # LOAD LEVELS (ONLY ONCE)
    # ==========================
    def load_levels(self, symbol):

        print("📊 Fetching candles for levels...")

        df = get_candles(self.smartApi, symbol)

        self.strategy.set_opening_range(df)

        self.levels_loaded = True

    # ==========================
    # MAIN LOOP
    # ==========================
    def run(self):

        self.login()

        symbol = "BHARTIARTL-EQ"

        print(f"📡 Streaming candles for {symbol}...")

        for candle in get_latest_candle_stream(self.smartApi, symbol):

            now = datetime.now()
            today = now.date()

            # ==========================
            # DAY RESET (ONLY ONCE)
            # ==========================
            if self.current_day != today:
                self.current_day = today
                self.reset_day()

            # ==========================
            # LOAD LEVELS ONLY AFTER 10:00
            # ==========================
            if (
                not self.levels_loaded
                and now.time() >= time(10, 0)
            ):
                self.load_levels(symbol)

            # ==========================
            # WAIT UNTIL LEVELS READY
            # ==========================
            if not self.levels_loaded:
                continue

            # ==========================
            # SIGNAL CHECK
            # ==========================
            signal = self.strategy.on_candle(candle)

            if signal and not self.trade_taken_today:

                print(f"\n📊 SIGNAL: {signal['action']}")

                opened = self.broker.open_trade(
                    signal["symbol"],
                    signal["action"],
                    signal["entry"],
                    signal["target"],
                    signal["sl"]
                )

                if opened:
                    self.trade_taken_today = True

                    self.logger.log_trade({
                        "symbol": signal["symbol"],
                        "direction": signal["action"],
                        "entry": signal["entry"],
                        "exit": None,
                        "target": signal["target"],
                        "stoploss": signal["sl"],
                        "reason": "OPEN",
                        "pnl": 0
                    })

            # ==========================
            # EXIT CHECK
            # ==========================
            if self.broker.position:

                result = self.broker.check_exit(candle["close"])

                if result:

                    trade = self.broker.trade_history[-1]
                    self.logger.log_trade(trade)

        print("Bot Stopped")


# ==========================
# START BOT
# ==========================
if __name__ == "__main__":
    bot = TradingBot()
    bot.run()