from config import SYMBOL
class Strategy:

    def __init__(self):

        self.high_level = None
        self.low_level = None

        self.levels_set = False
        self.trade_taken = False
        self.current_day = None
        self.position = None
        self.same_colour = False

    # ==========================
    # RESET
    # ==========================

    def reset(self):

        self.high_level = None
        self.low_level = None

        self.levels_set = False
        self.trade_taken = False
        self.position = None
        self.same_colour = False


    # ==========================
    # CLEAR POSITION
    # ==========================
    def clear_position(self):
        self.position = None

    # ==========================
    # SET LEVELS (FROM REST API)
    # ==========================

    def set_levels(
        self,
        high_level,
        low_level,
        same_colour
    ):

        self.high_level = high_level
        self.low_level = low_level
        self.same_colour = same_colour

        self.levels_set = True

        print("\n📊 LEVELS SET")
        print("HIGH :", self.high_level)
        print("LOW  :", self.low_level)
        print("SAME COLOR :", self.same_colour)

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


        close = candle["close"]

        # ==========================
        # EXIT LOGIC
        # ==========================

        if self.position:

            # BUY EXIT
            if self.position["direction"] == "BUY":

                if close >= self.position["target"]:

                    return {
                        "type": "EXIT",
                        "reason": "TARGET_HIT",
                        "price": close
                    }

                if close <= self.position["sl"]:

                    return {
                        "type": "EXIT",
                        "reason": "SL_HIT",
                        "price": close
                    }

            # SELL EXIT
            else:

                if close <= self.position["target"]:

                    return {
                        "type": "EXIT",
                        "reason": "TARGET_HIT",
                        "price": close
                    }

                if close >= self.position["sl"]:

                    return {
                        "type": "EXIT",
                        "reason": "SL_HIT",
                        "price": close
                    }

            return None
        
        if not self.same_colour:
            return None
        
        if self.trade_taken:
            return None

        # BUY BREAKOUT
        if close > self.high_level:

            self.trade_taken = True

            entry = close

            sl = entry * 0.995
            target = entry * 1.005

            print("📈 BUY BREAKOUT")

            self.position = {
                "direction": "BUY",
                "entry": entry,
                "sl": sl,
                "target": target
            }

            return {
                "type": "ENTRY",
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

            sl = entry * 1.005
            target = entry * 0.995

            print("📉 SELL BREAKOUT")

            self.position = {
                "direction": "SELL",
                "entry": entry,
                "sl": sl,
                "target": target
            }

            return {
                "type": "ENTRY",
                "action": "SELL",
                "symbol": SYMBOL,
                "entry": entry,
                "sl": sl,
                "target": target
            }

        return None