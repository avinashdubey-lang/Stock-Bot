from config import MODE, SYMBOL, ACCOUNTS
import traceback
import threading

import time
from datetime import datetime, time as dt_time


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
def create_brokers():

    if MODE == "PAPER":
        print("🧪 PAPER MODE ACTIVE")
        return [PaperBroker()]

    print("🔥 LIVE MODE ACTIVE")

    brokers = []

    for account in ACCOUNTS:

        print(f"\n🔑 Logging into {account['name']}")

        smartApi, feed_token, client_code, api_key, jwt_token = login_user(account)

        broker = AngelBroker(
            smartApi=smartApi,
            api_key=account["api_key"],
            client_code=account["client_code"],
            password=account["password"],
            totp=account["totp_secret"],
            quantity=account["quantity"],
            account_name=account["name"]
        )

        brokers.append(broker)

    return brokers


# ==========================
# INIT SYSTEM COMPONENTS
# ==========================
brokers = create_brokers()
primary_broker = brokers[0]
smartApi = primary_broker.smartApi

engines = []

for broker in brokers:
    logger = TradeLogger()
    risk = RiskManager()

    engines.append(
        ExecutionEngine(
            broker,
            logger,
            risk
        )
    )
strategy = Strategy()

symboltoken = get_token(SYMBOL)

while True:
    try:
        high, low = get_opening_levels(primary_broker.smartApi, SYMBOL)

        strategy.set_levels(high, low)

        print(f"📊 LEVELS SET: {high} / {low}")

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

    for engine in engines:
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
        client_code=primary_broker.client_code,
        api_key=primary_broker.api_key,
        auth_token=primary_broker.jwt_token,
        feed_token=primary_broker.feed_token,
        on_tick=on_tick,
        lookup=InstrumentLookup(),
        strategy=strategy,
        engines=engines
    )


feed = create_feed()

def eod_watchdog():
    global last_price

    while True:

        now = datetime.now().time()

        if now >= dt_time(14, 59):

            print("🔥 EOD WATCHDOG TRIGGERED")

            for broker, engine in zip(brokers, engines):

                if broker.position and last_price is not None:
                    print("🚨 FORCE EOD EXIT")

                    trade = broker.close_all("EOD_EXIT", last_price)

                    if trade:
                        engine.logger.log_trade(trade)
                        engine.risk.update_pnl(trade["pnl"])

                    engine.trading_done = True

            break

        time.sleep(1)


# ==========================
# START SYSTEM
# ==========================
try:
    threading.Thread(target=eod_watchdog, daemon=True).start()
    feed.start()
except Exception as e:
    print("❌ FEED CRASH:")
    traceback.print_exc()