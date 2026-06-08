<<<<<<< ours
from datetime import datetime, time

=======
from datetime import datetime
>>>>>>> theirs
from login import login_user
from market_data import get_opening_levels, get_token
from websocket_feed import start_websocket
from strategy import Strategy
from paper_broker import PaperBroker
from trade_logger import TradeLogger


class TradingBot:

    def __init__(self):

        self.strategy = Strategy()
        self.broker = PaperBroker()
        self.logger = TradeLogger()

        self.smartApi = None
        self.feed_token = None
        self.client_code = None
        self.api_key = None
        self.jwt_token = None

        self.current_day = None
        self.trade_taken_today = False

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

<<<<<<< ours
        print("✅ LOGIN SUCCESSFUL")
=======
        print("✅ Login Successful")
>>>>>>> theirs

    # ==========================
    # RESET DAY
    # ==========================

    def reset_day(self):

        self.strategy.reset()

        self.trade_taken_today = False

        print("\n🔄 NEW DAY RESET DONE")

    # ==========================
<<<<<<< ours
    # ON NEW CANDLE
=======
    # CANDLE HANDLER
>>>>>>> theirs
    # ==========================

    def on_candle(self, candle):

        today = datetime.now().date()

        # ----------------------
        # Daily Reset
        # ----------------------
        if self.current_day != today:

            self.current_day = today

<<<<<<< ours
            self.reset_day()

        # ----------------------
        # Opening Range
        # ----------------------
        if not self.strategy.levels_set:

            self.strategy.set_opening_range_ws(
                candle
            )

        if not self.strategy.levels_set:
            return

        # ----------------------
        # Signal Generation
        # ----------------------
        signal = self.strategy.on_candle(
            candle
        )
=======
        if self.current_day != now:

            self.current_day = now

            self.reset_day()

            print("\n========== DEBUG ==========")
            print("Current Close:", candle["close"])
            print("Range High:", self.strategy.range_high)
            print("Range Low:", self.strategy.range_low)
            print("Levels Set:", self.strategy.levels_set)
            print("===========================\n")

        signal = self.strategy.on_candle(candle)
>>>>>>> theirs

        if signal and not self.trade_taken_today:

            print(
<<<<<<< ours
                f"\n📊 SIGNAL: {signal['action']}"
=======
                f"\n📊 SIGNAL : "
                f"{signal['action']}"
>>>>>>> theirs
            )

            opened = self.broker.open_trade(
                signal["symbol"],
                signal["action"],
                signal["entry"],
                signal["target"],
                signal["sl"]
            )

            if opened:

                self.trade_taken_today = True

                print(
                    f"🟢 TRADE OPENED: "
                    f"{signal['action']} "
                    f"@ {signal['entry']}"
                )

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

<<<<<<< ours
        # ----------------------
        # Market Close Exit
        # ----------------------
        current_time = datetime.now().time()

        if (
            self.broker.position
            and current_time >= time(15, 15)
        ):

            trade = self.broker.close_all(
                candle["close"],
                "MARKET_CLOSE"
            )

            if trade:

                self.logger.log_trade(
                    trade
                )

                print(
                    "🔴 MARKET CLOSE EXIT"
                )

            return

        # ----------------------
        # Target / Stoploss Exit
        # ----------------------
=======
        # TEMPORARY EXIT LOGIC
>>>>>>> theirs
        if self.broker.position:

            trade = self.broker.check_exit(
                candle["close"]
            )

            if trade:

<<<<<<< ours
                self.logger.log_trade(
                    trade
                )
=======
                self.logger.log_trade(trade)
>>>>>>> theirs

    # ==========================
    # RUN BOT
    # ==========================

    def run(self):

        self.login()

        self.current_day = datetime.now().date()

        import time
        time.sleep(2)

        symbol = "BHARTIARTL-EQ"
        symboltoken = get_token(symbol)

<<<<<<< ours
        print(
            f"📡 Starting WebSocket for {symbol}"
        )

        start_websocket(
            self.smartApi,
            self.feed_token,
            self.client_code,
            self.api_key,
            symbol,
            self.on_candle
=======
        # ----------------------
        # GET LEVELS FROM REST
        # ----------------------

        high_level, low_level = (
            get_opening_levels(
                self.smartApi,
                symbol
            )
>>>>>>> theirs
        )

        self.strategy.set_levels(
            high_level,
            low_level
        )

        # ----------------------
        # START WEBSOCKET
        # ----------------------

        while True:

            try:

                print("\n🚀 Starting WebSocket...")

                start_websocket(
                    self.smartApi,
                    self.feed_token,
                    self.client_code,
                    self.api_key,
                    symboltoken,
                    self.on_candle
                )

            except Exception as e:

                print(
                    f"\n❌ WebSocket Crashed: {e}"
                )

                print(
                    "🔄 Reconnecting in 10 seconds..."
                )

                import time
                time.sleep(10)


# ==========================
# START
# ==========================
if __name__ == "__main__":

    bot = TradingBot()

    bot.run()