from datetime import time


class Strategy:

    def __init__(self):
        self.range_high = None
        self.range_low = None
        self.levels_set = False
        self.trade_taken = False

        # store first 2 candles for opening range
        self.buffer = []

    # ==========================
    # RESET
    # ==========================
    def reset(self):
        self.range_high = None
        self.range_low = None
        self.levels_set = False
        self.trade_taken = False
        self.buffer = []

    # ==========================
    # OPENING RANGE (WS VERSION)
    # ==========================
    def set_opening_range_ws(self, candle):

        if self.levels_set:
            return

        # collect first 2 candles only
        self.buffer.append(candle)

        if len(self.buffer) < 2:
            return

        c1 = self.buffer[0]
        c2 = self.buffer[1]

        self.range_high = max(c1["high"], c2["high"])
        self.range_low = min(c1["low"], c2["low"])

        self.levels_set = True

        print("\n📊 OPENING RANGE SET (WS)")
        print("HIGH :", self.range_high)
        print("LOW  :", self.range_low)

    # ==========================
    # SIGNAL GENERATION
    # ==========================
    def on_candle(self, candle):

        if not self.levels_set:
            return None

        if self.trade_taken:
            return None

        close = candle["close"]

        # BREAKOUT BUY
        if close > self.range_high:
            self.trade_taken = True
            print("📈 BUY BREAKOUT")

            return {
                "action": "BUY",
                "symbol": "BHARTIARTL-EQ",
                "entry": close,
                "sl": self.range_low,
                "target": close + (close - self.range_low)
            }

        # BREAKOUT SELL
        if close < self.range_low:
            self.trade_taken = True
            print("📉 SELL BREAKOUT")

            return {
                "action": "SELL",
                "symbol": "BHARTIARTL-EQ",
                "entry": close,
                "sl": self.range_high,
                "target": close - (self.range_high - close)
            }

        return None