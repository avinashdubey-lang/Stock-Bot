from Data_fetcher import get_historical_data
from login import login_user
from market_data import get_token
from config import STOCKS

import pandas as pd

# =====================================================
# SETTINGS
# =====================================================

Days = 30

BROKERAGE_PER_TRADE = 70

INITIAL_CAPITAL = 14000

LEVERAGE = 5

effective_capital = INITIAL_CAPITAL * LEVERAGE

# =====================================================
# LOGIN
# =====================================================

smartApi = login_user()[0]

# =====================================================
# DOWNLOAD DATA FOR ALL STOCKS
# =====================================================

stock_data = {}

print("=" * 120)
print("DOWNLOADING DATA")
print("=" * 120)

for symbol in STOCKS:

    print(f"Downloading {symbol}...")

    token = get_token(symbol)

    df = get_historical_data(
        smartApi=smartApi,
        symboltoken=token,
        interval="FIFTEEN_MINUTE",
        days=Days
    )

    df["DateOnly"] = df["Datetime"].dt.date

    stock_data[symbol] = df

print("\nDownload Complete.")

# =====================================================
# FIND COMMON DAYS
# =====================================================

common_days = sorted(
    list(
        set.intersection(
            *[
                set(df["DateOnly"].unique())
                for df in stock_data.values()
            ]
        )
    )
)

# =====================================================
# PORTFOLIO VARIABLES
# =====================================================

capital = INITIAL_CAPITAL

highest_capital = INITIAL_CAPITAL

max_drawdown = 0

portfolio_trades = []

winner_history = []

previous_day_winner = None


# =====================================================
# STRATEGY FUNCTION
# =====================================================

def simulate_day(day):

    if len(day) < 5:
        return None

    day = day.copy()

    day.reset_index(
        drop=True,
        inplace=True
    )

    second = day.iloc[1]

    third = day.iloc[2]

    if (
        second["Open"] == second["Close"]
        or
        third["Open"] == third["Close"]
    ):
        return None

    same_color = (
        (
            second["Close"] > second["Open"]
            and
            third["Close"] > third["Open"]
        )
        or
        (
            second["Close"] < second["Open"]
            and
            third["Close"] < third["Open"]
        )
    )

    if not same_color:
        return None

    range_high = max(
        second["High"],
        third["High"]
    )

    range_low = min(
        second["Low"],
        third["Low"]
    )

    trade_taken = False

    direction = None
    entry = None
    target = None
    sl = None
    quantity = None

    for i in range(3, len(day)):

        candle = day.iloc[i]

        # ==========================================
        # ENTRY
        # ==========================================

        if not trade_taken:

            if candle["Close"] > range_high:

                direction = "LONG"

                entry = float(candle["Close"])

                target = entry * (1 + 0.52 / 100)

                sl = entry * (1 - 0.49 / 100)

                quantity = (capital * LEVERAGE) / entry

                trade_taken = True

                continue

            elif candle["Close"] < range_low:

                direction = "SHORT"

                entry = float(candle["Close"])

                target = entry * (1 - 0.53 / 100)

                sl = entry * (1 + 0.49 / 100)

                quantity = (capital * LEVERAGE) / entry

                trade_taken = True

                continue

        if trade_taken:

            exit_price = None

            pnl = None

            result = None

            if direction == "LONG":

                if candle["Low"] <= sl:

                    exit_price = sl

                    pnl = (
                        (exit_price - entry)
                        * quantity
                    )

                    result = "SL"

                elif candle["Close"] >= target:

                    exit_price = float(candle["Close"])

                    pnl = (
                        (exit_price - entry)
                        * quantity
                    )

                    result = "TARGET"

            else:

                if candle["High"] >= sl:

                    exit_price = sl

                    pnl = (
                        (entry - exit_price)
                        * quantity
                    )

                    result = "SL"

                elif candle["Close"] <= target:

                    exit_price = float(candle["Close"])

                    pnl = (
                        (entry - exit_price)
                        * quantity
                    )

                    result = "TARGET"

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

                result = "EOD"

            if exit_price is not None:

                pnl -= BROKERAGE_PER_TRADE

                return {
                    "Direction": direction,
                    "Entry": round(entry, 2),
                    "Exit": round(exit_price, 2),
                    "Quantity": round(quantity, 2),
                    "PnL": round(pnl, 2),
                    "Result": result
                }

    return None

# =====================================================
# DAILY LOOP
# =====================================================

for day_index, current_day in enumerate(common_days):

    print(f"\nProcessing {current_day}")

    today_results = []

    # ==========================================
    # RUN STRATEGY ON EVERY STOCK
    # ==========================================

    for symbol in STOCKS:

        df = stock_data[symbol]

        day = df[
            df["DateOnly"] == current_day
        ].copy()

        trade = simulate_day(day)

        if trade is None:
            continue

        trade["Stock"] = symbol
        trade["Date"] = current_day

        today_results.append(trade)

    if len(today_results) == 0:
        continue


    # ==========================================
    # FIND TODAY'S WINNER
    # ==========================================

    winner = max(
        today_results,
        key=lambda x: x["PnL"]
    )

    winner_history.append({

        "Date": current_day,

        "Winner": winner["Stock"],

        "PnL": winner["PnL"]

    })

    # ==========================================
    # FIRST DAY
    # NO PREVIOUS WINNER
    # ==========================================

    if previous_day_winner is None:

        previous_day_winner = winner

        print(
            f"Today's Winner : {winner['Stock']} "
            f"({winner['PnL']:.2f})"
        )

        continue

    # ==========================================
    # TRADE YESTERDAY'S WINNER
    # ==========================================

    traded_stock = previous_day_winner["Stock"]

    trade_today = None

    for trade in today_results:

        if trade["Stock"] == traded_stock:

            trade_today = trade

            break

    if trade_today is not None:

        capital += trade_today["PnL"]

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

        if drawdown > max_drawdown:

            max_drawdown = drawdown

        portfolio_trades.append({

            "Date": current_day,

            "Stock": traded_stock,

            "Direction": trade_today["Direction"],

            "Entry": trade_today["Entry"],

            "Exit": trade_today["Exit"],

            "Quantity": trade_today["Quantity"],

            "PnL": trade_today["PnL"],

            "Capital": round(capital, 2),

            "Drawdown%": round(drawdown, 2),

            "Result": trade_today["Result"]

        })

        print(
            f"Traded : {traded_stock} | "
            f"PnL : {trade_today['PnL']:.2f}"
        )

    # ==========================================
    # UPDATE WINNER
    # ==========================================

    previous_day_winner = winner

    print(
        f"Today's Winner : {winner['Stock']} "
        f"({winner['PnL']:.2f})"
    )

# =====================================================
# FINAL DATAFRAME
# =====================================================

trades_df = pd.DataFrame(portfolio_trades)

if trades_df.empty:

    print("\nNo trades were generated.")

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

    eod = len(
        month_df[
            month_df["Result"] == "EOD"
        ]
    )

    completed = wins + losses

    if completed > 0:

        win_rate = (
            wins / completed
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

    print(
        f"Starting Capital : {starting_capital:.2f}"
    )

    print(
        f"Ending Capital   : {ending_capital:.2f}"
    )

    print(
        f"Monthly Return   : {monthly_return:.2f}%"
    )

    print(
        f"Total Trades     : {total_trades}"
    )

    print(
        f"Winning Trades   : {wins}"
    )

    print(
        f"Losing Trades    : {losses}"
    )

    print(
        f"EOD Exits        : {eod}"
    )

    print(
        f"Win Rate         : {win_rate:.2f}%"
    )

    print(
        f"Max Drawdown     : {month_dd:.2f}%"
    )

# =====================================================
# OVERALL METRICS
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

completed = wins + losses

if completed > 0:

    win_rate = (

        wins

        /

        completed

    ) * 100

else:

    win_rate = 0

print("\n")

print("=" * 150)

print("PORTFOLIO RESULTS")

print("=" * 150)

print(trades_df)

print("\n")

print("=" * 150)

print(
    "Initial Capital :",
    round(INITIAL_CAPITAL, 2)
)

print(
    "Leverage :",
    f"{LEVERAGE}x"
)

print(
    "Effective Capital :",
    round(effective_capital, 2)
)

print(
    "Final Capital :",
    round(capital, 2)
)

print(
    "Total Return :",
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
    ),
    "%"
)

print(
    "Max Drawdown :",
    round(max_drawdown, 2),
    "%"
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
# SAVE CSV
# =====================================================

trades_df.to_csv(

    "portfolio_backtest.csv",

    index=False

)

print("\nPortfolio CSV saved successfully.")