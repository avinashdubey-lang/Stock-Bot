import yfinance as yf
import pandas as pd

# =====================================================
# SETTINGS
# =====================================================

STOCKS = [

    "BHARTIARTL.NS"

]

PERIOD = "7d"
INTERVAL = "15m"

TARGET_PERCENT = 0.5
SL_PERCENT = 0.5

INITIAL_CAPITAL = 2000

# =====================================================
# FINAL SUMMARY
# =====================================================

summary = []

# =====================================================
# MAIN LOOP
# =====================================================

for SYMBOL in STOCKS:

    print(f"\nTesting {SYMBOL}...")

    try:

        # =============================================
        # DOWNLOAD DATA
        # =============================================

        df = yf.download(

            SYMBOL,

            period=PERIOD,

            interval=INTERVAL,

            auto_adjust=True,

            progress=False

        )

        df.dropna(inplace=True)

        if len(df) == 0:
            continue


        # =============================================
        # FIX MULTIINDEX
        # =============================================

        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = (
                df.columns
                .get_level_values(0)
            )


        df.reset_index(inplace=True)


        # =============================================
        # FIND DATETIME COLUMN
        # =============================================

        time_col = None

        for col in df.columns:

            if (
                "Date" in str(col)
                or
                "Datetime" in str(col)
            ):

                time_col = col
                break


        if time_col is None:
            continue


        # =============================================
        # CREATE DATE COLUMN
        # =============================================

        df["DateOnly"] = pd.to_datetime(
            df[time_col]
        ).dt.date


        trade_log = []

        days = df["DateOnly"].unique()


        # =============================================
        # DAILY LOOP
        # =============================================

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


            # =========================================
            # RANGE CREATION
            # Ignore first candle
            # Use 2nd and 3rd candle
            # =========================================

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


            # =========================================
            # INTRADAY LOOP
            # =========================================

            for i in range(3, len(day)):

                candle = day.iloc[i]


                # =====================================
                # ENTRY
                # =====================================

                if not trade_taken:


                    # LONG BREAKOUT

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

                        trade_taken = True

                        continue


                    # SHORT BREAKOUT

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

                        trade_taken = True

                        continue


                # =====================================
                # TRADE MANAGEMENT
                # =====================================

                if trade_taken:

                    exit_price = None
                    pnl = None


                    # =================================
                    # LONG TRADE
                    # =================================

                    if direction == "LONG":

                        # Stoploss immediate touch

                        if candle["Low"] <= sl:

                            exit_price = sl

                            pnl = (
                                exit_price - entry
                            )


                        # Target on candle close

                        elif candle["Close"] >= target:

                            exit_price = float(
                                candle["Close"]
                            )

                            pnl = (
                                exit_price - entry
                            )


                    # =================================
                    # SHORT TRADE
                    # =================================

                    else:

                        if candle["High"] >= sl:

                            exit_price = sl

                            pnl = (
                                entry - exit_price
                            )


                        elif candle["Close"] <= target:

                            exit_price = float(
                                candle["Close"]
                            )

                            pnl = (
                                entry - exit_price
                            )


                    # =================================
                    # SAVE TRADE
                    # =================================

                    if exit_price is not None:

                        trade_log.append(
                            pnl
                        )

                        break


        # =============================================
        # STOCK STATS
        # =============================================

        if len(trade_log) > 0:

            results = pd.Series(
                trade_log
            )


            # =========================================
            # CAPITAL SIMULATION
            # =========================================

            capital = INITIAL_CAPITAL

            highest_capital = INITIAL_CAPITAL

            max_drawdown = 0


            for pnl in results:

                capital += pnl


                # Track highest capital

                if capital > highest_capital:

                    highest_capital = capital


                # Drawdown

                drawdown = (

                    highest_capital
                    -
                    capital

                )

                if drawdown > max_drawdown:

                    max_drawdown = drawdown


            final_capital = capital

            net_profit = (

                final_capital
                -
                INITIAL_CAPITAL

            )

            profit_percent = (

                (net_profit / INITIAL_CAPITAL)

                * 100

            )


            # =========================================
            # BASIC STATS
            # =========================================

            total_trades = len(results)

            wins = len(
                results[
                    results > 0
                ]
            )

            losses = len(
                results[
                    results <= 0
                ]
            )

            win_rate = (
                wins / total_trades
            ) * 100


            # =========================================
            # SAVE SUMMARY
            # =========================================

            summary.append({

                "Stock": SYMBOL,

                "FinalCapital": round(
                    final_capital,
                    2
                ),

                "ProfitPercent": round(
                    profit_percent,
                    2
                ),

                "Drawdown": round(
                    max_drawdown,
                    2
                ),

                "Trades": total_trades,

                "Wins": wins,

                "Losses": losses,

                "WinRate": round(
                    win_rate,
                    2
                )

            })


    except Exception as e:

        print(
            f"Error in {SYMBOL}:",
            e
        )


# =====================================================
# FINAL RESULTS
# =====================================================

summary_df = pd.DataFrame(summary)

summary_df = summary_df.sort_values(

    by="ProfitPercent",

    ascending=False

)

print("\n")
print("="*100)
print("MULTI STOCK BACKTEST RESULTS")
print("="*100)

print(summary_df)

print("\n")
print("="*100)

overall_profit = summary_df[
    "ProfitPercent"
].sum()

print(
    "Overall Profit %:",
    round(overall_profit,2)
)