from SmartApi import SmartWebSocket


class LiveFeed:

    def __init__(self, client_code, api_key, token, on_tick):

        self.client_code = client_code
        self.api_key = api_key
        self.token = token
        self.on_tick = on_tick

        self.ws = SmartWebSocket(
            self.api_key,
            self.client_code,
            self.token
        )

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

        # Example subscription (you will update token)
        self.ws.subscribe("nse_cm|26009")  # BHARTIARTL token example

    # ==========================
    # RECEIVE TICK
    # ==========================
    def on_message(self, ws, message):

        try:
            ltp = message.get("last_traded_price")

            if ltp:
                print("LIVE TICK:", ltp)
                self.on_tick(float(ltp))

        except Exception as e:
            print("Tick Error:", e)

    def on_error(self, ws, error):
        print("WS ERROR:", error)

    def on_close(self, ws):
        print("🔴 FEED CLOSED")