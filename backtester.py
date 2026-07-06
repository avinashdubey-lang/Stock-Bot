from Data_fetcher import get_historical_data
from login import login_user
from market_data import get_token
from config import SYMBOL
import pandas as pd

# =====================================================
# SETTINGS
# =====================================================

Days=720

TARGET_PERCENT = 0.5
SL_PERCENT = 0.5

INITIAL_CAPITAL = 14000

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

smartApi = login_user()[0]

symboltoken = get_token(SYMBOL)

df = get_historical_data(
    smartApi=smartApi,
    symboltoken=symboltoken,
    interval="FIFTEEN_MINUTE",
    days=Days
)

# =====================================================
# FIND DATETIME COLUMN
# =====================================================

df["DateOnly"] = df["Datetime"].dt.date

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

    # =================================================
    # CANDLE COLOR
    # =================================================

    if (
        second["Open"] == second["Close"]
        or
        third["Open"] == third["Close"]
    ):
        continue

    same_color = (
        (second["Close"] > second["Open"] and third["Close"] > third["Open"])
        or
        (second["Close"] < second["Open"] and third["Close"] < third["Open"])
    )

    if not same_color:
        continue

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

                if same_color:
                    target_percent = 0.52
                else:
                    target_percent = 0.27

                target = entry * (1 + TARGET_PERCENT / 100)
                if same_color:
                    sl_percent = 0.49
                else:
                    sl_percent = 0.38
                sl = entry *(1-SL_PERCENT/100)

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

                if same_color:
                    target_percent = 0.53
                else:
                    target_percent = 0.27

                target = entry * (1 - TARGET_PERCENT / 100)

                if same_color:
                    sl_percent = 0.49
                else:
                    sl_percent = 0.38
                sl = entry *(1+SL_PERCENT/100)

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

                if candle["Close"] <= sl:

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

                if candle["Close"] >= sl:

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


            # =============================================
            # EOD EXIT
            # =============================================

            if exit_price is None and i == len(day) - 1:

                exit_price = float(candle["Close"])

                if direction == "LONG":

                    pnl = (
                        (exit_price - entry)
                        * quantity
                    )

                else:

                    pnl = (
                        (entry - exit_price)
                        * quantity
                    )

                reason = "EOD"

            # =============================================
            # SAVE TRADE
            # =============================================

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

if trades_df.empty:
    print("No trades generated.")
    exit()

# =====================================================
# WIN RATE
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

completed_trades = wins + losses

if completed_trades > 0:
    win_rate = (
        wins / completed_trades
    ) * 100
else:
    win_rate = 0

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

print(
    "Total Trades:",
    len(trades_df)
)

print(
    "Winning Trades:",
    wins
)

print(
    "Losing Trades:",
    losses
)

print(
    "EOD Exits:",
    eod
)

print(
    "Break Even Trades :",
    be
)

print(
    "Win Rate:",
    f"{win_rate:.2f}%"
)

# =====================================================
# EXPORT CSV
# =====================================================

trades_df.to_csv(

    f"{SYMBOL}_all_trades.csv",

    index=False

)

print("\nCSV file saved successfully.")