#websocket_feed.py
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from datetime import datetime


class CandleBuilder:

    def __init__(self):
        self.current_candle = None
        self.current_bucket = None

    def bucket(self, ts):
        minute = (ts.minute // 15) * 15
        return ts.replace(minute=minute, second=0, microsecond=0)

    def on_tick(self, ltp, ts):

        bucket = self.bucket(ts)

        if self.current_bucket is None:
            self.current_bucket = bucket

            self.current_candle = {
                "time": bucket,
                "open": ltp,
                "high": ltp,
                "low": ltp,
                "close": ltp
            }
            return None

        if bucket == self.current_bucket:

            self.current_candle["high"] = max(self.current_candle["high"], ltp)
            self.current_candle["low"] = min(self.current_candle["low"], ltp)
            self.current_candle["close"] = ltp
            return None

        completed = self.current_candle

        self.current_bucket = bucket
        self.current_candle = {
            "time": bucket,
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp
        }

        return completed


def start_websocket(api, feed_token, client_code, api_key,
                    symboltoken, strategy, execution_engine):

    candle_builder = CandleBuilder()

    sws = SmartWebSocketV2(
        auth_token=feed_token,
        api_key=api_key,
        client_code=client_code,
        feed_token=feed_token
    )

    tokens = [{
        "exchangeType": 1,
        "tokens": [symboltoken]
    }]

    def on_data(wsapp, message):

        try:
            tick = message

            ltp = tick["last_traded_price"] / 100
            ts = datetime.fromtimestamp(tick["exchange_timestamp"] / 1000)

            # -----------------------
            # 1. EXECUTION ENGINE (LIVE TICK)
            # -----------------------
            execution_engine.on_tick(ltp)

            # -----------------------
            # 2. CANDLE ENGINE
            # -----------------------
            candle = candle_builder.on_tick(ltp, ts)

            if candle:
                print(f"\n15M CLOSED | {candle}")

                strategy(candle)

        except Exception as e:
            print("❌ ON_DATA ERROR:", e)

    def on_open(wsapp):
        print("✅ WebSocket Connected")
        sws.subscribe("stream_1", 2, tokens)

    def on_error(wsapp, error):
        print("❌ WS ERROR:", error)

    def on_close(wsapp):
        print("🔴 WS CLOSED")

    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    sws.connect()