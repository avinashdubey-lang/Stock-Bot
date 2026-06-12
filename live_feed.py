from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import json


class LiveFeed:

    def __init__(self, client_code, api_key, feed_token, on_tick):

        self.client_code = client_code
        self.api_key = api_key
        self.feed_token = feed_token
        self.on_tick = on_tick

        self.ws = SmartWebSocketV2(self.api_key, self.client_code, self.feed_token)

        self.ws.on_open = self.on_open
        self.ws.on_message = self.on_message
        self.ws.on_error = self.on_error
        self.ws.on_close = self.on_close

    # ==========================
    # CONNECT
    # ==========================
    def start(self):

        print("🔌 Connecting to Live Market Feed...")
        self.ws.connect()

    # ==========================
    # SUBSCRIBE
    # ==========================
    def on_open(self, ws):

        print("✅ LIVE FEED CONNECTED")

        # TEMP FIX: replace later with dynamic symbol token
        self.ws.subscribe("nse_cm", ["26009"])

    # ==========================
    # RECEIVE TICK
    # ==========================
    def on_message(self, ws, message):

        try:
            data = json.loads(message) if isinstance(message, str) else message

            ltp = None

            if isinstance(data, dict):
                ltp = data.get("ltp") or data.get("last_traded_price")

                # SmartAPI sometimes nests data
                if not ltp and "data" in data:
                    ltp = data["data"].get("ltp") or data["data"].get("last_traded_price")

            if ltp:
                print("LIVE TICK:", ltp)
                self.on_tick(float(ltp))

        except Exception as e:
            print("Tick Error:", e)

    def on_error(self, ws, error):
        print("WS ERROR:", error)

    def on_close(self, ws):
        print("🔴 FEED CLOSED")