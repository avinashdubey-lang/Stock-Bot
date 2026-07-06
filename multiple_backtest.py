"""Vande Bharat intraday strategy backtester.

Existing project dependencies:
    login.py
        login_user()

    market_data.py
        get_token(symbol)

    Data_fetcher.py
        get_historical_data(smartApi, symboltoken, interval, days)

    config.py
        STOCKS

Stocks are ranked by the previous day's percentage gain (a temporary proxy for
open interest).  The five highest-ranked stocks are scanned for the first valid
PDH/PDL breakout, one-inside-candle pattern.  Positions use risk-based sizing
and a 10 EMA close-based exit, with a 15:15 square-off.

Candle timestamps are assumed to represent candle opening times.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import time
from pathlib import Path
from typing import Optional

import pandas as pd

from config import STOCKS
from Data_fetcher import get_historical_data
from login import login_user
from market_data import get_token


# =============================================================================
# CONFIGURATION
# =============================================================================

INTERVAL = "FIVE_MINUTE"
HISTORICAL_DAYS = 360

INITIAL_CAPITAL = 14000.0
LEVERAGE = 5.0
RISK_PER_DAY_PERCENT = 1.0
MAXIMUM_TRADES = 1
TOP_STOCK_COUNT = 5
EMA_PERIOD = 10

MARKET_OPEN_TIME = time(9, 15)
ENTRY_START_TIME = time(9, 30)
LAST_CANDLE_TIME = time(15, 15)

# Angel One intraday brokerage assumption:
# 0.03% or ₹20 per executed order, whichever is lower.
# Adjust these values for your actual brokerage plan.
BROKERAGE_RATE = 0.0003
MAX_BROKERAGE_PER_ORDER = 20.0

# Optional simulated slippage on each side.
SLIPPAGE_PERCENT = 0.0

# With OHLC data, the order of target and SL cannot be known when both are hit
# in one candle. Using SL first is the conservative assumption.
OUTPUT_DIRECTORY = Path("backtest_results")
TRADE_LOG_FILE = OUTPUT_DIRECTORY / "trade_log.csv"
CAPITAL_CURVE_FILE = OUTPUT_DIRECTORY / "capital_curve.csv"
MONTHLY_PERFORMANCE_FILE = OUTPUT_DIRECTORY / "monthly_performance.csv"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Trade:
    trade_date: object
    symbol: str
    previous_day_return_pct: float
    opening_gap_pct: float

    direction: str
    range_high: float
    range_low: float

    entry_time: pd.Timestamp
    entry_price: float
    quantity: int
    exposure: float

    target_price: float
    stop_price: float

    exit_time: pd.Timestamp
    exit_price: float
    exit_reason: str

    entry_brokerage: float
    exit_brokerage: float
    total_brokerage: float

    gross_pnl: float
    net_pnl: float
    return_on_capital_pct: float

    capital_before: float
    capital_after: float


@dataclass
class SelectedStock:
    symbol: str
    previous_return_pct: float
    gap_pct: float
    day_data: pd.DataFrame


# Set by run_backtest so the intentionally simple public ranking function can
# later be replaced by an OI data provider without changing the engine.
_ranking_grouped_data: dict[str, dict[object, pd.DataFrame]] = {}


# =============================================================================
# DATA PREPARATION
# =============================================================================

def normalize_historical_data(
    data: pd.DataFrame,
    symbol: str,
) -> pd.DataFrame:
    """Validate and normalize data returned by Data_fetcher."""

    required_columns = {
        "Datetime",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    }

    if data is None or data.empty:
        return pd.DataFrame()

    data = data.copy()

    missing = required_columns.difference(data.columns)
    if missing:
        print(f"Skipping {symbol}: missing columns {sorted(missing)}")
        return pd.DataFrame()

    data["Datetime"] = pd.to_datetime(
        data["Datetime"],
        errors="coerce",
    )

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(
        subset=["Datetime", "Open", "High", "Low", "Close"]
    )

    if data.empty:
        return pd.DataFrame()

    # Convert timezone-aware values to local, timezone-naive timestamps.
    if data["Datetime"].dt.tz is not None:
        data["Datetime"] = (
            data["Datetime"]
            .dt.tz_convert("Asia/Kolkata")
            .dt.tz_localize(None)
        )

    data = (
        data.sort_values("Datetime")
        .drop_duplicates(subset=["Datetime"], keep="last")
        .reset_index(drop=True)
    )

    valid_ohlc = (
        (data["High"] >= data[["Open", "Close", "Low"]].max(axis=1))
        & (data["Low"] <= data[["Open", "Close", "High"]].min(axis=1))
        & (data["Open"] > 0)
        & (data["Close"] > 0)
    )

    invalid_count = int((~valid_ohlc).sum())
    if invalid_count:
        print(f"{symbol}: discarded {invalid_count} invalid candles.")

    data = data.loc[valid_ohlc].copy()

    data["TradeDate"] = data["Datetime"].dt.date
    data["CandleTime"] = data["Datetime"].dt.time

    # Keep only regular market-session candles.
    data = data[
        (data["CandleTime"] >= MARKET_OPEN_TIME)
        & (data["CandleTime"] <= LAST_CANDLE_TIME)
    ].reset_index(drop=True)

    return data


def download_all_stock_data(
    smart_api,
) -> dict[str, pd.DataFrame]:
    """
    Download each stock exactly once.

    The existing project downloader is reused without duplicating its logic.
    """

    stock_data: dict[str, pd.DataFrame] = {}

    for position, symbol in enumerate(STOCKS, start=1):
        print(f"[{position}/{len(STOCKS)}] Downloading {symbol}...")

        try:
            symbol_token = get_token(symbol)

            if symbol_token is None or str(symbol_token).strip() == "":
                print(f"Skipping {symbol}: token not found.")
                continue

            raw_data = get_historical_data(
                smart_api,
                str(symbol_token),
                INTERVAL,
                HISTORICAL_DAYS,
            )

            clean_data = normalize_historical_data(raw_data, symbol)

            if clean_data.empty:
                print(f"Skipping {symbol}: no valid historical candles.")
                continue

            stock_data[symbol] = clean_data

        except Exception as exc:
            print(f"Skipping {symbol}: {exc}")

    return stock_data


def group_data_by_day(
    stock_data: dict[str, pd.DataFrame],
) -> dict[str, dict[object, pd.DataFrame]]:
    """
    Group downloaded data for efficient daily access.

    This avoids repeatedly filtering full DataFrames inside the backtest.
    """

    grouped: dict[str, dict[object, pd.DataFrame]] = {}

    for symbol, data in stock_data.items():
        grouped[symbol] = {
            trade_date: day.reset_index(drop=True)
            for trade_date, day in data.groupby("TradeDate", sort=True)
        }

    return grouped


def get_trading_calendar(
    grouped_data: dict[str, dict[object, pd.DataFrame]],
) -> list:
    """Build a sorted union of all available trading dates."""

    dates = set()

    for symbol_days in grouped_data.values():
        dates.update(symbol_days.keys())

    return sorted(dates)


# =============================================================================
# STOCK SELECTION
# =============================================================================

def get_daily_open_close(
    day_data: pd.DataFrame,
) -> Optional[tuple[float, float]]:
    """Return the regular-session opening price and final closing price."""

    if day_data.empty:
        return None

    day_data = day_data.sort_values("Datetime")

    opening_candle = day_data[
        day_data["CandleTime"] == MARKET_OPEN_TIME
    ]

    if opening_candle.empty:
        return None

    day_open = float(opening_candle.iloc[0]["Open"])
    day_close = float(day_data.iloc[-1]["Close"])

    if day_open <= 0 or day_close <= 0:
        return None

    return day_open, day_close


def get_market_bias(date) -> str:
    """Return LONG, SHORT or BOTH for a date.

    Historical breadth is not available yet.  Keeping this behind a function
    makes a future breadth implementation independent of strategy execution.
    """

    del date
    return "BOTH"


def rank_by_open_interest(date) -> list[tuple[str, float, float]]:
    """Return the Top 5 stocks using previous-day gain as the OI proxy.

    Each tuple contains symbol, previous-day percentage gain and previous
    close.  Unlike the old momentum filter, negative returns are retained so
    that the universe still has a complete descending ranking.
    """

    rankings = []

    for symbol, symbol_days in _ranking_grouped_data.items():
        prior_dates = sorted(day for day in symbol_days if day < date)
        if not prior_dates:
            continue

        previous_data = symbol_days[prior_dates[-1]]
        prices = get_daily_open_close(previous_data)
        if prices is None:
            continue

        previous_open, previous_close = prices
        gain_pct = (previous_close - previous_open) / previous_open * 100.0
        rankings.append((symbol, gain_pct, previous_close))

    rankings.sort(key=lambda item: item[1], reverse=True)
    return rankings[:TOP_STOCK_COUNT]


def select_stocks_for_day(
    grouped_data: dict[str, dict[object, pd.DataFrame]],
    current_date,
) -> list[SelectedStock]:
    """Build daily inputs for every available stock in the Top 5 ranking."""

    selected = []
    for symbol, previous_return, previous_close in rank_by_open_interest(
        current_date
    ):
        current_data = grouped_data[symbol].get(current_date)
        if current_data is None or current_data.empty or previous_close <= 0:
            continue

        current_data = current_data.sort_values("Datetime").reset_index(drop=True)
        opening = current_data[
            current_data["CandleTime"] == MARKET_OPEN_TIME
        ]
        if opening.empty:
            continue

        gap_pct = (
            (float(opening.iloc[0]["Open"]) - previous_close)
            / previous_close
            * 100.0
        )
        selected.append(SelectedStock(
            symbol=symbol,
            previous_return_pct=previous_return,
            gap_pct=gap_pct,
            day_data=current_data,
        ))

    return selected


# =============================================================================
# TRADE EXECUTION
# =============================================================================

def calculate_brokerage(price: float, quantity: int) -> float:
    """Calculate brokerage for one executed order."""

    turnover = price * quantity
    return min(turnover * BROKERAGE_RATE, MAX_BROKERAGE_PER_ORDER)


def apply_entry_slippage(price: float, direction: str) -> float:
    """Apply unfavorable entry slippage."""

    slippage = SLIPPAGE_PERCENT / 100.0

    if direction == "LONG":
        return price * (1.0 + slippage)

    return price * (1.0 - slippage)


def apply_exit_slippage(price: float, direction: str) -> float:
    """Apply unfavorable exit slippage."""

    slippage = SLIPPAGE_PERCENT / 100.0

    if direction == "LONG":
        return price * (1.0 - slippage)

    return price * (1.0 + slippage)


def get_previous_day_levels(
    grouped_data: dict[str, dict[object, pd.DataFrame]],
    symbol: str,
    current_date,
) -> Optional[tuple[float, float]]:
    """Return the immediately preceding available session's PDH and PDL."""

    symbol_days = grouped_data.get(symbol, {})
    prior_dates = sorted(day for day in symbol_days if day < current_date)
    if not prior_dates:
        return None

    previous_data = symbol_days[prior_dates[-1]]
    return float(previous_data["High"].max()), float(previous_data["Low"].min())


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_price: float,
) -> int:
    """Size by configured risk, capped by leveraged available capital."""

    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0

    risk_per_day = capital * RISK_PER_DAY_PERCENT / 100.0
    risk_per_trade = risk_per_day / MAXIMUM_TRADES
    risk_quantity = math.floor(risk_per_trade / risk_per_share)
    capital_quantity = math.floor(capital * LEVERAGE / entry_price)
    return max(0, min(risk_quantity, capital_quantity))


def find_entry_signal(
    day_data: pd.DataFrame,
    previous_high: float,
    previous_low: float,
    market_bias: str,
) -> Optional[dict]:
    """Find the first breakout -> one inside candle -> price-break signal."""

    scan = day_data[
        (day_data["CandleTime"] >= ENTRY_START_TIME)
        & (day_data["CandleTime"] < LAST_CANDLE_TIME)
    ]

    signals = []
    for offset in range(len(scan) - 1):
        breakout = scan.iloc[offset]
        inside = scan.iloc[offset + 1]

        is_inside = (
            float(inside["High"]) <= float(breakout["High"])
            and float(inside["Low"]) >= float(breakout["Low"])
            and float(inside["Volume"]) < float(breakout["Volume"])
        )
        if not is_inside:
            continue

        direction = None
        trigger_level = None
        stop_price = None

        if (
            market_bias in {"LONG", "BOTH"}
            and float(breakout["Close"]) > previous_high
            and float(inside["Close"]) < float(inside["Open"])
        ):
            direction = "LONG"
            trigger_level = float(inside["High"])
            stop_price = float(inside["Low"])
        elif (
            market_bias in {"SHORT", "BOTH"}
            and float(breakout["Close"]) < previous_low
            and float(inside["Close"]) > float(inside["Open"])
        ):
            direction = "SHORT"
            trigger_level = float(inside["Low"])
            stop_price = float(inside["High"])

        if direction is None:
            continue

        # Once the required single inside candle has formed, wait for its
        # level to break; it need not happen in the very next candle.
        for trigger_offset in range(offset + 2, len(scan)):
            trigger = scan.iloc[trigger_offset]
            level_broken = (
                float(trigger["High"]) > trigger_level
                if direction == "LONG"
                else float(trigger["Low"]) < trigger_level
            )
            if not level_broken:
                continue

            entry = (
                max(float(trigger["Open"]), trigger_level)
                if direction == "LONG"
                else min(float(trigger["Open"]), trigger_level)
            )
            signals.append({
                "index": trigger.name,
                "direction": direction,
                "entry_price": entry,
                "stop_price": stop_price,
                "time": trigger["Datetime"],
            })
            break

    return min(signals, key=lambda signal: signal["time"]) if signals else None


def execute_strategy(
    selected: SelectedStock,
    capital: float,
    previous_high: float,
    previous_low: float,
    market_bias: str,
) -> Optional[Trade]:
    """Execute one Vande Bharat signal and manage it using SL/EMA/EOD."""

    day_data = selected.day_data.copy()
    day_data["EMA10"] = day_data["Close"].ewm(
        span=EMA_PERIOD, adjust=False
    ).mean()
    signal = find_entry_signal(
        day_data, previous_high, previous_low, market_bias
    )
    if signal is None:
        return None

    entry_index = signal["index"]
    direction = signal["direction"]
    entry_candle = day_data.loc[entry_index]
    entry_price = apply_entry_slippage(signal["entry_price"], direction)
    stop_price = signal["stop_price"]
    quantity = calculate_position_size(capital, entry_price, stop_price)
    if quantity <= 0:
        return None

    exposure = entry_price * quantity
    target_price = float("nan")

    exit_price = None
    exit_reason = None
    exit_time = None

    subsequent_candles = day_data.loc[entry_index + 1:]

    for _, candle in subsequent_candles.iterrows():
        candle_open = float(candle["Open"])
        candle_close = float(candle["Close"])
        ema = float(candle["EMA10"])

        if candle["CandleTime"] >= LAST_CANDLE_TIME:
            raw_exit = candle_close
            exit_reason = "END_OF_DAY"
        elif direction == "LONG" and float(candle["Low"]) <= stop_price:
            raw_exit = min(candle_open, stop_price)
            exit_reason = "STOP_LOSS"
        elif direction == "SHORT" and float(candle["High"]) >= stop_price:
            raw_exit = max(candle_open, stop_price)
            exit_reason = "STOP_LOSS"
        elif direction == "LONG" and candle_close < ema:
            raw_exit = float(candle["Low"])
            exit_reason = "EMA_EXIT"
        elif direction == "SHORT" and candle_close > ema:
            raw_exit = float(candle["High"])
            exit_reason = "EMA_EXIT"
        else:
            continue

        exit_price = apply_exit_slippage(raw_exit, direction)
        exit_time = candle["Datetime"]
        break

    if exit_price is None:
        final_candle = day_data.iloc[-1]
        exit_price = apply_exit_slippage(
            float(final_candle["Close"]),
            direction,
        )
        exit_reason = "END_OF_DAY"
        exit_time = final_candle["Datetime"]

    if direction == "LONG":
        gross_pnl = (exit_price - entry_price) * quantity
    else:
        gross_pnl = (entry_price - exit_price) * quantity

    entry_brokerage = calculate_brokerage(entry_price, quantity)
    exit_brokerage = calculate_brokerage(exit_price, quantity)
    total_brokerage = entry_brokerage + exit_brokerage

    net_pnl = gross_pnl - total_brokerage
    capital_after = capital + net_pnl

    return Trade(
        trade_date=entry_candle["TradeDate"],
        symbol=selected.symbol,
        previous_day_return_pct=selected.previous_return_pct,
        opening_gap_pct=selected.gap_pct,
        direction=direction,
        range_high=previous_high,
        range_low=previous_low,
        entry_time=entry_candle["Datetime"],
        entry_price=entry_price,
        quantity=quantity,
        exposure=exposure,
        target_price=target_price,
        stop_price=stop_price,
        exit_time=exit_time,
        exit_price=exit_price,
        exit_reason=exit_reason,
        entry_brokerage=entry_brokerage,
        exit_brokerage=exit_brokerage,
        total_brokerage=total_brokerage,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        return_on_capital_pct=(net_pnl / capital) * 100.0,
        capital_before=capital,
        capital_after=capital_after,
    )


# =============================================================================
# BACKTEST
# =============================================================================

def run_backtest(
    grouped_data: dict[str, dict[object, pd.DataFrame]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run stock selection and trading chronologically."""

    global _ranking_grouped_data
    _ranking_grouped_data = grouped_data

    calendar = get_trading_calendar(grouped_data)
    capital = INITIAL_CAPITAL
    trades: list[Trade] = []

    capital_records = [{
        "Date": None,
        "Capital": capital,
        "DailyPnL": 0.0,
        "Symbol": None,
    }]

    for position in range(1, len(calendar)):
        current_date = calendar[position]
        market_bias = get_market_bias(current_date)
        selected_stocks = select_stocks_for_day(grouped_data, current_date)

        daily_pnl = 0.0
        traded_symbol = None

        # Evaluate all Top 5 independently, then take the earliest valid entry.
        # Stable sorting makes ranking order the tie-breaker.
        candidates = []
        for rank, selected in enumerate(selected_stocks):
            levels = get_previous_day_levels(
                grouped_data, selected.symbol, current_date
            )
            if levels is None:
                continue

            trade = execute_strategy(
                selected,
                capital,
                previous_high=levels[0],
                previous_low=levels[1],
                market_bias=market_bias,
            )
            if trade is not None:
                candidates.append((trade.entry_time, rank, trade))

        if candidates:
            _, _, trade = min(candidates, key=lambda item: (item[0], item[1]))
            trades.append(trade)
            capital = trade.capital_after
            daily_pnl = trade.net_pnl
            traded_symbol = trade.symbol

        capital_records.append({
            "Date": current_date,
            "Capital": capital,
            "DailyPnL": daily_pnl,
            "Symbol": traded_symbol,
        })

    trade_log = pd.DataFrame([asdict(trade) for trade in trades])
    capital_curve = pd.DataFrame(capital_records)

    return trade_log, capital_curve


# =============================================================================
# PERFORMANCE STATISTICS
# =============================================================================

def calculate_monthly_performance(
    capital_curve: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate monthly P&L and return from the daily capital curve."""

    daily = capital_curve.dropna(subset=["Date"]).copy()

    if daily.empty:
        return pd.DataFrame()

    daily["Date"] = pd.to_datetime(daily["Date"])
    daily["Month"] = daily["Date"].dt.to_period("M").astype(str)

    monthly_rows = []

    for month, group in daily.groupby("Month", sort=True):
        group = group.sort_values("Date")

        ending_capital = float(group.iloc[-1]["Capital"])
        monthly_pnl = float(group["DailyPnL"].sum())
        starting_capital = ending_capital - monthly_pnl

        monthly_return = (
            monthly_pnl / starting_capital * 100.0
            if starting_capital != 0
            else 0.0
        )

        monthly_rows.append({
            "Month": month,
            "StartingCapital": starting_capital,
            "EndingCapital": ending_capital,
            "NetPnL": monthly_pnl,
            "ReturnPct": monthly_return,
            "Trades": int((group["Symbol"].notna()).sum()),
        })

    return pd.DataFrame(monthly_rows)


def calculate_statistics(
    trade_log: pd.DataFrame,
    capital_curve: pd.DataFrame,
) -> dict:
    """Calculate requested portfolio-level metrics."""

    if trade_log.empty:
        return {
            "Total Trades": 0,
            "Win Rate (%)": 0.0,
            "Gross Profit": 0.0,
            "Gross Loss": 0.0,
            "Profit Factor": 0.0,
            "Maximum Drawdown": 0.0,
            "Maximum Drawdown (%)": 0.0,
            "Total Return (%)": 0.0,
            "Final Capital": INITIAL_CAPITAL,
        }

    net_pnl = trade_log["net_pnl"].astype(float)
    winning_pnl = net_pnl[net_pnl > 0]
    losing_pnl = net_pnl[net_pnl < 0]

    gross_profit = float(winning_pnl.sum())
    gross_loss = abs(float(losing_pnl.sum()))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    equity = capital_curve["Capital"].astype(float)
    running_peak = equity.cummax()
    drawdown = running_peak - equity

    drawdown_pct = (
        drawdown.div(running_peak.replace(0, pd.NA)) * 100.0
    ).fillna(0.0)

    final_capital = float(equity.iloc[-1])

    return {
        "Total Trades": len(trade_log),
        "Win Rate (%)": float((net_pnl > 0).mean() * 100.0),
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss,
        "Profit Factor": profit_factor,
        "Maximum Drawdown": float(drawdown.max()),
        "Maximum Drawdown (%)": float(drawdown_pct.max()),
        "Total Return (%)": (
            (final_capital - INITIAL_CAPITAL)
            / INITIAL_CAPITAL
            * 100.0
        ),
        "Final Capital": final_capital,
    }


def print_statistics(statistics: dict) -> None:
    """Print a readable performance report."""

    profit_factor = statistics["Profit Factor"]

    if math.isinf(profit_factor):
        profit_factor_text = "Infinity"
    else:
        profit_factor_text = f"{profit_factor:.2f}"

    print("\n" + "=" * 62)
    print("STOCK SELECTION + RANGE BREAKOUT BACKTEST")
    print("=" * 62)
    print(f"Initial Capital       : ₹{INITIAL_CAPITAL:,.2f}")
    print(f"Final Capital         : ₹{statistics['Final Capital']:,.2f}")
    print(f"Total Trades          : {statistics['Total Trades']}")
    print(f"Win Rate              : {statistics['Win Rate (%)']:.2f}%")
    print(f"Gross Profit          : ₹{statistics['Gross Profit']:,.2f}")
    print(f"Gross Loss            : ₹{statistics['Gross Loss']:,.2f}")
    print(f"Profit Factor         : {profit_factor_text}")
    print(f"Maximum Drawdown      : ₹{statistics['Maximum Drawdown']:,.2f}")
    print(
        f"Maximum Drawdown      : "
        f"{statistics['Maximum Drawdown (%)']:.2f}%"
    )
    print(f"Total Return          : {statistics['Total Return (%)']:.2f}%")
    print("=" * 62)


def export_results(
    trade_log: pd.DataFrame,
    capital_curve: pd.DataFrame,
    monthly_performance: pd.DataFrame,
) -> None:
    """Export all backtest reports."""

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    trade_log.to_csv(TRADE_LOG_FILE, index=False)
    capital_curve.to_csv(CAPITAL_CURVE_FILE, index=False)
    monthly_performance.to_csv(
        MONTHLY_PERFORMANCE_FILE,
        index=False,
    )

    print(f"\nTrade log saved to: {TRADE_LOG_FILE.resolve()}")
    print(f"Capital curve saved to: {CAPITAL_CURVE_FILE.resolve()}")
    print(
        "Monthly performance saved to: "
        f"{MONTHLY_PERFORMANCE_FILE.resolve()}"
    )


# =============================================================================
# MAIN
# =============================================================================

def validate_configuration() -> None:
    """Fail early when configuration is invalid."""

    if not STOCKS:
        raise ValueError("config.STOCKS is empty.")

    if INITIAL_CAPITAL <= 0:
        raise ValueError("INITIAL_CAPITAL must be greater than zero.")

    if LEVERAGE <= 0:
        raise ValueError("LEVERAGE must be greater than zero.")

    if RISK_PER_DAY_PERCENT <= 0:
        raise ValueError("RISK_PER_DAY_PERCENT must be greater than zero.")

    if MAXIMUM_TRADES <= 0:
        raise ValueError("MAXIMUM_TRADES must be greater than zero.")

    if EMA_PERIOD <= 0 or TOP_STOCK_COUNT <= 0:
        raise ValueError("EMA_PERIOD and TOP_STOCK_COUNT must be positive.")


def main() -> None:
    validate_configuration()

    print("Logging in to Angel One SmartAPI...")
    smart_api = login_user()[0]

    if smart_api is None:
        raise RuntimeError("login_user() did not return a SmartAPI client.")

    stock_data = download_all_stock_data(smart_api)

    if not stock_data:
        raise RuntimeError(
            "No historical data was downloaded for any configured stock."
        )

    print(
        f"\nLoaded historical data for "
        f"{len(stock_data)}/{len(STOCKS)} stocks."
    )

    grouped_data = group_data_by_day(stock_data)

    trade_log, capital_curve = run_backtest(grouped_data)
    monthly_performance = calculate_monthly_performance(capital_curve)
    statistics = calculate_statistics(trade_log, capital_curve)

    print_statistics(statistics)
    export_results(
        trade_log,
        capital_curve,
        monthly_performance,
    )


if __name__ == "__main__":
    main()
