from Data_fetcher import get_historical_data
from login import login_user
from market_data import get_token
from config import SYMBOL
import pandas as pd

# =====================================================
# SETTINGS
# =====================================================

Days=360

TARGET_PERCENT = 0.5
SL_PERCENT = 0.5
BROKERAGE_PER_TRADE = 70

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

                entry = float(candle["Close"])

                target = entry * (1 + TARGET_PERCENT / 100)

                sl = entry * (1 - SL_PERCENT / 100)

                quantity = effective_capital / entry

                trade_taken = True

                continue



            # SHORT ENTRY
            elif candle["Close"] < range_low:
                direction = "SHORT"

                entry = float(candle["Close"])

                target = entry * (1 - TARGET_PERCENT / 100)

                sl = entry * (1 + SL_PERCENT / 100)

                quantity = effective_capital / entry

                trade_taken = True

                continue


        # =============================================
        # TRADE MANAGEMENT
        # =============================================

        if trade_taken:

            exit_price = None
            pnl = None
            reason = None

            # LONG TRADE
            if direction == "LONG":

                if candle["High"] >= target:
                    exit_price = target
                    pnl = (exit_price - entry) * quantity
                    reason = "TARGET"

                elif candle["Low"] <= sl:
                    exit_price = sl
                    pnl = (exit_price - entry) * quantity
                    reason = "SL"

            # SHORT TRADE
            else:

                if candle["Low"] <= target:
                    exit_price = target
                    pnl = (entry - exit_price) * quantity
                    reason = "TARGET"

                elif candle["High"] >= sl:
                    exit_price = sl
                    pnl = (entry - exit_price) * quantity
                    reason = "SL"

            # =============================================
            # EOD EXIT
            # =============================================

            if trade_taken and exit_price is None and i == len(day) - 1:

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

                pnl -= BROKERAGE_PER_TRADE

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

                    "Brokerage": BROKERAGE_PER_TRADE,

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
# MONTHLY METRICS
# =====================================================

trades_df["Date"] = pd.to_datetime(trades_df["Date"])
trades_df["Month"] = trades_df["Date"].dt.to_period("M")

print("\n")
print("=" * 150)
print("MONTHLY PERFORMANCE")
print("=" * 150)

for month, month_df in trades_df.groupby("Month"):

    total_trades = len(month_df)

    wins = len(month_df[month_df["Result"] == "TARGET"])
    losses = len(month_df[month_df["Result"] == "SL"])
    eod = len(month_df[month_df["Result"] == "EOD"])

    completed = wins + losses

    if completed > 0:
        win_rate = (wins / completed) * 100
    else:
        win_rate = 0

    starting_capital = (
        INITIAL_CAPITAL
        if month_df.index[0] == trades_df.index[0]
        else trades_df.loc[month_df.index[0] - 1, "Capital"]
    )

    ending_capital = month_df.iloc[-1]["Capital"]

    monthly_return = (
        (ending_capital - starting_capital)
        / starting_capital
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