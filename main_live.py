from config import MODE, QUANTITY, SYMBOL, API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET
import traceback

import time
from datetime import datetime, date, time as dt_time

from strategy import Strategy
from execution_engine import ExecutionEngine
from risk_manager import RiskManager
from trade_logger import TradeLogger
from market_data import get_opening_levels, get_token
from login import login_user

from paper_broker import PaperBroker
from angel_broker import AngelBroker

from live_feed import LiveFeed
from instrument_lookup import InstrumentLookup


# ==========================
# BROKER CREATION
# ==========================
def create_broker():

    if MODE == "PAPER":
        print("🧪 PAPER MODE ACTIVE")
        return PaperBroker()

    print("🔥 LIVE MODE ACTIVE")

    smartApi = login_user()[0]

    return AngelBroker(
        smartApi=smartApi,
        api_key=API_KEY,
        client_code=CLIENT_CODE,
        password=PASSWORD,
        totp=TOTP_SECRET,
        quantity=QUANTITY
    )


# ==========================
# INIT SYSTEM COMPONENTS
# ==========================
broker = create_broker()
smartApi = broker.smartApi

logger = TradeLogger()
risk = RiskManager()

strategy = Strategy()

engine = ExecutionEngine(
    broker,
    logger,
    risk,
    strategy
)

symboltoken = get_token(SYMBOL)

levels_initialized = False

current_day = date.today()

# ==========================
# START NEW TRADING DAY
# ==========================
def start_new_day():

    high, low, same_colour = get_opening_levels(
        broker.smartApi,
        SYMBOL
    )

    strategy.reset()
    engine.reset()
    risk.reset()

    strategy.set_levels(
        high,
        low,
        same_colour
    )

    print(f"📊 LEVELS SET: {high} / {low}")
    print(f"🎨 SAME COLOR : {same_colour}")


if datetime.now().time() >= dt_time(10, 0):

    try:

        print("📊 Initializing today's levels...")

        start_new_day()

        levels_initialized = True

    except Exception as e:

        print("❌ Failed to initialize today's levels.")
        print(e)

else:
    print("⏳ Waiting until 10:00 AM before initializing levels.")



# ==========================
# TICK CALLBACK (CORE LOOP)
# ==========================
last_price = None

def on_tick(price):

    global last_price
    global current_day
    global levels_initialized

    # New trading day
    if date.today() != current_day:

        print("\n🌅 NEW TRADING DAY DETECTED")

        current_day = date.today()

        levels_initialized = False

        feed.reset()

    # Initialize today's levels after 10:00
    if (
        not levels_initialized
        and datetime.now().time() >= dt_time(10, 0)
    ):

        try:

            print("📊 Initializing today's levels...")

            start_new_day()

            levels_initialized = True

        except Exception as e:

            print("❌ Failed to initialize today's levels.")
            print(e)

    last_price = price


    print("\nTICK:", price)

    engine.on_tick(price)


# ==========================
# LIVE FEED SETUP
# ==========================
def create_feed():

    if MODE == "PAPER":
        print("🧪 PAPER FEED MODE")
        return None

    # IMPORTANT: reuse same session from broker
    return LiveFeed(
        client_code=CLIENT_CODE,
        api_key=API_KEY,
        auth_token=broker.jwt_token,
        feed_token=broker.feed_token,
        on_tick=on_tick,
        lookup=InstrumentLookup(),
        strategy=strategy,
        engine=engine
    )


feed = create_feed()



# ==========================
# START SYSTEM
# ==========================
try:
    feed.start()
except Exception as e:
    print("❌ FEED CRASH:")
    traceback.print_exc()