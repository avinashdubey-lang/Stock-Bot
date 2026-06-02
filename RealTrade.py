import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from SmartApi import SmartConnect
import pyotp
import csv

# =============================
# 🔐 SMART API LOGIN
# =============================
api_key = "K9Fhvfho"
client_id = "AAAN998226"
password = "3027"
totp_secret = "UA3PJRBKTOTUQSVH67Y4F5ZEZM"

totp = pyotp.TOTP(totp_secret).now()

obj = SmartConnect(api_key=api_key)
session = obj.generateSession(client_id, password, totp)

print("✅ Logged in")

# =============================
# CONFIG
# =============================
TICKER = "^NSEI"
SYMBOL = "NIFTY"
TOKEN = "99926000"

TARGET = 25
STOPLOSS = 25
MAX_TRADES = 1

position = 0
entry_price = 0
trade_count = 0

upper_level = None
lower_level = None

# =============================
# LOG FILE
# =============================
def log_trade(action, price):
    with open("trades.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), action, price])

# =============================
# ORDER FUNCTION
# =============================
def place_order(order_type, qty):
    try:
        orderparams = {
            "variety": "NORMAL",
            "tradingsymbol": SYMBOL,
            "symboltoken": TOKEN,
            "transactiontype": order_type,
            "exchange": "NSE",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": qty
        }

        orderId = obj.placeOrder(orderparams)
        print(f"✅ {order_type} ORDER PLACED")
        return True

    except Exception as e:
        print("❌ Order Error:", e)
        return False

# =============================
# GET PRICE
# =============================
def get_price():
    data = yf.download(TICKER, period="1d", interval="1m")
    return data['Close'].iloc[-1]

# =============================
# MAIN LOOP
# =============================
while True:
    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # ⏰ Market time filter
        if current_time < "09:20":
            print("Waiting for market open...")
            time.sleep(60)
            continue

        if current_time > "15:15":

            if position != 0:
                print("⚠️ Closing open position before market close")

                if position == 1:
                  place_order("SELL", 1)

                elif position == -1:
                  place_order("BUY", 1)

                position = 0

            print("Market closing, exiting...")
            break

        # 📊 Get 15m data
        data = yf.download(TICKER, period="1d", interval="15m")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if len(data) < 3:
            print("Not enough candles")
            time.sleep(60)
            continue

        # 🎯 Set levels once
        if upper_level is None:
            candle2 = data.iloc[1]
            candle3 = data.iloc[2]

            upper_level = max(candle2['Open'], candle3['Open'])
            lower_level = min(candle2['Close'], candle3['Close'])

            print(f"📏 Levels → Upper: {upper_level}, Lower: {lower_level}")

        price = get_price()
        print(f"🕒 Price: {price} | Trades: {trade_count} | Position: {position}")

        # =============================
        # ENTRY
        # =============================
        if position == 0 and trade_count < MAX_TRADES:

            if data['Close'].iloc[-2] > upper_level:
                if place_order("BUY", 1):
                    position = 1
                    entry_price = price
                    trade_count += 1
                    log_trade("BUY", price)

            elif data['Close'].iloc[-2] < lower_level:
                if place_order("SELL", 1):
                    position = -1
                    entry_price = price
                    trade_count += 1
                    log_trade("SELL", price)

        # =============================
        # EXIT
        # =============================
        elif position != 0:

            # BUY
            if position == 1:
                if price >= entry_price + TARGET:
                    if place_order("SELL", 1):
                        print("💰 TARGET HIT (BUY)")
                        log_trade("EXIT BUY", price)
                        position = 0

                elif price <= entry_price - STOPLOSS:
                    if place_order("SELL", 1):
                        print("🛑 STOP LOSS (BUY)")
                        log_trade("SL BUY", price)
                        position = 0

            # SELL
            elif position == -1:
                if price <= entry_price - TARGET:
                    if place_order("BUY", 1):
                        print("💰 TARGET HIT (SELL)")
                        log_trade("EXIT SELL", price)
                        position = 0

                elif price >= entry_price + STOPLOSS:
                    if place_order("BUY", 1):
                        print("🛑 STOP LOSS (SELL)")
                        log_trade("SL SELL", price)
                        position = 0

        time.sleep(60)

    except Exception as e:
        print("⚠️ Error:", e)
        time.sleep(60)