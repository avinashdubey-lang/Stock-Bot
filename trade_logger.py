import pandas as pd
import os


class TradeLogger:

    def __init__(
        self,
        filename="trade_log.csv"
    ):

        self.filename = filename

        if not os.path.exists(
            self.filename
        ):

            columns = [
                "Date",
                "Symbol",
                "Direction",
                "Entry",
                "Exit",
                "Target",
                "Stoploss",
                "Reason",
                "PnL"
            ]

            pd.DataFrame(
                columns=columns
            ).to_csv(
                self.filename,
                index=False
            )

    # ==========================
    # SAVE TRADE
    # ==========================

    def log_trade(
        self,
        trade
    ):

        row = {
            "Date":
            pd.Timestamp.now(),

            "Symbol":
            trade["symbol"],

            "Direction":
            trade["direction"],

            "Entry":
            trade["entry"],

            "Exit":
            trade["exit"],

            "Target":
            trade["target"],

            "Stoploss":
            trade["stoploss"],

            "Reason":
            trade["reason"],

            "PnL":
            trade["pnl"]
        }

        df = pd.DataFrame(
            [row]
        )

        df.to_csv(
            self.filename,
            mode="a",
            header=False,
            index=False
        )

        print(
            "Trade Saved"
        )