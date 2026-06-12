import pandas as pd


class InstrumentLookup:

    def __init__(self, filepath="instruments.csv"):

        self.filepath = filepath

        self.df = pd.read_csv(filepath)

        # normalize columns (Angel CSV usually has these)
        self.df.columns = [col.strip().lower() for col in self.df.columns]

        print("✅ Instrument file loaded")

    # ==========================
    # GET TOKEN
    # ==========================
    def get_token(self, symbol, exchange="NSE"):

        row = self.df[
            (self.df["symbol"] == symbol) &
            (self.df["exchange"] == exchange)
        ]

        if row.empty:
            raise Exception(f"Token not found for {symbol}")

        return str(row.iloc[0]["token"])

    # ==========================
    # GET FULL INSTRUMENT INFO
    # ==========================
    def get_instrument(self, symbol, exchange="NSE"):

        row = self.df[
            (self.df["symbol"] == symbol) &
            (self.df["exchange"] == exchange)
        ]

        if row.empty:
            raise Exception(f"Instrument not found for {symbol}")

        return row.iloc[0].to_dict()