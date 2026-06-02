from datetime import time


class Strategy:

    def __init__(self):
        self.range_high = None
        self.range_low = None
        self.levels_set = False
        self.trade_taken = False

    # ==========================
    # RESET
    # ==========================
    def reset(self):
        self.range_high = None
        self.range_low = None
        self.levels_set = False
        self.trade_taken = False

    # ==========================
    # SET OPENING RANGE
    # ==========================
    def set_opening_range(self, df):

        if self.levels_set:
            return

        if df is None or len(df) == 0:
            return

        df = df.sort_values("time")

        # convert to HH:MM string for stable matching
        df["hhmm"] = df["time"].dt.strftime("%H:%M")

        # required candles
        candle_945 = df[df["hhmm"] == "09:45"]
        candle_1000 = df[df["hhmm"] == "10:00"]

        # wait until both exist
        if candle_945.empty or candle_1000.empty:
            return

        # take ONLY those 2 candles
        base = df[df["hhmm"].isin(["09:45", "10:00"])]

        # FINAL FIX: correct high/low logic
        self.range_high = base["high"].max()
        self.range_low = base["low"].min()

        self.levels_set = True

        print("\n📊 LEVELS SET (LOCKED ONCE PER DAY)")
        print("HIGH:", self.range_high)
        print("LOW :", self.range_low)

    # ==========================
    # SIGNAL
    # ==========================
    def on_candle(self, candle):

        if not self.levels_set:
            return None

        if self.trade_taken:
            return None

        close = candle["close"]

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