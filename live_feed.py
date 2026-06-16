from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import json


class LiveFeed:

    def __init__(self, client_code, api_key, auth_token, feed_token, on_tick, lookup):

        self.client_code = client_code
        self.api_key = api_key
        self.auth_token = auth_token
        self.feed_token = feed_token
        self.on_tick = on_tick
        self.lookup = lookup

        self.ws = SmartWebSocketV2(
        auth_token=self.feed_token,
        api_key=self.api_key,
        client_code=self.client_code,
        feed_token=self.feed_token
    )

        # bind callbacks
        self.ws.on_open = self.on_open
        self.ws.on_data = self.on_message
        self.ws.on_error = self.on_error
        self.ws.on_close = self.on_close
        print("WS OBJECT:", self.ws)
        print("ON MESSAGE:", self.ws.on_message)
    # ==========================
    # CONNECT
    # ==========================
    def start(self):

        print("🔌 Connecting to Live Market Feed...")
        self.ws.connect()
        print("WAITING FOR STREAM DATA...")

    # ==========================
    # SUBSCRIBE (THIS IS THE IMPORTANT PART)
    # ==========================

    def on_open(self, ws):

        print("✅ LIVE FEED CONNECTED")

        token = self.lookup.get_token("BHARTIARTL-EQ")

        token_list = [
            {
                "exchangeType": 2,
                "tokens": [str(token)]
            }
        ]

        print("📡 SUBSCRIBING...")

        self.ws.subscribe(
            "bharti_live",
            2,
            token_list
        )

        print("📡 SUBSCRIBED")


    # ==========================
    # RECEIVE TICK
    # ==========================
    def on_message(self, ws, message):

        print("🔥 RAW:", message)

        try:
            ltp = message["last_traded_price"] / 100

            print("📈 LTP:", ltp)

            self.on_tick(ltp)

        except Exception as e:
            print("❌ TICK PROCESSING ERROR:", e)


    def on_error(self, ws, error):
        print("WS ERROR:", error)

    def on_close(self, ws):
        print("🔴 FEED CLOSED")