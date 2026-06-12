from SmartApi import SmartConnect
from instrument_lookup import InstrumentLookup
import pyotp



class AngelBroker:

    def __init__(self, api_key, client_code, password, totp, quantity):

        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp = totp

        self.quantity = quantity
        self.lookup = InstrumentLookup()

        self.position = None
        self.trade_history = []

        self.obj = SmartConnect(api_key=self.api_key)

        self.session = self.obj.generateSession(
            self.client_code,
            self.password,
            pyotp.TOTP(self.totp).now()
        )

        if not self.session:
            raise Exception("Login failed")

        self.jwt_token = self.session["data"]["jwtToken"]
        self.feed_token = self.session["data"]["feedToken"]

        print("✅ Angel One Login Successful")
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

        response = self.obj.placeOrder(order_params)

        print("ORDER RESPONSE:", response)

        return response

    # ==========================
    # BUY
    # ==========================
    def open_trade(self, symbol, direction, entry, target, stoploss):

        if self.position:
            return None

        transaction_type = "BUY" if direction == "BUY" else "SELL"

        order_id = self._place_order(symbol, transaction_type)

        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "target": target,
            "stoploss": stoploss,
            "order_id": order_id
        }

        print(f"🟢 LIVE ORDER PLACED: {direction} {symbol} @ {entry}")

        return self.position

    # ==========================
    # CLOSE POSITION
    # ==========================
    def close_all(self, reason, exit_price):

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

        self._place_order(symbol, transaction_type)

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