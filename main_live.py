from config import MODE, QUANTITY

from strategy import Strategy
from execution_engine import ExecutionEngine
from risk_manager import RiskManager
from trade_logger import TradeLogger

from paper_broker import PaperBroker
from angel_broker import AngelBroker

from live_feed import LiveFeed


def create_broker():

    if MODE == "PAPER":
        print("🧪 PAPER MODE ACTIVE")
        return PaperBroker()

    print("🔥 LIVE MODE ACTIVE")

    return AngelBroker(
        api_key="YOUR_API_KEY",
        client_code="YOUR_CLIENT_CODE",
        password="YOUR_PASSWORD",
        totp="YOUR_TOTP",
        quantity=QUANTITY
    )


broker = create_broker()
logger = TradeLogger()
risk = RiskManager()

engine = ExecutionEngine(broker, logger, risk)
strategy = Strategy()


# ⚡ IMPORTANT: set levels (temporary static)
strategy.set_levels(
    high_level=1803,
    low_level=1795
)


# ==========================
# CALLBACK (CORE LINK)
# ==========================
def on_tick(price):

    print("\nTICK:", price)

    signal = strategy.on_candle({"close": price})

    if signal:
        engine.on_signal(signal)

    engine.on_tick(price)


# ==========================
# LIVE FEED START
# ==========================
feed = LiveFeed(
    client_code="YOUR_CLIENT_CODE",
    api_key="YOUR_API_KEY",
    token="YOUR_SESSION_TOKEN",   # from login session
    on_tick=on_tick
)

feed.start()