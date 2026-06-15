import requests

class InstrumentLookup:

    def __init__(self):

        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

        print("📥 Loading instrument master...")

        self.data = requests.get(url).json()

        print("✅ Instrument master loaded")

    def get_token(self, symbol):

        for item in self.data:

            if item["symbol"] == symbol:

                return item["token"]

        raise Exception(f"Token not found for {symbol}")