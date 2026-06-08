from datetime import datetime, time

from login import login_user
from websocket_stream import start_websocket
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

        symbol = "BHARTIARTL-EQ"

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
        )


# ==========================
# START
# ==========================
if __name__ == "__main__":

    bot = TradingBot()

    bot.run()