from SmartApi import SmartConnect
import pyotp
import pandas as pd
import requests
import datetime as dt
import time

# ==========================
# LOGIN
# ==========================

api_key = "K9Fhvfho"
client_id = "AAAN998226"
password = "3027"
totp_secret = "UA3PJRBKTOTUQSVH67Y4F5ZEZM"

smartApi = SmartConnect(api_key)

totp = pyotp.TOTP(totp_secret).now()

data = smartApi.generateSession(
    client_id,
    password,
    totp
)

print("Login Successful")

# ==========================
# BHARTIARTL TOKEN
# ==========================

master = requests.get(
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
).json()

bharti = next(
    item for item in master
    if item["symbol"] == "BHARTIARTL-EQ"
    and item["exch_seg"] == "NSE"
)

token = bharti["token"]

print("Token:", token)

# ==========================
# STRATEGY VARIABLES
# ==========================

range_high = None
range_low = None

levels_set = False
signal_given = False

# ==========================
# MAIN LOOP
# ==========================

while True:

    now = dt.datetime.now()

    # Only market hours

    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        time.sleep(30)
        continue

    if now.hour > 15:
        break

    try:

        # ------------------------
        # GET LAST 15M CANDLES
        # ------------------------

        to_date = now.strftime("%Y-%m-%d %H:%M")

        from_date = (
            now - dt.timedelta(days=2)
        ).strftime("%Y-%m-%d %H:%M")

        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": from_date,
            "todate": to_date
        }

        candles = smartApi.getCandleData(params)

        df = pd.DataFrame(
            candles["data"],
            columns=[
                "Datetime",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        )

        today = dt.date.today()

        df["Datetime"] = pd.to_datetime(df["Datetime"])

        today_df = df[
            df["Datetime"].dt.date == today
        ]

        # Need at least 3 candles

        if len(today_df) < 3:

            print("Waiting for candles...")
            time.sleep(60)
            continue

        # ------------------------
        # SET RANGE
        # ------------------------

        if not levels_set:

            second = today_df.iloc[1]
            third = today_df.iloc[2]

            range_high = max(
                second["High"],
                third["High"]
            )

            range_low = min(
                second["Low"],
                third["Low"]
            )

            levels_set = True

            print("\nLEVELS SET")
            print("HIGH =", range_high)
            print("LOW  =", range_low)

        # ------------------------
        # CHECK BREAKOUT
        # ------------------------

        if levels_set and not signal_given:

            latest = today_df.iloc[-1]

            if latest["Close"] > range_high:

                signal_given = True

                print("\nBUY SIGNAL")
                print(
                    "Price:",
                    latest["Close"]
                )

            elif latest["Close"] < range_low:

                signal_given = True

                print("\nSELL SIGNAL")
                print(
                    "Price:",
                    latest["Close"]
                )

        print(
            now.strftime("%H:%M:%S"),
            "Monitoring..."
        )

    except Exception as e:

        print("ERROR:", e)

    time.sleep(60)