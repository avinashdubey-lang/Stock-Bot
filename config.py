# config.py

import os
from dotenv import load_dotenv

MODE = "LIVE"       # "PAPER" or "LIVE"

load_dotenv()

SYMBOL = os.getenv("ANGEL_SYMBOL")

QUANTITY = 88

EXCHANGE = "NSE"

PRODUCT_TYPE = "INTRADAY"

# Angel One (used only in LIVE mode)




API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")