from SmartApi import SmartConnect
from instrument_lookup import InstrumentLookup
import pyotp



class AngelBroker:

    def __init__(self, smartApi, api_key, client_code, password, totp, quantity):

        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp = totp
        self.smartApi = smartApi

        self.quantity = quantity
        self.lookup = InstrumentLookup()

        self.position = None
        self.trade_history = []

        self.obj = smartApi

        self.jwt_token = smartApi.access_token
        self.feed_token = smartApi.getfeedToken()

        print("✅ Reusing existing Angel session")
        print("JWT READY")
        print("FEED READY")

    # ==========================
    # PLACE ORDER (CORE)
    # ==========================
    def _place_order(self, symbol, transaction_type):

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": self._get_token(symbol),
            "transactiontype": transaction_type,
            "exchange": "NSE",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": self.quantity
        }

        try:
            response = self.obj.placeOrder(order_params)
        except Exception as e:
            print("❌ BROKER ERROR:", e)
            return None

        if not response:
            print("❌ ORDER FAILED:", response)
            return None

        if isinstance(response, dict):
            if response.get("status") is False:
                print("❌ ORDER FAILED:", response)
                return None

        print("ORDER RESPONSE:", response)
        return response

    # ==========================
    # BUY
    # ==========================
    def open_trade(self, symbol, direction, entry, target, stoploss):

        if self.position:
            return None

        transaction_type = "BUY" if direction == "BUY" else "SELL"

        response = self._place_order(symbol, transaction_type)

        print("ENTRY ORDER RESPONSE:", response)

        if not response:
            return None

        if isinstance(response, dict):
            order_id = (
                response.get("data", {}).get("orderid")
                or response.get("orderid")
            )
        else:
            order_id = response

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss,
            "order_id": order_id
        }

        print("✅ POSITION STORED:", self.position)

        print(f"🟢 LIVE ORDER PLACED: {direction} {symbol} @ {entry}")

        return self.position

    # ==========================
    # CLOSE POSITION
    # ==========================
    def close_all(self, reason, exit_price):

        print("🚨 CLOSE_ALL CALLED")
        print("REASON:", reason)
        print("EXIT PRICE:", exit_price)


        if not self.position:
            return None

        direction = self.position["direction"]
        symbol = self.position["symbol"]
        entry = self.position["entry"]

        # reverse order
        if direction == "BUY":
            transaction_type = "SELL"
        else:
            transaction_type = "BUY"

        token = self._get_token(symbol)

        if not token:
            print("❌ CLOSE FAILED: invalid token")
            return None

        print("➡️ ABOUT TO SEND EXIT ORDER")
        print("SYMBOL:", symbol)
        print("SIDE:", transaction_type)

        try:
            response = self._place_order(symbol, transaction_type)
            print("⬅️ EXIT ORDER RETURNED:", response)

        except Exception as e:
            print("💥 EXIT ORDER EXCEPTION:", e)
            raise

        if not response:
            print("❌ EXIT ORDER FAILED")
            return None

        # pnl calculation
        if direction == "BUY":
            pnl = exit_price - entry
        else:
            pnl = entry - exit_price

        trade = {
            **self.position,
            "exit": exit_price,
            "reason": reason,
            "pnl": pnl
        }

        self.trade_history.append(trade)

        print(f"🔴 LIVE EXIT: {reason} @ {exit_price}")

        self.position = None

        return trade

    # ==========================
    # TOKEN RESOLUTION (placeholder)
    # ==========================
    def _get_token(self, symbol):
        return self.lookup.get_token(symbol)