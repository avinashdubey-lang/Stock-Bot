from config import SYMBOL
class Strategy:

    def __init__(self):

        self.high_level = None
        self.low_level = None

        self.levels_set = False
        self.trade_taken = False
        self.current_day = None

    # ==========================
    # RESET
    # ==========================

    def reset(self):

        self.high_level = None
        self.low_level = None

        self.levels_set = False
        self.trade_taken = False

    # ==========================
    # SET LEVELS (FROM REST API)
    # ==========================

    def set_levels(
        self,
        high_level,
        low_level
    ):

        self.high_level = high_level
        self.low_level = low_level

        self.levels_set = True

        print("\n📊 LEVELS SET")
        print("HIGH :", self.high_level)
        print("LOW  :", self.low_level)

    # ==========================
    # SIGNAL GENERATION
    # ==========================

    def on_candle(self, candle):

        if not self.levels_set:
            return None

        candle_day = candle["time"].date()

        if self.current_day != candle_day:
            self.current_day = candle_day
            self.trade_taken = False

        if self.trade_taken:
            return None

        close = candle["close"]

        # BUY BREAKOUT
        if close > self.high_level:

            self.trade_taken = True

            entry = close

            sl = entry * 0.999
            target = entry * 1.001

            print("📈 BUY BREAKOUT")

            return {
                "action": "BUY",
                "symbol": SYMBOL,
                "entry": entry,
                "sl": sl,
                "target": target
            }

        # SELL BREAKOUT
        if close < self.low_level:

            self.trade_taken = True

            entry = close

            sl = entry * 1.001
            target = entry * 0.999

            print("📉 SELL BREAKOUT")

            return {
                "action": "SELL",
                "symbol": SYMBOL,
                "entry": entry,
                "sl": sl,
                "target": target
            }

        return None