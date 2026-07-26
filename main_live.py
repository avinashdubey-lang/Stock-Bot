from config import MODE, QUANTITY, SYMBOL, API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET
import traceback

import time


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

while True:
    try:
        high, low, same_colour = get_opening_levels(broker.smartApi, SYMBOL)

        strategy.reset()
        engine.reset()

        strategy.set_levels(high, low, same_colour)

        print(f"📊 LEVELS SET: {high} / {low}")
        print(f"🎨 SAME COLOR : {same_colour}")

        break

    except Exception as e:
        print("⏳ Waiting for opening levels...")
        print(e)

        time.sleep(60)



# ==========================
# TICK CALLBACK (CORE LOOP)
# ==========================
last_price = None
def on_tick(price):

    global last_price
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