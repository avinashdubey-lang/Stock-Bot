#trade_logger.py
import pandas as pd
import os


class TradeLogger:

    def __init__(self, filename="trade_log.csv"):

        self.filename = filename

        if not os.path.exists(self.filename):

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

            pd.DataFrame(columns=columns).to_csv(
                self.filename,
                index=False
            )

    # ==========================
    # SAVE TRADE
    # ==========================
    def log_trade(self, trade):

        if trade is None:
            print("⚠️ No trade to log")
            return

        row = {
            "Date": pd.Timestamp.now(),
            "Symbol": trade.get("symbol", ""),
            "Direction": trade.get("direction", ""),
            "Entry": trade.get("entry", 0),
            "Exit": trade.get("exit", None),
            "Target": trade.get("target", 0),
            "Stoploss": trade.get("stoploss", 0),
            "Reason": trade.get("reason", ""),
            "PnL": trade.get("pnl", 0)
        }

        df = pd.DataFrame([row])

        df.to_csv(
            self.filename,
            mode="a",
            header=False,
            index=False
        )

        print("📁 Trade Saved")