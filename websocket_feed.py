from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from datetime import datetime


class CandleBuilder:

    def __init__(self):
        self.current_candle = None
        self.current_bucket = None

    def get_bucket(self, ts):

        minute = (ts.minute // 15) * 15

        return ts.replace(
            minute=minute,
            second=0,
            microsecond=0
        )

    def on_tick(self, tick):

        ltp = tick["last_traded_price"]/100

        ts = datetime.fromtimestamp(
            tick["exchange_timestamp"] / 1000
        )

        bucket = self.get_bucket(ts)

        # First candle
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

        # Same candle
        if bucket == self.current_bucket:

            self.current_candle["high"] = max(
                self.current_candle["high"],
                ltp
            )

            self.current_candle["low"] = min(
                self.current_candle["low"],
                ltp
            )

            self.current_candle["close"] = ltp

            return None

        # Completed candle
        completed_candle = self.current_candle

        self.current_bucket = bucket

        self.current_candle = {
            "time": bucket,
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp
        }

        return completed_candle


def start_websocket(
    smartApi,
    feed_token,
    client_code,
    api_key,
    symboltoken,
    callback
):

    candle_builder = CandleBuilder()

    sws = SmartWebSocketV2(
        auth_token=feed_token,
        api_key=api_key,
        client_code=client_code,
        feed_token=feed_token
    )

    correlation_id = "stream_1"

    mode = 2

    tokens = [{
        "exchangeType": 1,
        "tokens": [symboltoken]
    }]

    def on_data(wsapp, message):

        try:
            tick = message
           
            completed_candle = (
                candle_builder.on_tick(tick)
            )

            if completed_candle is None:
                return

            print(
                f"\n15M CLOSED | "
                f"{completed_candle['time']} | "
                f"O:{completed_candle['open']} "
                f"H:{completed_candle['high']} "
                f"L:{completed_candle['low']} "
                f"C:{completed_candle['close']}"
            )

            callback(completed_candle)

        except Exception as e:

            print(
                f"❌ ON_DATA ERROR: {e}"
            )

    def on_open(wsapp):

        print("✅ WebSocket Connected")

        sws.subscribe(
            correlation_id,
            mode,
            tokens
        )

    def on_error(wsapp, error):

        print(
            f"❌ WS ERROR: {error}"
        )

    def on_close(wsapp):

        print(
            "🔴 WebSocket Closed"
        )

    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    sws.connect()