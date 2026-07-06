from Data_fetcher import get_historical_data
from login import login_user
from market_data import get_token

import pandas as pd
import numpy as np

# =====================================================
# CONFIGURATION
# =====================================================

SYMBOL = "NIFTY"

DAYS = 365

TIMEFRAME = "FIFTEEN_MINUTE"

ENTRY_BUFFER = 1.5

TARGET_POINTS = 30

SL_POINTS = 15

MAX_RANGE = 500

MAX_TRADES_PER_DAY = 2

BROKERAGE = 70

INITIAL_CAPITAL = 100000

LEVERAGE = 1

SQUARE_OFF_TIME = "15:15"

# =====================================================
# LOGIN
# =====================================================

smartApi = login_user()[0]

# =====================================================
# TOKEN
# =====================================================

symboltoken = get_token(SYMBOL)

# =====================================================
# DOWNLOAD DATA
# =====================================================

print("=" * 120)
print("DOWNLOADING HISTORICAL DATA")
print("=" * 120)

df = get_historical_data(
    smartApi=smartApi,
    symboltoken=symboltoken,
    interval=TIMEFRAME,
    days=DAYS
)

if df.empty:
    raise Exception("No historical data received.")

# =====================================================
# DATA PREPARATION
# =====================================================

df["Datetime"] = pd.to_datetime(df["Datetime"])

df["Date"] = df["Datetime"].dt.date

df["Time"] = df["Datetime"].dt.strftime("%H:%M")

df.sort_values("Datetime", inplace=True)

df.reset_index(drop=True, inplace=True)

# =====================================================
# VOLUME MOVING AVERAGE
# =====================================================

df["Volume_MA5"] = (

    df["Volume"]

    .rolling(5)

    .mean()

)

# =====================================================
# STORAGE
# =====================================================

capital = INITIAL_CAPITAL

highest_capital = INITIAL_CAPITAL

max_drawdown = 0

all_trades = []

# =====================================================
# HELPER
# =====================================================

def process_day(day_df, current_day):

    day_df = day_df.copy()

    day_df.reset_index(
        drop=True,
        inplace=True
    )

    if len(day_df) < 5:
        return []

    # ----------------------------------------------
    # FIRST CANDLE
    # ----------------------------------------------

    first = day_df.iloc[0]

    # ----------------------------------------------
    # REFERENCE RANGE
    # ----------------------------------------------

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

    range_width = range_high - range_low

    print(
    current_day,
    round(range_high,2),
    round(range_low,2),
    round(range_width,2)
)

    # ----------------------------------------------
    # RANGE FILTER
    # ----------------------------------------------

    if range_width > MAX_RANGE:

        return []

    trades = []

    trades_taken = 0

    sl_hits = 0

    position = None

    return {
        "day_df": day_df,
        "range_high": range_high,
        "range_low": range_low,
        "trades": trades,
        "trades_taken": trades_taken,
        "sl_hits": sl_hits,
        "position": position
    }

# =====================================================
# DAILY DATA
# =====================================================

days = df["Date"].unique()

print(f"\nTrading Days : {len(days)}")

# =====================================================
# BACKTEST ENGINE
# =====================================================

for current_day in days:

    day_df = df[
        df["Date"] == current_day
    ].copy()

    state = process_day(day_df, current_day)

    if not state:
        continue

    day_df = state["day_df"]

    range_high = state["range_high"]

    range_low = state["range_low"]

    trades_taken = 0

    sl_hits = 0

    position = None

    # =================================================
    # START AFTER 10:00 AM
    # =================================================

    for i in range(3, len(day_df)):

        candle = day_df.iloc[i]

        # =============================================
        # STOP AFTER TWO TRADES
        # =============================================

        if trades_taken >= MAX_TRADES_PER_DAY:
            break

        # =============================================
        # STOP AFTER TWO SL
        # =============================================

        if sl_hits >= 2:
            break

        # =============================================
        # SQUARE OFF
        # =============================================

        if candle["Time"] >= SQUARE_OFF_TIME:

            if position is not None:

                exit_price = candle["Close"]

                if position["Direction"] == "LONG":

                    pnl = (

                        exit_price

                        -

                        position["Entry"]

                    )

                else:

                    pnl = (

                        position["Entry"]

                        -

                        exit_price

                    )

                pnl *= position["Quantity"]

                pnl -= BROKERAGE

                capital += pnl

                all_trades.append({

                    "Date": current_day,

                    "Direction": position["Direction"],

                    "Entry": round(position["Entry"],2),

                    "Exit": round(exit_price,2),

                    "Quantity": position["Quantity"],

                    "PnL": round(pnl,2),

                    "Result": "EOD"

                })

                position = None

            break

        # =============================================
        # ENTRY
        # =============================================

        if position is None:

            # ----------------------------
            # Volume Filter
            # ----------------------------

            # Volume filter disabled for debugging

            # if pd.isna(candle["Volume_MA5"]):
            #     continue

            # if candle["Volume"] <= candle["Volume_MA5"]:
            #     continue

            # ----------------------------
            # LONG ENTRY
            # ----------------------------

            prev = day_df.iloc[i - 1]

            if (
                prev["Close"] <= range_high + ENTRY_BUFFER
                and
                candle["Close"] > range_high + ENTRY_BUFFER
            ):

                entry = candle["Close"]

                quantity = int(
                    (capital * LEVERAGE)
                    / entry
                )

                sl = max(
                    entry - SL_POINTS,
                    range_low
                )

                target = entry + TARGET_POINTS

                position = {

                    "Direction": "LONG",

                    "Entry": entry,

                    "SL": sl,

                    "Target": target,

                    "Quantity": quantity,

                    "BreakEven": False

                }

                trades_taken += 1

                continue

            # ----------------------------
            # SHORT ENTRY
            # ----------------------------

            elif (
                prev["Close"] >= range_low - ENTRY_BUFFER
                and
                candle["Close"] < range_low - ENTRY_BUFFER
            ):

                entry = candle["Close"]

                quantity = int(
                    (capital * LEVERAGE)
                    / entry
                )

                sl = min(
                    entry + SL_POINTS,
                    range_high
                )

                target = entry - TARGET_POINTS

                position = {

                    "Direction": "SHORT",

                    "Entry": entry,

                    "SL": sl,

                    "Target": target,

                    "Quantity": quantity,

                    "BreakEven": False

                }

                trades_taken += 1

                continue

        # =============================================
        # TRADE MANAGEMENT
        # =============================================

        else:

            if position is None:
                continue

            direction = position["Direction"]

            entry = position["Entry"]

            target = position["Target"]

            sl = position["SL"]

            quantity = position["Quantity"]

            break_even = position["BreakEven"]

            exit_price = None

            result = None


        # -------------------------------- LONG

            if direction == "LONG":

                # Move SL to Entry

                if (

                    not break_even

                    and

                    candle["High"]

                    >=

                    entry + 20

                ):

                    position["SL"] = entry

                    position["BreakEven"] = True

                    sl = entry

                # Stop

                if candle["Low"] <= sl:

                    exit_price = sl

                    if sl == entry:

                        result = "BE"

                    else:

                        result = "SL"

                        sl_hits += 1

                # Target

                elif candle["High"] >= target:

                    exit_price = target

                    result = "TARGET"

            # -------------------------------- SHORT

            else:

                if (

                    not break_even

                    and

                    candle["Low"]

                    <=

                    entry - 20

                ):

                    position["SL"] = entry

                    position["BreakEven"] = True

                    sl = entry

                if candle["High"] >= sl:

                    exit_price = sl

                    if sl == entry:

                        result = "BE"

                    else:

                        result = "SL"

                        sl_hits += 1

                elif candle["Low"] <= target:

                    exit_price = target

                    result = "TARGET"

            # =========================================
            # EXIT
            # =========================================

            if exit_price is not None:

                if direction == "LONG":

                    pnl = (

                        exit_price

                        -

                        entry

                    )

                else:

                    pnl = (

                        entry

                        -

                        exit_price

                    )

                pnl *= quantity

                pnl -= BROKERAGE

                capital += pnl

                if capital > highest_capital:

                    highest_capital = capital

                drawdown = (

                    (

                        highest_capital

                        -

                        capital

                    )

                    /

                    highest_capital

                ) * 100

                max_drawdown = max(

                    max_drawdown,

                    drawdown

                )

                all_trades.append({

                    "Date": current_day,

                    "Direction": direction,

                    "Entry": round(entry,2),

                    "Exit": round(exit_price,2),

                    "Quantity": quantity,

                    "PnL": round(pnl,2),

                    "Capital": round(capital,2),

                    "Drawdown%": round(drawdown,2),

                    "Result": result

                })

                position = None

# =====================================================
# FINAL DATAFRAME
# =====================================================

trades_df = pd.DataFrame(all_trades)

if trades_df.empty:

    print("\nNo trades generated.")

    exit()

# =====================================================
# MONTH COLUMN
# =====================================================

trades_df["Date"] = pd.to_datetime(trades_df["Date"])

trades_df["Month"] = trades_df["Date"].dt.to_period("M")

# =====================================================
# MONTHLY PERFORMANCE
# =====================================================

print("\n")
print("=" * 150)
print("MONTHLY PERFORMANCE")
print("=" * 150)

for month, month_df in trades_df.groupby("Month"):

    total_trades = len(month_df)

    wins = len(
        month_df[
            month_df["Result"] == "TARGET"
        ]
    )

    losses = len(
        month_df[
            month_df["Result"] == "SL"
        ]
    )

    be = len(
        month_df[
            month_df["Result"] == "BE"
        ]
    )

    eod = len(
        month_df[
            month_df["Result"] == "EOD"
        ]
    )

    completed = wins + losses

    if completed > 0:

        win_rate = (

            wins

            /

            completed

        ) * 100

    else:

        win_rate = 0

    starting_capital = (

        INITIAL_CAPITAL

        if month_df.index[0] == trades_df.index[0]

        else trades_df.loc[
            month_df.index[0] - 1,
            "Capital"
        ]

    )

    ending_capital = month_df.iloc[-1]["Capital"]

    monthly_return = (

        (
            ending_capital

            -

            starting_capital

        )

        /

        starting_capital

    ) * 100

    month_dd = month_df["Drawdown%"].max()

    print(f"\n📅 {month}")

    print("-" * 60)

    print(f"Starting Capital : {starting_capital:.2f}")

    print(f"Ending Capital   : {ending_capital:.2f}")

    print(f"Monthly Return   : {monthly_return:.2f}%")

    print(f"Total Trades     : {total_trades}")

    print(f"Winning Trades   : {wins}")

    print(f"Losing Trades    : {losses}")

    print(f"EOD Exits        : {eod}")

    print(f"Win Rate         : {win_rate:.2f}%")

    print(f"Max Drawdown     : {month_dd:.2f}%")

# =====================================================
# OVERALL STATISTICS
# =====================================================

wins = len(

    trades_df[
        trades_df["Result"] == "TARGET"
    ]

)

losses = len(
    trades_df[
        trades_df["Result"] == "SL"
    ]
)

be = len(
    trades_df[
        trades_df["Result"] == "BE"
    ]
)

eod = len(

    trades_df[
        trades_df["Result"] == "EOD"
    ]

)

completed = wins + losses

if completed > 0:

    win_rate = (

        wins

        /

        completed

    ) * 100

else:

    win_rate = 0

gross_profit = trades_df[
    trades_df["PnL"] > 0
]["PnL"].sum()

gross_loss = abs(

    trades_df[
        trades_df["PnL"] < 0
    ]["PnL"].sum()

)

if gross_loss == 0:

    profit_factor = float("inf")

else:

    profit_factor = gross_profit / gross_loss

# =====================================================
# DISPLAY RESULTS
# =====================================================

print("\n")
print("=" * 150)
print(f"ALL TRADES FOR {SYMBOL}")
print("=" * 150)

print(trades_df)

print("\n")
print("=" * 150)

print(
    "Initial Capital :",
    round(INITIAL_CAPITAL,2)
)

print(
    "Final Capital :",
    round(capital,2)
)

print(
    "Net Profit :",
    round(
        capital - INITIAL_CAPITAL,
        2
    )
)

print(
    "Total Return % :",
    round(

        (
            (
                capital
                -
                INITIAL_CAPITAL
            )

            /

            INITIAL_CAPITAL

        ) * 100,

        2

    )
)

print(
    "Gross Profit :",
    round(gross_profit,2)
)

print(
    "Gross Loss :",
    round(gross_loss,2)
)

print(
    "Profit Factor :",
    round(profit_factor,2)
)

print(
    "Maximum Drawdown % :",
    round(max_drawdown,2)
)

print(
    "Total Trades :",
    len(trades_df)
)

print(
    "Winning Trades :",
    wins
)

print(
    "Losing Trades :",
    losses
)

print(
    "EOD Exits :",
    eod
)

print(
    "Win Rate :",
    f"{win_rate:.2f}%"
)

# =====================================================
# EXPORT CSV
# =====================================================

trades_df.to_csv(

    f"{SYMBOL}_ORB_Backtest.csv",

    index=False

)

print("\nCSV exported successfully.")