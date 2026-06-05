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
            self.api_key
        ) = login_user()

        print("Login Successful")

    # ==========================
    # RESET DAY
    # ==========================
    def reset_day(self):
        self.strategy.reset()
        self.trade_taken_today = False
        print("\n🔄 NEW DAY RESET DONE")

    # ==========================
    # WEB SOCKET HANDLER
    # ==========================
    def on_candle(self, candle):

        now = datetime.now().date()

        if self.current_day != now:
            self.current_day = now
            self.reset_day()

        # STEP 1: build opening range from first 2 candles
        if not self.strategy.levels_set:
            self.strategy.set_opening_range_ws(candle)

        # STEP 2: ignore until levels ready
        if not self.strategy.levels_set:
            return

        # STEP 3: signal check
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

        # STEP 4: exit logic
        if self.broker.position:
            if self.broker.check_exit(candle["close"]):
                trade = self.broker.close_all("TARGET/SL HIT")
                self.logger.log_trade(trade)

    # ==========================
    # RUN
    # ==========================
    def run(self):

        self.login()

        symbol = "BHARTIARTL-EQ"

        start_websocket(
            self.smartApi,
            symbol,
            self.on_candle
        )


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()