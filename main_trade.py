from datetime import datetime, time

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

        print("✅ LOGIN SUCCESSFUL")

    # ==========================
    # RESET DAY
    # ==========================

    def reset_day(self):

        self.strategy.reset()

        self.trade_taken_today = False

        print("\n🔄 NEW DAY RESET DONE")

    # ==========================
    # ON NEW CANDLE
    # ==========================

    def on_candle(self, candle):

        today = datetime.now().date()

        # ----------------------
        # Daily Reset
        # ----------------------
        if self.current_day != today:

            self.current_day = today

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

        if signal and not self.trade_taken_today:

            print(
                f"\n📊 SIGNAL: {signal['action']}"
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
        if self.broker.position:

            trade = self.broker.check_exit(
                candle["close"]
            )

            if trade:

                self.logger.log_trade(
                    trade
                )

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

        # 1. GET OPENING LEVELS (REST ONCE)
        high_level, low_level = get_opening_levels(
            self.smartApi,
            symbol
        )

        # 2. SET STRATEGY LEVELS
        self.strategy.set_levels(high_level, low_level)

        print(f"📡 Starting WebSocket for {symbol}")

        # 3. RECONNECT LOOP (ONLY HERE)
        import time

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
                    self.on_candle
                )

            except Exception as e:
                print(f"\n❌ WebSocket Crashed: {e}")
                print(f"🔄 Reconnecting in {wait} seconds...")

                time.sleep(wait)
                wait = min(wait * 2, 60)

# ==========================
# START
# ==========================
if __name__ == "__main__":

    bot = TradingBot()

    bot.run()