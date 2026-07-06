"""
Download 30-minute Bank Nifty historical candles from Angel One SmartAPI.

Credentials are read from environment variables:
    K9Fhvfho
    AAAN998226
    3027
    UA3PJRBKTOTUQSVH67Y4F5ZEZM
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pyotp
from SmartApi import SmartConnect


# =============================================================================
# CONFIGURATION
# =============================================================================

EXCHANGE = "NSE"

# Bank Nifty spot/index token in Angel One's NSE instrument master.
SYMBOL_TOKEN = "26009"

INTERVAL = "THIRTY_MINUTE"

FROM_DATE = "2024-01-01"
TO_DATE = "2025-12-31"

OUTPUT_FILE = "banknifty_30min.csv"

# Request smaller periods to avoid historical API range limitations.
CHUNK_DAYS = 90
MAX_RETRIES = 3
REQUEST_DELAY_SECONDS = 0.5


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_required_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}. "
            "Set your Angel One credentials before running the script."
        )

    return value.strip()


def create_smartapi_session() -> tuple[SmartConnect, str]:
    """Authenticate with Angel One using PIN and TOTP."""

    api_key = get_required_environment_variable("ANGEL_API_KEY")
    client_code = get_required_environment_variable("ANGEL_CLIENT_CODE")
    pin = get_required_environment_variable("ANGEL_PIN")
    totp_secret = get_required_environment_variable("ANGEL_TOTP_SECRET")

    try:
        totp = pyotp.TOTP(totp_secret).now()
    except Exception as exc:
        raise RuntimeError("Could not generate TOTP. Check the TOTP secret.") from exc

    smart_api = SmartConnect(api_key=api_key)

    response = smart_api.generateSession(
        client_code,
        pin,
        totp,
    )

    if not response or not response.get("status"):
        message = response.get("message", "Unknown login error") if response else ""
        error_code = response.get("errorcode", "") if response else ""

        raise RuntimeError(
            f"Angel One login failed: {message} ({error_code})"
        )

    print("Successfully authenticated with Angel One SmartAPI.")

    return smart_api, client_code


# =============================================================================
# DATA EXTRACTION
# =============================================================================

def request_candles(
    smart_api: SmartConnect,
    from_datetime: datetime,
    to_datetime: datetime,
) -> list:
    """Request one chunk of historical candles with retry handling."""

    parameters = {
        "exchange": EXCHANGE,
        "symboltoken": SYMBOL_TOKEN,
        "interval": INTERVAL,
        "fromdate": from_datetime.strftime("%Y-%m-%d %H:%M"),
        "todate": to_datetime.strftime("%Y-%m-%d %H:%M"),
    }

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = smart_api.getCandleData(parameters)

            if response and response.get("status"):
                return response.get("data") or []

            message = response.get("message", "Unknown API error")
            error_code = response.get("errorcode", "")

            last_error = RuntimeError(
                f"Historical API failed: {message} ({error_code})"
            )

        except Exception as exc:
            last_error = exc

        if attempt < MAX_RETRIES:
            wait_seconds = 2 ** (attempt - 1)

            print(
                f"Request failed; retrying in {wait_seconds} second(s). "
                f"Attempt {attempt}/{MAX_RETRIES}"
            )
            time.sleep(wait_seconds)

    raise RuntimeError(
        f"Unable to retrieve candles for "
        f"{parameters['fromdate']} to {parameters['todate']}"
    ) from last_error


def normalize_timestamp(value: object) -> pd.Timestamp:
    """
    Convert Angel One's timestamp to a timezone-naive Indian-market timestamp.

    The backtester expects local exchange times such as 09:15.
    """

    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("Asia/Kolkata").tz_localize(None)

    return timestamp


def download_historical_data(
    smart_api: SmartConnect,
    from_date: str,
    to_date: str,
) -> pd.DataFrame:
    """Download historical candles in chunks and return a clean DataFrame."""

    start = datetime.strptime(from_date, "%Y-%m-%d").replace(
        hour=9,
        minute=15,
    )

    # Include the entire final trading day.
    final_end = datetime.strptime(to_date, "%Y-%m-%d").replace(
        hour=15,
        minute=30,
    )

    if start > final_end:
        raise ValueError("FROM_DATE must not be later than TO_DATE.")

    all_candles = []
    chunk_start = start

    while chunk_start <= final_end:
        chunk_end = min(
            chunk_start + timedelta(days=CHUNK_DAYS),
            final_end,
        )

        print(
            f"Downloading {chunk_start:%Y-%m-%d} "
            f"to {chunk_end:%Y-%m-%d}..."
        )

        candles = request_candles(
            smart_api=smart_api,
            from_datetime=chunk_start,
            to_datetime=chunk_end,
        )

        all_candles.extend(candles)

        # Move beyond the previous request boundary.
        chunk_start = chunk_end + timedelta(minutes=1)
        time.sleep(REQUEST_DELAY_SECONDS)

    columns = [
        "DateTime",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if not all_candles:
        return pd.DataFrame(columns=columns)

    # Angel One returns:
    # [timestamp, open, high, low, close, volume]
    data = pd.DataFrame(all_candles, columns=columns)

    data["DateTime"] = data["DateTime"].apply(normalize_timestamp)

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(
        subset=["DateTime", "Open", "High", "Low", "Close"]
    )

    data = (
        data.drop_duplicates(subset=["DateTime"], keep="last")
        .sort_values("DateTime")
        .reset_index(drop=True)
    )

    # Retain regular Bank Nifty market-session candles.
    candle_time = data["DateTime"].dt.time

    data = data[
        (candle_time >= datetime.strptime("09:15", "%H:%M").time())
        & (candle_time <= datetime.strptime("15:15", "%H:%M").time())
    ].reset_index(drop=True)

    return data


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    smart_api = None
    client_code = None

    try:
        smart_api, client_code = create_smartapi_session()

        data = download_historical_data(
            smart_api=smart_api,
            from_date=FROM_DATE,
            to_date=TO_DATE,
        )

        if data.empty:
            print("Angel One returned no candle data.")
            return

        output_path = Path(OUTPUT_FILE)
        data.to_csv(output_path, index=False)

        print(f"\nDownloaded {len(data):,} candles.")
        print(f"First candle: {data['DateTime'].min()}")
        print(f"Last candle : {data['DateTime'].max()}")
        print(f"Saved to    : {output_path.resolve()}")

    finally:
        if smart_api is not None and client_code is not None:
            try:
                smart_api.terminateSession(client_code)
                print("Angel One session terminated.")
            except Exception:
                pass


if __name__ == "__main__":
    main()