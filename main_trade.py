from datetime import datetime, time

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
        self.levels_loaded = False

        # 🔥 FIX: track entry candle time
        self.entry_block_time = None

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
        self.levels_loaded = False
        self.entry_block_time = None
        print("\n🔄 NEW DAY RESET DONE")

    # ==========================
    # LOAD LEVELS
    # ==========================
    def load_levels(self, symbol):

        print("📊 Fetching candles for levels...")

        df = get_candles(self.smartApi, symbol)
        self.strategy.set_opening_range(df)

        if self.strategy.levels_set:
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
            # NEW DAY RESET
            # ==========================
            if self.current_day != today:
                self.current_day = today
                self.reset_day()

            # ==========================
            # LOAD LEVELS
            # ==========================
            if (
                not self.levels_loaded
                and now.time() >= time(10, 0)
            ):
                self.load_levels(symbol)

            if not self.levels_loaded:
                continue

            # ==========================
            # EXIT FIRST (SAFE ORDER)
            # ==========================
            if self.broker.position:

                # 🔥 BLOCK SAME CANDLE EXIT
                if self.entry_block_time == candle["time"]:
                    continue

                result = self.broker.check_exit(candle["close"])

                if result:
                    trade = self.broker.trade_history[-1]
                    self.logger.log_trade(trade)

                    print(f"🔴 EXIT EXECUTED: {result}")

                    continue

            # ==========================
            # ENTRY SIGNAL
            # ==========================
            signal = self.strategy.on_candle(candle)

            if signal:

                print(f"\n📊 SIGNAL: {signal['action']}")

                opened = self.broker.open_trade(
                    signal["symbol"],
                    signal["action"],
                    signal["entry"],
                    signal["target"],
                    signal["sl"]
                )

                if opened:

                    # 🔥 IMPORTANT FIX
                    self.entry_block_time = candle["time"]

                    print(f"🟢 TRADE OPENED: {signal['action']} @ {signal['entry']}")

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
            # FORCE EXIT (END OF DAY SAFE)
            # ==========================
            if (
                self.broker.position
                and now.time() >= time(15, 15)
                and self.entry_block_time != candle["time"]
            ):

                entry = self.broker.position["entry"]
                direction = self.broker.position["direction"]
                exit_price = candle["close"]

                pnl = (
                    exit_price - entry
                    if direction == "BUY"
                    else entry - exit_price
                )

                self.broker.close_trade(
                    exit_price,
                    pnl,
                    "MARKET_CLOSE"
                )

                trade = self.broker.trade_history[-1]
                self.logger.log_trade(trade)

                print("🔴 FORCE EXIT (MARKET CLOSE)")

                continue

        print("Bot Stopped")


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
