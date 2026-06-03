from datetime import time


class Strategy:

    def __init__(self):
        self.range_high = None
        self.range_low = None
        self.levels_set = False
        self.trade_taken = False

    # ==========================
    # RESET DAILY
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

        df = df.sort_values("time").copy()

        df["hhmm"] = df["time"].dt.strftime("%H:%M")

        # Wait until both candles exist
        candle_930 = df[df["hhmm"] == "09:30"]
        candle_945 = df[df["hhmm"] == "09:45"]

        if candle_930.empty or candle_945.empty:
            return

        # Use ONLY 2nd and 3rd candle
        base = df[df["hhmm"].isin(["09:30", "09:45"])]

        self.range_high = base["high"].max()
        self.range_low = base["low"].min()

        self.levels_set = True

        print("\n📊 OPENING RANGE SET")
        print(f"HIGH : {self.range_high}")
        print(f"LOW  : {self.range_low}")

    # ==========================
    # GENERATE SIGNAL
    # ==========================
    def on_candle(self, candle):

        if not self.levels_set:
            return None

        if self.trade_taken:
            return None

        close = float(candle["close"])

        # BUY BREAKOUT
        if close > self.range_high:

            self.trade_taken = True

            target = round(close * 1.005, 2)
            sl = round(close * 0.995, 2)

            print(f"📈 BUY BREAKOUT @ {close}")
            print(f"🎯 TARGET = {target}")
            print(f"🛑 SL = {sl}")

            return {
                "action": "BUY",
                "symbol": "BHARTIARTL-EQ",
                "entry": close,
                "target": target,
                "sl": sl
            }

        # SELL BREAKOUT
        if close < self.range_low:

            self.trade_taken = True

            target = round(close * 0.995, 2)
            sl = round(close * 1.005, 2)

            print(f"📉 SELL BREAKOUT @ {close}")
            print(f"🎯 TARGET = {target}")
            print(f"🛑 SL = {sl}")

            return {
                "action": "SELL",
                "symbol": "BHARTIARTL-EQ",
                "entry": close,
                "target": target,
                "sl": sl
            }

        return None
