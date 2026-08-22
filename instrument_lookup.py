import json
import os
import time
import requests


class InstrumentLookup:

    MASTER_URL = (
        "https://margincalculator.angelbroking.com/"
        "OpenAPI_File/files/OpenAPIScripMaster.json"
    )

    CACHE_FILE = "instrument_master.json"

    MAX_RETRIES = 5
    RETRY_DELAY = 10
    REQUEST_TIMEOUT = 30

    def __init__(self):

        print("📥 Loading instrument master...")

        self.data = self._load_master()

        if not self.data:
            raise Exception("Instrument master is empty")

        print(
            f"✅ Instrument master loaded "
            f"({len(self.data)} instruments)"
        )

    # ==========================================
    # LOAD MASTER
    # ==========================================

    def _load_master(self):

        # --------------------------------------
        # 1. TRY CACHE FIRST
        # --------------------------------------

        if os.path.exists(self.CACHE_FILE):

            try:

                print("📂 Loading cached instrument master...")

                with open(
                    self.CACHE_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:

                    data = json.load(f)

                if isinstance(data, list) and data:

                    print("✅ Cached instrument master loaded")

                    return data

                print("⚠️ Cached instrument master is invalid")

            except Exception as e:

                print(
                    f"⚠️ Failed to load cached master: {e}"
                )

        # --------------------------------------
        # 2. DOWNLOAD WITH RETRIES
        # --------------------------------------

        for attempt in range(1, self.MAX_RETRIES + 1):

            try:

                print(
                    f"📥 Downloading instrument master "
                    f"(attempt {attempt}/{self.MAX_RETRIES})..."
                )

                response = requests.get(
                    self.MASTER_URL,
                    timeout=self.REQUEST_TIMEOUT
                )

                response.raise_for_status()

                data = response.json()

                # ----------------------------------
                # VALIDATE RESPONSE
                # ----------------------------------

                if not isinstance(data, list) or not data:

                    raise Exception(
                        "Invalid or empty instrument master"
                    )

                # ----------------------------------
                # SAVE ONLY AFTER SUCCESS
                # ----------------------------------

                temp_file = self.CACHE_FILE + ".tmp"

                with open(
                    temp_file,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(data, f)

                os.replace(
                    temp_file,
                    self.CACHE_FILE
                )

                print("✅ Instrument master downloaded")
                print("💾 Instrument master cached")

                return data

            except Exception as e:

                print(
                    f"❌ Instrument master attempt "
                    f"{attempt}/{self.MAX_RETRIES} failed"
                )

                print(f"   {e}")

                if attempt < self.MAX_RETRIES:

                    print(
                        f"⏳ Retrying in "
                        f"{self.RETRY_DELAY} seconds..."
                    )

                    time.sleep(self.RETRY_DELAY)

        # --------------------------------------
        # 3. EVERYTHING FAILED
        # --------------------------------------

        raise Exception(
            "❌ Unable to load instrument master "
            "after all retry attempts"
        )

    # ==========================================
    # TOKEN LOOKUP
    # ==========================================

    def get_token(self, symbol):

        for item in self.data:

            if item.get("symbol") == symbol:

                return item["token"]

        raise Exception(
            f"Token not found for {symbol}"
        )