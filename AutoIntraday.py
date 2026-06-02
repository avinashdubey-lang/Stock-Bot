import yfinance as yf
import pandas as pd
import time
from datetime import datetime

# =====================================================
# SETTINGS
# =====================================================
active_trades = {}
completed_trades = []
traded_today = {}

opening_ranges = {}
STOCKS = [
   "BHARTIARTL.NS"
]

INTERVAL = "15m"
PERIOD = "5d"

TARGET_PERCENT = 0.5
SL_PERCENT = 0.5

CHECK_EVERY_SECONDS = 60

# =====================================================
# INTERNAL STORAGE
# =====================================================

active_trades = {}
completed_trades = []
traded_today = {}


# =====================================================
# GET TODAY DATE
# =====================================================


def get_today():
    return str(datetime.now().date())


# =====================================================
# DOWNLOAD DATA
# =====================================================


def get_data(symbol):

    df = yf.download(
        symbol,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=True,
        progress=False
    )

    if len(df) == 0:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(inplace=True)

    df.reset_index(inplace=True)

    return df


# =====================================================
# GET TODAY CANDLES
# =====================================================


def get_today_data(df):

    time_col = None

    for col in df.columns:
        if "Date" in str(col) or "Datetime" in str(col):
            time_col = col
            break

    if time_col is None:
        return None

    df["DateOnly"] = pd.to_datetime(df[time_col]).dt.date

    today = datetime.now().date()

    day_df = df[df["DateOnly"] == today].copy()

    day_df.reset_index(drop=True, inplace=True)

    return day_df


# =====================================================
# ENTRY CHECK
# =====================================================


def check_entry(symbol, day_df):

    if len(day_df) < 4:
        return

    today = get_today()

    if traded_today.get(symbol) == today:
        return

    # =========================
    # CREATE LEVELS AT 10:00
    # =========================

    if symbol not in opening_ranges:

        second = day_df.iloc[1]
        third = day_df.iloc[2]

        range_high = max(
            second["High"],
            third["High"]
        )

        range_low = min(
            second["Low"],
            third["Low"]
        )

        opening_ranges[symbol] = {

            "high": range_high,
            "low": range_low

        }

        print("\n======================")
        print(f"{symbol}")
        print(
            f"Range High: {round(range_high,2)}"
        )
        print(
            f"Range Low : {round(range_low,2)}"
        )
        print("======================")

        return


    # =========================
    # USE STORED LEVELS
    # =========================

    range_high = opening_ranges[symbol]["high"]
    range_low = opening_ranges[symbol]["low"]

    latest = day_df.iloc[-1]

    close_price = float(
        latest["Close"]
    )


    # LONG

    if close_price > range_high:

        entry = close_price

        target = entry * (
            1 + TARGET_PERCENT/100
        )

        sl = entry * (
            1 - SL_PERCENT/100
        )

        active_trades[symbol] = {

            "Direction": "LONG",
            "Entry": entry,
            "Target": target,
            "SL": sl,
            "EntryTime": str(datetime.now())

        }

        traded_today[symbol] = today

        print("\n======================")
        print(f"LONG ENTRY -> {symbol}")
        print(f"Entry : {round(entry,2)}")
        print(f"Target: {round(target,2)}")
        print(f"SL    : {round(sl,2)}")
        print("======================")


    # SHORT

    elif close_price < range_low:

        entry = close_price

        target = entry * (
            1 - TARGET_PERCENT/100
        )

        sl = entry * (
            1 + SL_PERCENT/100
        )

        active_trades[symbol] = {

            "Direction": "SHORT",
            "Entry": entry,
            "Target": target,
            "SL": sl,
            "EntryTime": str(datetime.now())

        }

        traded_today[symbol] = today

        print("\n======================")
        print(f"SHORT ENTRY -> {symbol}")
        print(f"Entry : {round(entry,2)}")
        print(f"Target: {round(target,2)}")
        print(f"SL    : {round(sl,2)}")
        print("======================")


# =====================================================
# SAVE RESULTS
# =====================================================


def save_results():

    if len(completed_trades) == 0:
        return

    df = pd.DataFrame(completed_trades)

    df.to_csv("trade_results.csv", index=False)


# =====================================================
# MAIN LOOP
# =====================================================

print("\nLIVE PAPER TRADING BOT STARTED...")
print("Waiting for market data...\n")

while True:

    try:

        current_time = datetime.now().strftime("%H:%M:%S")

        print(f"\nChecking Market -> {current_time}")

        for symbol in STOCKS:

            df = get_data(symbol)

            if df is None:
                continue

            day_df = get_today_data(df)

            if day_df is None:
                continue

            if len(day_df) < 4:
                continue

            # Check new entry
            if symbol not in active_trades:
                check_entry(symbol, day_df)

            # Manage active trade
            else:
                manage_trade(symbol, day_df)

        save_results()

        print("Sleeping...\n")

        time.sleep(CHECK_EVERY_SECONDS)

    except Exception as e:

        print("ERROR:", e)

        time.sleep(CHECK_EVERY_SECONDS)
