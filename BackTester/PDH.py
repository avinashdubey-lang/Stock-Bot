import yfinance as yf
import pandas as pd
import numpy as np

# ==========================
# CONFIGURATION
# ==========================

INITIAL_CAPITAL = 100000
RISK_PER_TRADE = 0.01          # 1%
BROKERAGE = 0                  # Keep 0 for now
SLIPPAGE = 0                   # Keep 0 for now



STOCKS = [
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "TATAMOTORS.NS",
    "LT.NS",
    "M&M.NS",
    "SUNPHARMA.NS",
    "AXISBANK.NS"
]

# ==========================
# RESULTS
# ==========================

summary = []
trade_log = []

# ==========================
# START TESTING
# ==========================

for stock in STOCKS:

    print(f"\nTesting {stock}")

    df = yf.download(
        stock,
        interval="15m",
        period="60d",
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        print("No Data")
        continue

    # Remove MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    df["Date"] = df["Datetime"].dt.date

    grouped = df.groupby("Date")

    dates = list(grouped.groups.keys())

    # ==========================
    # METRICS
    # ==========================

    capital = INITIAL_CAPITAL

    wins = 0
    losses = 0
    trades = 0

    gross_profit = 0
    gross_loss = 0

    equity_curve = [capital]

    max_consecutive_wins = 0
    max_consecutive_losses = 0

    current_win_streak = 0
    current_loss_streak = 0

    largest_win = 0
    largest_loss = 0

    # ==========================
    # LOOP THROUGH DAYS
    # ==========================

    for i in range(1, len(dates)):

        prev_day = grouped.get_group(dates[i-1])
        curr_day = grouped.get_group(dates[i])

        previous_high = prev_day["High"].max()
        previous_low = prev_day["Low"].min()

        curr_day = curr_day.reset_index(drop=True)

        traded_today = False

        # ==========================
        # LOOP THROUGH CANDLES
        # ==========================

        for j in range(len(curr_day)-1):

            if traded_today:
                break

            candle = curr_day.iloc[j]

            # BUY condition

            if candle["Close"] > previous_high:

                entry = curr_day.iloc[j+1]["Open"]

                STOPLOSS_MODE = "PDL"        # Previous Day Low
                # STOPLOSS_MODE = "BREAKOUT"
                # STOPLOSS_MODE = "ATR"
                # STOPLOSS_MODE = "FIXED"

                risk_per_share = entry - STOPLOSS_MODE

                if risk_per_share <= 0:
                    continue

                target = entry + risk_per_share

                risk_amount = capital * RISK_PER_TRADE

                quantity = risk_amount / risk_per_share

                # Trade execution will be added in Part 2

                traded_today = True

            # SELL condition

            elif candle["Close"] < previous_low:

                entry = curr_day.iloc[j+1]["Open"]

                STOPLOSS_MODE = "PDH"        # Previous Day Low
                # STOPLOSS_MODE = "BREAKOUT"
                # STOPLOSS_MODE = "ATR"
                # STOPLOSS_MODE = "FIXED"

                risk_per_share = STOPLOSS_MODE - entry

                if risk_per_share <= 0:
                    continue

                target = entry - risk_per_share

                risk_amount = capital * RISK_PER_TRADE

                quantity = risk_amount / risk_per_share

                # Trade execution will be added in Part 2

                traded_today = True