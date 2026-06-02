import requests
import pandas as pd
import datetime as dt
import time


MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

master_data = requests.get(MASTER_URL).json()


# ==========================
# TOKEN
# ==========================

def get_token(symbol):

    for item in master_data:
        if item["symbol"] == symbol and item["exch_seg"] == "NSE":
            return item["token"]

    raise Exception(f"Token not found: {symbol}")


# ==========================
# CANDLES
# ==========================

def get_candles(smartApi, symbol, interval="FIFTEEN_MINUTE", days=1):

    token = get_token(symbol)

    to_date = dt.datetime.now()
    from_date = to_date - dt.timedelta(days=days)

    params = {
        "exchange": "NSE",
        "symboltoken": token,
        "interval": interval,
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M")
    }

    candles = smartApi.getCandleData(params)

    if not candles or "data" not in candles:
        return pd.DataFrame(columns=["time","open","high","low","close","volume"])

    df = pd.DataFrame(
        candles["data"],
        columns=["time", "open", "high", "low", "close", "volume"]
    )

    df["time"] = pd.to_datetime(df["time"])

    return df


# ==========================
# LIVE STREAM (FIXED)
# ==========================

def get_latest_candle_stream(smartApi, symbol, interval="FIFTEEN_MINUTE"):

    print(f"📡 Streaming candles for {symbol}...")

    last_time = None

    while True:

        df = get_candles(smartApi, symbol, interval)

        if df.empty:
            print("⚠️ No candle data, retrying...")
            time.sleep(5)
            continue

        latest = df.iloc[-1]

        # prevent duplicate candle replay
        if last_time == latest["time"]:
            time.sleep(5)
            continue

        last_time = latest["time"]

        yield {
            "time": latest["time"],
            "open": latest["open"],
            "high": latest["high"],
            "low": latest["low"],
            "close": latest["close"],
            "volume": latest["volume"]
        }

        time.sleep(120)