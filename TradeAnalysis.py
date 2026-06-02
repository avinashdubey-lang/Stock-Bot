import yfinance as yf
import pandas as pd

# =====================================================
# SETTINGS
# =====================================================

SYMBOL = "BHARTIARTL.NS"

PERIOD = "60d"
INTERVAL = "15m"

TARGET_PERCENT = 0.5
SL_PERCENT = 0.5

INITIAL_CAPITAL = 10000

# 5x Intraday Leverage
LEVERAGE = 5

# =====================================================
# EFFECTIVE CAPITAL
# =====================================================

effective_capital = (
    INITIAL_CAPITAL * LEVERAGE
)

# =====================================================
# DOWNLOAD DATA
# =====================================================

df = yf.download(

    SYMBOL,

    period=PERIOD,

    interval=INTERVAL,

    auto_adjust=True,

    progress=False

)

df.dropna(inplace=True)

# =====================================================
# FIX MULTIINDEX
# =====================================================

if isinstance(
    df.columns,
    pd.MultiIndex
):

    df.columns = (
        df.columns
        .get_level_values(0)
    )

df.reset_index(inplace=True)

# =====================================================
# FIND DATETIME COLUMN
# =====================================================

time_col = None

for col in df.columns:

    if (
        "Date" in str(col)
        or
        "Datetime" in str(col)
    ):

        time_col = col
        break

# =====================================================
# CREATE DATE COLUMN
# =====================================================

df["DateOnly"] = pd.to_datetime(
    df[time_col]
).dt.date

days = df["DateOnly"].unique()

# =====================================================
# TRADE STORAGE
# =====================================================

all_trades = []

capital = INITIAL_CAPITAL

highest_capital = INITIAL_CAPITAL

max_drawdown = 0

# =====================================================
# DAILY LOOP
# =====================================================

for current_day in days:

    day = df[
        df["DateOnly"]
        ==
        current_day
    ].copy()

    day.reset_index(
        drop=True,
        inplace=True
    )

    if len(day) < 5:
        continue

    # =================================================
    # RANGE CREATION
    # Ignore first candle
    # Use 2nd and 3rd candle
    # =================================================

    second = day.iloc[1]
    third = day.iloc[2]

    range_high = max(

        second["High"],
        third["High"]

    )

    range_low = min(

        second["Low"],
        third["Low"]

    )

    trade_taken = False

    # =================================================
    # INTRADAY LOOP
    # =================================================

    for i in range(3, len(day)):

        candle = day.iloc[i]

        # =============================================
        # ENTRY
        # =============================================

        if not trade_taken:

            # LONG ENTRY

            if candle["Close"] > range_high:

                direction = "LONG"

                entry = float(
                    candle["Close"]
                )

                target = entry * (
                    1 + TARGET_PERCENT/100
                )

                sl = entry * (
                    1 - SL_PERCENT/100
                )

                # Quantity based on leveraged capital

                quantity = (
                    effective_capital / entry
                )

                trade_taken = True

                continue


            # SHORT ENTRY

            elif candle["Close"] < range_low:

                direction = "SHORT"

                entry = float(
                    candle["Close"]
                )

                target = entry * (
                    1 - TARGET_PERCENT/100
                )

                sl = entry * (
                    1 + SL_PERCENT/100
                )

                quantity = (
                    effective_capital / entry
                )

                trade_taken = True

                continue


        # =============================================
        # TRADE MANAGEMENT
        # =============================================

        if trade_taken:

            exit_price = None
            pnl = None
            reason = None

            # =========================================
            # LONG TRADE
            # =========================================

            if direction == "LONG":

                # STOPLOSS

                if candle["Low"] <= sl:

                    exit_price = sl

                    pnl = (

                        (exit_price - entry)

                        * quantity

                    )

                    reason = "SL"


                # TARGET

                elif candle["Close"] >= target:

                    exit_price = float(
                        candle["Close"]
                    )

                    pnl = (

                        (exit_price - entry)

                        * quantity

                    )

                    reason = "TARGET"


            # =========================================
            # SHORT TRADE
            # =========================================

            else:

                # STOPLOSS

                if candle["High"] >= sl:

                    exit_price = sl

                    pnl = (

                        (entry - exit_price)

                        * quantity

                    )

                    reason = "SL"


                # TARGET

                elif candle["Close"] <= target:

                    exit_price = float(
                        candle["Close"]
                    )

                    pnl = (

                        (entry - exit_price)

                        * quantity

                    )

                    reason = "TARGET"


            # =========================================
            # SAVE TRADE
            # =========================================

            if exit_price is not None:

                capital += pnl

                # =====================================
                # DRAWDOWN TRACKING
                # =====================================

                if capital > highest_capital:

                    highest_capital = capital

                drawdown = (

                    (
                        highest_capital
                        -
                        capital
                    )

                    / highest_capital

                ) * 100

                if drawdown > max_drawdown:

                    max_drawdown = drawdown


                # =====================================
                # SAVE TRADE DETAILS
                # =====================================

                all_trades.append({

                    "Date": current_day,

                    "Direction": direction,

                    "Entry": round(entry,2),

                    "Exit": round(exit_price,2),

                    "Quantity": round(quantity,2),

                    "PnL": round(pnl,2),

                    "Capital": round(capital,2),

                    "Drawdown%": round(drawdown,2),

                    "Result": reason

                })

                break

# =====================================================
# FINAL DATAFRAME
# =====================================================

trades_df = pd.DataFrame(all_trades)

print("\n")
print("="*140)
print(f"ALL TRADES FOR {SYMBOL}")
print("="*140)

print(trades_df)

print("\n")
print("="*140)

print(
    "Initial Capital:",
    round(INITIAL_CAPITAL,2)
)

print(
    "Leverage Used:",
    f"{LEVERAGE}x"
)

print(
    "Effective Trading Capital:",
    round(effective_capital,2)
)

print(
    "Final Capital:",
    round(capital,2)
)

print(
    "Total Return %:",
    round(
        (
            (capital - INITIAL_CAPITAL)
            /
            INITIAL_CAPITAL
        ) * 100,
        2
    )
)

print(
    "Max Drawdown %:",
    round(max_drawdown,2)
)

# =====================================================
# EXPORT CSV
# =====================================================

trades_df.to_csv(

    f"{SYMBOL}_all_trades.csv",

    index=False

)

print("\nCSV file saved successfully.")