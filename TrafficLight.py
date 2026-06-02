from SmartApi import SmartConnect
import pyotp
import pandas as pd
import requests
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
# GET BHARTIARTL TOKEN
# ==========================

url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

master = requests.get(url).json()

bharti = next(
    item for item in master
    if item["symbol"] == "BHARTIARTL-EQ"
    and item["exch_seg"] == "NSE"
)

token = bharti["token"]

print("Token:", token)

# ==========================
# LIVE PRICE LOOP
# ==========================

while True:

    try:

        ltp = smartApi.ltpData(
            "NSE",
            "BHARTIARTL-EQ",
            token
        )

        price = ltp["data"]["ltp"]

        print(
            time.strftime("%H:%M:%S"),
            "-> BHARTIARTL =",
            price
        )

    except Exception as e:

        print("Error:", e)

    time.sleep(5)