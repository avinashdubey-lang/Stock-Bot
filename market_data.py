import requests
import pandas as pd
import datetime as dt
import time

MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# ==========================
# LOAD MASTER DATA (SAFE + RETRY)
# ==========================

def load_master_data():

    try:
        response = requests.get(MASTER_URL, timeout=20)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"❌ Failed to load master data: {e}")

        # retry once
        try:
            print("🔄 Retrying master data fetch...")
            response = requests.get(MASTER_URL, timeout=20)
            response.raise_for_status()
            return response.json()

        except Exception as e2:
            print(f"❌ Second attempt failed: {e2}")
            return []


master_data = load_master_data()


# ==========================
# TOKEN (FIXED MATCHING LOGIC)
# ==========================

def get_token(symbol):

    if not master_data:
        raise Exception("Master data not loaded")

    base_symbol = symbol.replace("-EQ", "").strip()

    for item in master_data:

        if item.get("exch_seg") != "NSE":
            continue

        if (
            item.get("symbol") == symbol
            or item.get("symbol") == base_symbol
            or base_symbol in item.get("symbol", "")
        ):
            return item["token"]

    raise Exception(f"Token not found: {symbol}")


# ==========================
# CANDLES
# ==========================

def get_candles(smartApi, symbol, interval="FIFTEEN_MINUTE"):

    try:

        token = get_token(symbol)

        today = dt.datetime.now().date()

        from_date = dt.datetime.combine(
            today,
            dt.time(9, 15)
        )

        to_date = dt.datetime.now()

        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }

        print("📥 Fetching candle data...")

        candles = smartApi.getCandleData(params)

        if not candles or "data" not in candles:
            return pd.DataFrame(
                columns=[
                    "time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume"
                ]
            )

        df = pd.DataFrame(
            candles["data"],
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        df["time"] = pd.to_datetime(df["time"])

        return df

    except Exception as e:

        print("\n⚠️ SMARTAPI RATE LIMIT / API ERROR")
        print(e)

        print("⏳ Sleeping for 5 minutes...")
        time.sleep(300)

        return pd.DataFrame(
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )


# ==========================
# LIVE STREAM (STABLE VERSION)
# ==========================

def get_latest_candle_stream(smartApi, symbol, interval="FIFTEEN_MINUTE"):

    print(f"📡 Streaming candles for {symbol}...")

    last_time = None

    while True:

        try:

            df = get_candles(smartApi, symbol, interval)

            if df.empty:
                print("⚠️ No candle data, retrying...")
                time.sleep(5)
                continue

            if len(df) < 2:
                time.sleep(5)
                continue

            latest = df.iloc[-2]  # last completed candle

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

        except Exception as e:

            print(f"❌ Stream Error: {e}")
            time.sleep(10)