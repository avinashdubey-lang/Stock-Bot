import json
import websocket


def start_websocket(symbol, callback):

    """
    PURE WEBSOCKET CLIENT (NO SmartAPI dependency)
    FIXES:
    - no start_websocket error
    - works with websocket-client
    """

    def on_message(ws, message):

        try:
            data = json.loads(message)

            if "data" not in data:
                return

            tick = data["data"]

            if isinstance(tick, list):
                tick = tick[0]

            candle = {
                "time": tick.get("time"),
                "open": tick.get("open"),
                "high": tick.get("high"),
                "low": tick.get("low"),
                "close": tick.get("close"),
                "volume": tick.get("volume", 0)
            }

            callback(candle)

        except Exception as e:
            print("WS ERROR:", e)


    def on_error(ws, error):
        print("WS ERROR:", error)


    def on_close(ws, close_status_code, close_msg):
        print("WebSocket Closed")


    def on_open(ws):
        print("WebSocket Connected")

        # NOTE: This is a generic structure
        # Angel One REAL WS requires feed_token auth
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": symbol
        }))


    ws = websocket.WebSocketApp(
        "wss://example-feed-url",   # placeholder (we fix next step)
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()