"""Intraday VWAP + traditional pivot-point portfolio backtester.

Historical candles are downloaded exclusively through the project's Angel One
SmartAPI helpers. Candle timestamps are assumed to be candle opening times.
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

DAYS = 360
INTERVAL = "FIVE_MINUTE"
INITIAL_CAPITAL = 10000.0
RISK_PER_TRADE_PERCENT = 1.0
BROKERAGE = 20.0  # Flat brokerage per executed order; set to actual plan.
MAX_TRADES_PER_DAY = 1
LEVERAGE = 5.0

# Supported values: "IMMEDIATE" or "PULLBACK".
ENTRY_MODE = "IMMEDIATE"
TARGET_MODE = "NEXT_PIVOT"  # Supported: "NEXT_PIVOT" or "TREND".

MIN_BREAKOUT_BODY_RATIO = 0.40
MIN_BREAKOUT_DISTANCE_PERCENT = 0.10
MIN_ENTRY_BODY_RATIO = 0.30
DOJI_BODY_RATIO = 0.10
MAX_OPPOSITE_WICK_BODY_RATIO = 1.50

USE_VOLUME_FILTER = True
VOLUME_MODE = "PREVIOUS"  # Supported: "PREVIOUS" or "EMA20".
VOLUME_EMA_PERIOD = 20

# Fixed point/tick distance below or above the entry pivot.
STOP_BUFFER_POINTS = 0.10
MARKET_OPEN = time(9, 15)
LAST_ENTRY_TIME = time(13, 30)
SQUARE_OFF_TIME = time(15, 15)

OUTPUT_DIRECTORY = Path("vwap_pivot_backtest_results")
TRADE_LOG_FILE = OUTPUT_DIRECTORY / "trade_log.csv"
CAPITAL_CURVE_FILE = OUTPUT_DIRECTORY / "capital_curve.csv"
MONTHLY_PERFORMANCE_FILE = OUTPUT_DIRECTORY / "monthly_performance.csv"


# =============================================================================
# DOMAIN OBJECTS
# =============================================================================

@dataclass(frozen=True)
class PivotLevels:
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float

    def resistance_chain(self) -> tuple[tuple[str, float, Optional[float]], ...]:
        return (("PP", self.pivot, self.r1), ("R1", self.r1, self.r2),
                ("R2", self.r2, self.r3), ("R3", self.r3, None))

    def support_chain(self) -> tuple[tuple[str, float, Optional[float]], ...]:
        return (("PP", self.pivot, self.s1), ("S1", self.s1, self.s2),
                ("S2", self.s2, self.s3), ("S3", self.s3, None))


@dataclass(frozen=True)
class EntrySignal:
    symbol: str
    trade_date: object
    candle_index: int
    entry_time: pd.Timestamp
    direction: str
    entry_price: float
    pivot_name: str
    pivot_price: float
    stop_price: float
    target_price: Optional[float]
    vwap: float
    entry_mode: str


@dataclass
class Trade:
    trade_date: object
    symbol: str
    direction: str
    pivot_name: str
    pivot_price: float
    entry_mode: str
    entry_time: pd.Timestamp
    entry_price: float
    vwap_at_entry: float
    stop_price: float
    target_price: Optional[float]
    quantity: int
    exposure: float
    planned_risk: float
    exit_time: pd.Timestamp
    exit_price: float
    exit_reason: str
    gross_pnl: float
    brokerage: float
    net_pnl: float
    r_multiple: float
    capital_before: float
    capital_after: float


# =============================================================================
# DATA PREPARATION AND INDICATORS
# =============================================================================

def normalize_historical_data(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Validate downloader output and retain regular-session candles only."""

    required = {"Datetime", "Open", "High", "Low", "Close", "Volume"}
    if data is None or data.empty:
        return pd.DataFrame()

    data = data.copy()
    missing = required.difference(data.columns)
    if missing:
        print(f"Skipping {symbol}: missing columns {sorted(missing)}")
        return pd.DataFrame()

    data["Datetime"] = pd.to_datetime(data["Datetime"], errors="coerce")
    for column in ("Open", "High", "Low", "Close", "Volume"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=list(required)).copy()
    if data.empty:
        return data

    if data["Datetime"].dt.tz is not None:
        data["Datetime"] = (
            data["Datetime"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        )

    data = (data.sort_values("Datetime")
            .drop_duplicates("Datetime", keep="last")
            .reset_index(drop=True))
    valid = (
        (data["Open"] > 0)
        & (data["Close"] > 0)
        & (data["Volume"] >= 0)
        & (data["High"] >= data[["Open", "Close", "Low"]].max(axis=1))
        & (data["Low"] <= data[["Open", "Close", "High"]].min(axis=1))
    )
    invalid_count = int((~valid).sum())
    if invalid_count:
        print(f"{symbol}: discarded {invalid_count} invalid candles.")
    data = data.loc[valid].copy()
    data["TradeDate"] = data["Datetime"].dt.date
    data["CandleTime"] = data["Datetime"].dt.time
    return data[
        (data["CandleTime"] >= MARKET_OPEN)
        & (data["CandleTime"] <= SQUARE_OFF_TIME)
    ].reset_index(drop=True)


def add_intraday_vwap(day_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate session-reset VWAP for one trading day."""

    result = day_data.sort_values("Datetime").reset_index(drop=True).copy()
    typical_price = (result["High"] + result["Low"] + result["Close"]) / 3.0
    cumulative_volume = result["Volume"].cumsum()
    result["VWAP"] = (
        (typical_price * result["Volume"]).cumsum()
        .div(cumulative_volume.replace(0, float("nan")))
    )
    result["VolumeEMA20"] = result["Volume"].ewm(
        span=VOLUME_EMA_PERIOD, adjust=False
    ).mean()
    return result


def calculate_pivot_levels(previous_day: pd.DataFrame) -> PivotLevels:
    """Calculate traditional pivots from the previous regular session."""

    previous_high = float(previous_day["High"].max())
    previous_low = float(previous_day["Low"].min())
    previous_close = float(
        previous_day.sort_values("Datetime").iloc[-1]["Close"]
    )
    pivot = (previous_high + previous_low + previous_close) / 3.0
    return PivotLevels(
        pivot=pivot,
        r1=2.0 * pivot - previous_low,
        r2=pivot + (previous_high - previous_low),
        r3=previous_high + 2.0 * (pivot - previous_low),
        s1=2.0 * pivot - previous_high,
        s2=pivot - (previous_high - previous_low),
        s3=previous_low - 2.0 * (previous_high - pivot),
    )


def download_all_data(smart_api) -> dict[str, pd.DataFrame]:
    """Download the complete watchlist before any backtest processing."""

    downloaded = {}
    for number, symbol in enumerate(STOCKS, start=1):
        print(f"[{number}/{len(STOCKS)}] Downloading {symbol}...")
        try:
            symboltoken = get_token(symbol)
            if symboltoken is None or not str(symboltoken).strip():
                print(f"Skipping {symbol}: token not found.")
                continue
            raw = get_historical_data(
                smartApi=smart_api,
                symboltoken=str(symboltoken),
                interval=INTERVAL,
                days=DAYS,
            )
            clean = normalize_historical_data(raw, symbol)
            if clean.empty:
                print(f"Skipping {symbol}: no valid candles.")
                continue
            downloaded[symbol] = clean
        except Exception as exc:
            print(f"Skipping {symbol}: {exc}")
    return downloaded


def group_data_by_day(
    stock_data: dict[str, pd.DataFrame],
) -> dict[str, dict[object, pd.DataFrame]]:
    return {
        symbol: {
            trade_date: day.sort_values("Datetime").reset_index(drop=True)
            for trade_date, day in data.groupby("TradeDate", sort=True)
        }
        for symbol, data in stock_data.items()
    }


# =============================================================================
# ISOLATED STRATEGY LOGIC
# =============================================================================

class VwapPivotStrategy:
    """Generate entries only; portfolio sizing and exits belong to the engine."""

    def __init__(self, entry_mode: str, stop_buffer_points: float) -> None:
        self.entry_mode = entry_mode.upper()
        self.stop_buffer = stop_buffer_points

    def generate_signals(
        self,
        symbol: str,
        day_data: pd.DataFrame,
        pivots: PivotLevels,
    ) -> list[EntrySignal]:
        prepared = add_intraday_vwap(day_data)
        if self.entry_mode == "IMMEDIATE":
            signals = self._immediate_signals(symbol, prepared, pivots)
        else:
            signals = self._pullback_signals(symbol, prepared, pivots)

        # A pivot can produce only one entry candidate per symbol/day. If a
        # gap candle crosses several pivots at once, use the furthest broken
        # level so the selected target always remains beyond the entry pivot.
        unique = {}
        for signal in sorted(signals, key=lambda item: item.entry_time):
            unique.setdefault((signal.direction, signal.pivot_name), signal)
        by_time = {}
        for signal in unique.values():
            key = (signal.entry_time, signal.direction)
            existing = by_time.get(key)
            if existing is None:
                by_time[key] = signal
            elif (
                signal.direction == "LONG"
                and signal.pivot_price > existing.pivot_price
            ):
                by_time[key] = signal
            elif (
                signal.direction == "SHORT"
                and signal.pivot_price < existing.pivot_price
            ):
                by_time[key] = signal
        return sorted(by_time.values(), key=lambda item: item.entry_time)

    @staticmethod
    def _crossed(candle: pd.Series, previous: Optional[pd.Series], level: float,
                 direction: str) -> bool:
        """Require an intraday candle to trade through a level, not gap over it."""

        del previous  # The candle's own open-to-close path is gap-safe.
        if direction == "LONG":
            return (
                float(candle["Open"]) <= level < float(candle["Close"])
            )
        return (
            float(candle["Open"]) >= level > float(candle["Close"])
        )

    @staticmethod
    def _candle_parts(candle: pd.Series) -> tuple[float, float, float, float]:
        candle_open = float(candle["Open"])
        candle_close = float(candle["Close"])
        body = abs(candle_close - candle_open)
        candle_range = float(candle["High"]) - float(candle["Low"])
        upper_wick = float(candle["High"]) - max(candle_open, candle_close)
        lower_wick = min(candle_open, candle_close) - float(candle["Low"])
        return body, candle_range, upper_wick, lower_wick

    def _volume_confirmed(
        self,
        data: pd.DataFrame,
        index: int,
    ) -> bool:
        if not USE_VOLUME_FILTER:
            return True
        volume = float(data.iloc[index]["Volume"])
        if VOLUME_MODE == "PREVIOUS":
            return index > 0 and volume > float(data.iloc[index - 1]["Volume"])
        return volume > float(data.iloc[index]["VolumeEMA20"])

    def _breakout_is_strong(
        self,
        data: pd.DataFrame,
        index: int,
        level: float,
        direction: str,
    ) -> bool:
        candle = data.iloc[index]
        body, candle_range, _, _ = self._candle_parts(candle)
        if candle_range <= 0 or level <= 0:
            return False
        body_ratio = body / candle_range
        close = float(candle["Close"])
        distance_pct = (
            (close - level) / level * 100.0
            if direction == "LONG"
            else (level - close) / level * 100.0
        )
        momentum_valid = (
            body_ratio >= MIN_BREAKOUT_BODY_RATIO
            or distance_pct >= MIN_BREAKOUT_DISTANCE_PERCENT
        )
        return momentum_valid and self._volume_confirmed(data, index)

    def _entry_candle_is_valid(
        self,
        candle: pd.Series,
        direction: str,
    ) -> bool:
        body, candle_range, upper_wick, lower_wick = self._candle_parts(candle)
        if candle_range <= 0:
            return False
        body_ratio = body / candle_range
        if body_ratio < MIN_ENTRY_BODY_RATIO or body_ratio <= DOJI_BODY_RATIO:
            return False
        opposite_wick = upper_wick if direction == "LONG" else lower_wick
        return opposite_wick <= body * MAX_OPPOSITE_WICK_BODY_RATIO

    def _is_rejection_candle(
        self,
        candle: pd.Series,
        level: float,
        direction: str,
    ) -> bool:
        body, candle_range, upper_wick, lower_wick = self._candle_parts(candle)
        if candle_range <= 0:
            return False
        candle_open = float(candle["Open"])
        candle_close = float(candle["Close"])
        midpoint = float(candle["Low"]) + candle_range / 2.0

        if direction == "LONG":
            return (
                float(candle["Low"]) <= level < candle_close
                and candle_close > candle_open
                and lower_wick > 0
                and lower_wick > upper_wick
                and candle_close >= midpoint
            )
        return (
            float(candle["High"]) >= level > candle_close
            and candle_close < candle_open
            and upper_wick > 0
            and upper_wick > lower_wick
            and candle_close <= midpoint
        )

    def _build_signal(self, symbol: str, candle: pd.Series, index: int,
                      direction: str, name: str, level: float,
                      target: Optional[float]) -> EntrySignal:
        stop = (level - self.stop_buffer if direction == "LONG"
                else level + self.stop_buffer)
        configured_target = target if TARGET_MODE == "NEXT_PIVOT" else None
        return EntrySignal(
            symbol=symbol,
            trade_date=candle["TradeDate"],
            candle_index=index,
            entry_time=candle["Datetime"],
            direction=direction,
            entry_price=float(candle["Close"]),
            pivot_name=name,
            pivot_price=level,
            stop_price=stop,
            target_price=configured_target,
            vwap=float(candle["VWAP"]),
            entry_mode=self.entry_mode,
        )

    def _immediate_signals(self, symbol: str, data: pd.DataFrame,
                           pivots: PivotLevels) -> list[EntrySignal]:
        signals = []
        for index in range(len(data)):
            candle = data.iloc[index]
            previous = data.iloc[index - 1] if index else None
            if (candle["CandleTime"] > LAST_ENTRY_TIME
                    or pd.isna(candle["VWAP"])):
                continue
            close = float(candle["Close"])
            for name, level, target in pivots.resistance_chain():
                if (
                    close > float(candle["VWAP"])
                    and self._crossed(candle, previous, level, "LONG")
                    and self._breakout_is_strong(data, index, level, "LONG")
                    and self._entry_candle_is_valid(candle, "LONG")
                ):
                    signals.append(self._build_signal(
                        symbol, candle, index, "LONG", name, level, target
                    ))
            for name, level, target in pivots.support_chain():
                if (
                    close < float(candle["VWAP"])
                    and self._crossed(candle, previous, level, "SHORT")
                    and self._breakout_is_strong(data, index, level, "SHORT")
                    and self._entry_candle_is_valid(candle, "SHORT")
                ):
                    signals.append(self._build_signal(
                        symbol, candle, index, "SHORT", name, level, target
                    ))
        return signals

    def _pullback_signals(self, symbol: str, data: pd.DataFrame,
                          pivots: PivotLevels) -> list[EntrySignal]:
        signals = []
        chains = (("LONG", pivots.resistance_chain()),
                  ("SHORT", pivots.support_chain()))
        for direction, levels in chains:
            for name, level, target in levels:
                breakout_index = None
                for index in range(len(data)):
                    candle = data.iloc[index]
                    previous = data.iloc[index - 1] if index else None
                    close = float(candle["Close"])
                    vwap = float(candle["VWAP"])
                    vwap_valid = (
                        close > vwap if direction == "LONG" else close < vwap
                    )
                    if (not pd.isna(candle["VWAP"]) and vwap_valid
                            and self._crossed(
                                candle, previous, level, direction
                            ) and self._breakout_is_strong(
                                data, index, level, direction
                            )):
                        breakout_index = index
                        break
                if breakout_index is None:
                    continue

                for index in range(breakout_index + 1, len(data) - 1):
                    rejection = data.iloc[index]
                    confirmation = data.iloc[index + 1]
                    if (confirmation["CandleTime"] > LAST_ENTRY_TIME
                            or pd.isna(confirmation["VWAP"])):
                        continue

                    confirmation_close = float(confirmation["Close"])
                    confirmation_vwap = float(confirmation["VWAP"])
                    if direction == "LONG":
                        confirmed = (
                            confirmation_close > float(rejection["High"])
                            and confirmation_close > confirmation_vwap
                        )
                    else:
                        confirmed = (
                            confirmation_close < float(rejection["Low"])
                            and confirmation_close < confirmation_vwap
                        )
                    if (
                        self._is_rejection_candle(rejection, level, direction)
                        and confirmed
                        and self._entry_candle_is_valid(confirmation, direction)
                    ):
                        signals.append(self._build_signal(
                            symbol,
                            confirmation,
                            index + 1,
                            direction,
                            name,
                            level,
                            target,
                        ))
                        break
        return signals


# =============================================================================
# PORTFOLIO ENGINE
# =============================================================================

class PortfolioBacktester:
    """Chronological, single-position portfolio execution engine."""

    def __init__(self, grouped_data, strategy: VwapPivotStrategy) -> None:
        self.grouped_data = grouped_data
        self.strategy = strategy

    @staticmethod
    def position_size(capital: float, signal: EntrySignal) -> int:
        risk_per_share = abs(signal.entry_price - signal.stop_price)
        if risk_per_share <= 0:
            return 0
        risk_amount = capital * RISK_PER_TRADE_PERCENT / 100.0
        risk_quantity = math.floor(risk_amount / risk_per_share)
        leverage_quantity = math.floor(
            capital * LEVERAGE / signal.entry_price
        )
        return max(0, min(risk_quantity, leverage_quantity))

    def _previous_day(self, symbol: str, trade_date) -> Optional[pd.DataFrame]:
        symbol_days = self.grouped_data[symbol]
        previous_dates = sorted(day for day in symbol_days if day < trade_date)
        return symbol_days[previous_dates[-1]] if previous_dates else None

    def _daily_signals(self, trade_date) -> list[EntrySignal]:
        signals = []
        for symbol, symbol_days in self.grouped_data.items():
            day_data = symbol_days.get(trade_date)
            previous_day = self._previous_day(symbol, trade_date)
            if day_data is None or previous_day is None:
                continue
            pivots = calculate_pivot_levels(previous_day)
            signals.extend(self.strategy.generate_signals(
                symbol, day_data, pivots
            ))
        return sorted(signals, key=lambda item: (item.entry_time, item.symbol))

    def _execute_trade(self, signal: EntrySignal,
                       capital: float) -> Optional[Trade]:
        quantity = self.position_size(capital, signal)
        if quantity <= 0:
            return None

        day_data = add_intraday_vwap(
            self.grouped_data[signal.symbol][signal.trade_date]
        )
        subsequent = day_data.iloc[signal.candle_index + 1:]
        exit_price = exit_time = exit_reason = None

        for _, candle in subsequent.iterrows():
            candle_open = float(candle["Open"])
            if candle["CandleTime"] >= SQUARE_OFF_TIME:
                exit_price = float(candle["Close"])
                exit_reason = "EOD"
            elif signal.direction == "LONG":
                stop_hit = float(candle["Low"]) <= signal.stop_price
                target_hit = (signal.target_price is not None
                              and float(candle["High"]) >= signal.target_price)
                if stop_hit:
                    exit_price = min(candle_open, signal.stop_price)
                    exit_reason = "STOP_LOSS"
                elif target_hit:
                    exit_price = max(candle_open, signal.target_price)
                    exit_reason = "TARGET"
                elif (signal.target_price is None
                      and float(candle["Close"]) < float(candle["VWAP"])):
                    exit_price = float(candle["Close"])
                    exit_reason = "VWAP_EXIT"
            else:
                stop_hit = float(candle["High"]) >= signal.stop_price
                target_hit = (signal.target_price is not None
                              and float(candle["Low"]) <= signal.target_price)
                if stop_hit:
                    exit_price = max(candle_open, signal.stop_price)
                    exit_reason = "STOP_LOSS"
                elif target_hit:
                    exit_price = min(candle_open, signal.target_price)
                    exit_reason = "TARGET"
                elif (signal.target_price is None
                      and float(candle["Close"]) > float(candle["VWAP"])):
                    exit_price = float(candle["Close"])
                    exit_reason = "VWAP_EXIT"

            if exit_price is not None:
                exit_time = candle["Datetime"]
                break

        if exit_price is None:
            final_candle = day_data.iloc[-1]
            exit_price = float(final_candle["Close"])
            exit_time = final_candle["Datetime"]
            exit_reason = "EOD"

        if signal.direction == "LONG":
            gross_pnl = (exit_price - signal.entry_price) * quantity
        else:
            gross_pnl = (signal.entry_price - exit_price) * quantity

        total_brokerage = BROKERAGE * 2.0
        net_pnl = gross_pnl - total_brokerage
        planned_risk = abs(signal.entry_price - signal.stop_price) * quantity
        return Trade(
            trade_date=signal.trade_date,
            symbol=signal.symbol,
            direction=signal.direction,
            pivot_name=signal.pivot_name,
            pivot_price=signal.pivot_price,
            entry_mode=signal.entry_mode,
            entry_time=signal.entry_time,
            entry_price=signal.entry_price,
            vwap_at_entry=signal.vwap,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            quantity=quantity,
            exposure=signal.entry_price * quantity,
            planned_risk=planned_risk,
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            brokerage=total_brokerage,
            net_pnl=net_pnl,
            r_multiple=net_pnl / planned_risk if planned_risk else 0.0,
            capital_before=capital,
            capital_after=capital + net_pnl,
        )

    def run(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        calendar = sorted({
            day for symbol_days in self.grouped_data.values()
            for day in symbol_days
        })
        capital = INITIAL_CAPITAL
        trades = []
        capital_rows = [{"Date": None, "Capital": capital, "DailyPnL": 0.0}]

        for trade_date in calendar:
            daily_pnl = 0.0
            trades_today = 0
            available_after = pd.Timestamp.min

            for signal in self._daily_signals(trade_date):
                if trades_today >= MAX_TRADES_PER_DAY:
                    break
                if signal.entry_time <= available_after:
                    continue

                trade = self._execute_trade(signal, capital)
                if trade is None:
                    continue
                trades.append(trade)
                capital = trade.capital_after
                daily_pnl += trade.net_pnl
                trades_today += 1
                available_after = trade.exit_time

            capital_rows.append({
                "Date": trade_date,
                "Capital": capital,
                "DailyPnL": daily_pnl,
            })

        trade_log = pd.DataFrame(
            [asdict(trade) for trade in trades],
            columns=Trade.__dataclass_fields__.keys(),
        )
        return trade_log, pd.DataFrame(capital_rows)


# =============================================================================
# REPORTING
# =============================================================================

def calculate_monthly_performance(capital_curve: pd.DataFrame) -> pd.DataFrame:
    daily = capital_curve.dropna(subset=["Date"]).copy()
    if daily.empty:
        return pd.DataFrame(columns=[
            "Month", "StartingCapital", "EndingCapital", "NetPnL",
            "ReturnPct", "TradingDays",
        ])
    daily["Date"] = pd.to_datetime(daily["Date"])
    daily["Month"] = daily["Date"].dt.to_period("M").astype(str)
    rows = []
    for month, group in daily.groupby("Month", sort=True):
        ending = float(group.iloc[-1]["Capital"])
        pnl = float(group["DailyPnL"].sum())
        starting = ending - pnl
        rows.append({
            "Month": month,
            "StartingCapital": starting,
            "EndingCapital": ending,
            "NetPnL": pnl,
            "ReturnPct": pnl / starting * 100.0 if starting else 0.0,
            "TradingDays": len(group),
        })
    return pd.DataFrame(rows)


def calculate_statistics(trades: pd.DataFrame,
                         capital_curve: pd.DataFrame) -> dict:
    equity = capital_curve["Capital"].astype(float)
    final_capital = float(equity.iloc[-1])
    daily = capital_curve.dropna(subset=["Date"]).copy()
    daily_returns = daily["DailyPnL"].astype(float).div(
        daily["Capital"].astype(float) - daily["DailyPnL"].astype(float)
    ).replace([float("inf"), -float("inf")], float("nan")).dropna()
    daily_std = float(daily_returns.std(ddof=1)) if len(daily_returns) > 1 else 0.0

    if trades.empty:
        net_pnl = pd.Series(dtype=float)
        reasons = pd.Series(dtype=str)
        r_multiples = pd.Series(dtype=float)
    else:
        net_pnl = trades["net_pnl"].astype(float)
        reasons = trades["exit_reason"]
        r_multiples = trades["r_multiple"].astype(float)

    wins, losses = net_pnl[net_pnl > 0], net_pnl[net_pnl < 0]
    gross_profit, gross_loss = float(wins.sum()), abs(float(losses.sum()))
    running_peak = equity.cummax()
    drawdown = running_peak - equity
    average_win = float(wins.mean()) if not wins.empty else 0.0
    average_loss = float(losses.mean()) if not losses.empty else 0.0
    win_rate = len(wins) / len(net_pnl) if len(net_pnl) else 0.0
    expectancy = win_rate * average_win + (1.0 - win_rate) * average_loss

    if trades.empty:
        winning_long = winning_short = immediate_entries = pullback_entries = 0
        average_holding_minutes = average_risk_reward = 0.0
        pivot_counts = {name: 0 for name in ("PP", "R1", "R2", "R3",
                                             "S1", "S2", "S3")}
    else:
        winners = trades[trades["net_pnl"].astype(float) > 0]
        winning_long = int((winners["direction"] == "LONG").sum())
        winning_short = int((winners["direction"] == "SHORT").sum())
        immediate_entries = int((trades["entry_mode"] == "IMMEDIATE").sum())
        pullback_entries = int((trades["entry_mode"] == "PULLBACK").sum())
        holding_minutes = (
            pd.to_datetime(trades["exit_time"])
            - pd.to_datetime(trades["entry_time"])
        ).dt.total_seconds() / 60.0
        average_holding_minutes = float(holding_minutes.mean())

        fixed_targets = trades.dropna(subset=["target_price"]).copy()
        if fixed_targets.empty:
            average_risk_reward = 0.0
        else:
            planned_reward = (
                fixed_targets["target_price"].astype(float)
                - fixed_targets["entry_price"].astype(float)
            ).abs()
            planned_risk = (
                fixed_targets["entry_price"].astype(float)
                - fixed_targets["stop_price"].astype(float)
            ).abs().replace(0, float("nan"))
            average_risk_reward = float(
                planned_reward.div(planned_risk).dropna().mean()
            )
        counts = trades["pivot_name"].value_counts()
        pivot_counts = {
            name: int(counts.get(name, 0))
            for name in ("PP", "R1", "R2", "R3", "S1", "S2", "S3")
        }

    return {
        "Initial Capital": INITIAL_CAPITAL,
        "Final Capital": final_capital,
        "Net Profit": final_capital - INITIAL_CAPITAL,
        "Return (%)": (final_capital / INITIAL_CAPITAL - 1.0) * 100.0,
        "Win Rate (%)": win_rate * 100.0,
        "Profit Factor": (gross_profit / gross_loss if gross_loss else
                          (float("inf") if gross_profit else 0.0)),
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss,
        "Maximum Drawdown": float(drawdown.max()),
        "Average Win": average_win,
        "Average Loss": average_loss,
        "Average R Multiple": (float(r_multiples.mean())
                               if not r_multiples.empty else 0.0),
        "Expectancy": expectancy,
        "Sharpe Ratio": (math.sqrt(252.0) * float(daily_returns.mean())
                         / daily_std if daily_std > 0 else 0.0),
        "Total Trades": len(net_pnl),
        "Winning Trades": len(wins),
        "Losing Trades": len(losses),
        "Winning Long Trades": winning_long,
        "Winning Short Trades": winning_short,
        "Immediate Entries": immediate_entries,
        "Pullback Entries": pullback_entries,
        "PP Trades": pivot_counts["PP"],
        "R1 Trades": pivot_counts["R1"],
        "R2 Trades": pivot_counts["R2"],
        "R3 Trades": pivot_counts["R3"],
        "S1 Trades": pivot_counts["S1"],
        "S2 Trades": pivot_counts["S2"],
        "S3 Trades": pivot_counts["S3"],
        "Average Holding (Minutes)": average_holding_minutes,
        "Average Risk:Reward": average_risk_reward,
        "Target Exits": int((reasons == "TARGET").sum()),
        "Stop Loss Exits": int((reasons == "STOP_LOSS").sum()),
        "VWAP Exits": int((reasons == "VWAP_EXIT").sum()),
        "EOD Exits": int((reasons == "EOD").sum()),
    }


def print_statistics(statistics: dict) -> None:
    money_fields = {
        "Initial Capital", "Final Capital", "Net Profit", "Gross Profit",
        "Gross Loss", "Maximum Drawdown", "Average Win", "Average Loss",
        "Expectancy",
    }
    percent_fields = {"Return (%)", "Win Rate (%)"}
    print("\n" + "=" * 62)
    print("VWAP + PIVOT POINT PORTFOLIO BACKTEST")
    print("=" * 62)
    for label, value in statistics.items():
        if label in money_fields:
            text = f"Rs. {value:,.2f}"
        elif label in percent_fields:
            text = f"{value:.2f}%"
        elif isinstance(value, float):
            text = "Infinity" if math.isinf(value) else f"{value:.2f}"
        else:
            text = str(value)
        print(f"{label:<25}: {text}")
    print("=" * 62)


def export_results(trades: pd.DataFrame, capital_curve: pd.DataFrame,
                   monthly: pd.DataFrame) -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    trades.to_csv(TRADE_LOG_FILE, index=False)
    capital_curve.to_csv(CAPITAL_CURVE_FILE, index=False)
    monthly.to_csv(MONTHLY_PERFORMANCE_FILE, index=False)
    print(f"\nTrade log saved to: {TRADE_LOG_FILE.resolve()}")
    print(f"Capital curve saved to: {CAPITAL_CURVE_FILE.resolve()}")
    print(f"Monthly performance saved to: {MONTHLY_PERFORMANCE_FILE.resolve()}")


def validate_configuration() -> None:
    if not STOCKS:
        raise ValueError("config.STOCKS cannot be empty.")
    if INITIAL_CAPITAL <= 0 or LEVERAGE <= 0:
        raise ValueError("INITIAL_CAPITAL and LEVERAGE must be positive.")
    if not 0 < RISK_PER_TRADE_PERCENT <= 100:
        raise ValueError("RISK_PER_TRADE_PERCENT must be between 0 and 100.")
    if BROKERAGE < 0 or STOP_BUFFER_POINTS <= 0:
        raise ValueError("BROKERAGE cannot be negative; stop buffer must be positive.")
    if MAX_TRADES_PER_DAY <= 0:
        raise ValueError("MAX_TRADES_PER_DAY must be positive.")
    if TARGET_MODE not in {"NEXT_PIVOT", "TREND"}:
        raise ValueError("TARGET_MODE must be NEXT_PIVOT or TREND.")
    if VOLUME_MODE not in {"PREVIOUS", "EMA20"}:
        raise ValueError("VOLUME_MODE must be PREVIOUS or EMA20.")
    if VOLUME_EMA_PERIOD <= 0:
        raise ValueError("VOLUME_EMA_PERIOD must be positive.")
    if not 0 <= DOJI_BODY_RATIO <= MIN_ENTRY_BODY_RATIO <= 1:
        raise ValueError("Candle body ratios must satisfy 0 <= DOJI <= ENTRY <= 1.")
    if not 0 <= MIN_BREAKOUT_BODY_RATIO <= 1:
        raise ValueError("MIN_BREAKOUT_BODY_RATIO must be between 0 and 1.")
    if MIN_BREAKOUT_DISTANCE_PERCENT < 0 or MAX_OPPOSITE_WICK_BODY_RATIO < 0:
        raise ValueError("Momentum and wick thresholds cannot be negative.")
    if not MARKET_OPEN <= LAST_ENTRY_TIME < SQUARE_OFF_TIME:
        raise ValueError(
            "LAST_ENTRY_TIME must be after market open and before square-off."
        )
    if ENTRY_MODE.upper() not in {"IMMEDIATE", "PULLBACK"}:
        raise ValueError("ENTRY_MODE must be IMMEDIATE or PULLBACK.")


def main() -> None:
    validate_configuration()
    print("Logging in to Angel One SmartAPI...")
    smart_api = login_user()[0]
    if smart_api is None:
        raise RuntimeError("login_user() did not return a SmartAPI client.")

    stock_data = download_all_data(smart_api)
    if not stock_data:
        raise RuntimeError("No historical data was downloaded.")
    print(f"\nLoaded {len(stock_data)}/{len(STOCKS)} configured stocks.")

    strategy = VwapPivotStrategy(ENTRY_MODE, STOP_BUFFER_POINTS)
    backtester = PortfolioBacktester(group_data_by_day(stock_data), strategy)
    trade_log, capital_curve = backtester.run()
    monthly = calculate_monthly_performance(capital_curve)
    statistics = calculate_statistics(trade_log, capital_curve)
    print_statistics(statistics)
    export_results(trade_log, capital_curve, monthly)


if __name__ == "__main__":
    main()
