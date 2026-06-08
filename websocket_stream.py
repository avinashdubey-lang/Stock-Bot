from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from market_data import get_token


def start_websocket(
    smartApi,
    feed_token,
    client_code,
    api_key,
    symbol,
    callback
):

    symbol_token = get_token(symbol)

    sws = SmartWebSocketV2(
        auth_token=feed_token,
        api_key=api_key,
        client_code=client_code,
        feed_token=feed_token
    )

    correlation_id = "bot_stream"
    mode = 1  # LTP mode

    token_list = [{
        "exchangeType": 1,
        "tokens": [str(symbol_token)]
    }]

    # ==========================
    # OPEN CONNECTION
    # ==========================
    def on_open(wsapp):
        print("✅ WebSocket Connected")

        sws.subscribe(
            correlation_id,
            mode,
            token_list
        )

    # ==========================
    # DATA HANDLER (FIXED)
    # ==========================
    def on_data(wsapp, message):

        try:
            # SmartAPI sometimes sends list inside "data"
            if isinstance(message, str):
                import json
                message = json.loads(message)

            data = message.get("data")

            if isinstance(data, list):
                data = data[0]

            if not data:
                return

            ltp = data.get("ltp")

            if ltp is None:
                return

            candle = {
                "time": data.get("exchange_timestamp"),
                "open": ltp,
                "high": ltp,
                "low": ltp,
                "close": ltp,
                "volume": data.get("volume_traded", 0)
            }

            callback(candle)

        except Exception as e:
            print("WS DATA ERROR:", e)

    # ==========================
    # ERROR HANDLER
    # ==========================
    def on_error(wsapp, error):
        print("WS ERROR:", error)

    # ==========================
    # CLOSE HANDLER
    # ==========================
    def on_close(wsapp):
        print("❌ WebSocket Closed")

    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close

    print(f"📡 Starting WebSocket for {symbol}")

    sws.connect()