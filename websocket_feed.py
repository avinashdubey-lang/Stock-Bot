from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from datetime import datetime


class CandleBuilder:

    def __init__(self):
        self.current_candle = None
        self.last_minute = None
        self.candles = []

    def on_tick(self, tick):

        ltp = tick["last_traded_price"]
        ts = datetime.fromtimestamp(tick["exchange_timestamp"] / 1000)

        minute = ts.replace(second=0, microsecond=0)

        # new candle starts
        if self.last_minute != minute:

            if self.current_candle:
                self.candles.append(self.current_candle)

            self.current_candle = {
                "time": minute,
                "open": ltp,
                "high": ltp,
                "low": ltp,
                "close": ltp
            }

            self.last_minute = minute

        else:
            self.current_candle["high"] = max(self.current_candle["high"], ltp)
            self.current_candle["low"] = min(self.current_candle["low"], ltp)
            self.current_candle["close"] = ltp

        return self.current_candle


def start_websocket(smartApi, token, symboltoken, strategy):

    candle_builder = CandleBuilder()

    sws = SmartWebSocketV2(
        auth_token=smartApi.getfeedToken(),
        api_key=smartApi.api_key,
        client_code=smartApi.client_code,
        feed_token=smartApi.getfeedToken()
    )

    correlation_id = "stream_1"
    mode = 2   # LTP mode

    tokens = [{
        "exchangeType": 1,      # NSE
        "tokens": [symboltoken]
    }]

    def on_data(wsapp, message):

        tick = message["data"][0]

        candle = candle_builder.on_tick(tick)

        if not candle:
            return

        signal = strategy.on_candle(candle)

        if signal:
            print("\n🚨 SIGNAL:", signal)

    def on_open(wsapp):
        print("WebSocket Connected")
        sws.subscribe(correlation_id, mode, tokens)

    def on_error(wsapp, error):
        print("WS ERROR:", error)

    def on_close(wsapp):
        print("WebSocket Closed")

    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    sws.connect()