"""
=================================================================
🧪 TEST 21: INSTRUMENT MASTER RETRY + CACHE RECOVERY
=================================================================

Tests:

21A - Instrument master download retry
21B - Successful download creates cache
21C - Existing cache avoids network request
21D - Invalid cache falls back to download

This test uses a controlled fake requests.get()
and does NOT contact Angel One.
"""

import json
import os
import tempfile
from unittest.mock import patch

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from instrument_lookup import InstrumentLookup


# ================================================================
# FAKE RESPONSE
# ================================================================

class FakeResponse:

    def __init__(self, data=None, error=None):

        self.data = data
        self.error = error

    def raise_for_status(self):

        if self.error:
            raise self.error

    def json(self):

        if self.error:
            raise self.error

        return self.data


# ================================================================
# FAKE REQUESTS
# ================================================================

class FakeRequests:

    def __init__(self):

        self.calls = 0

        self.valid_data = [
            {
                "symbol": "BHARTIARTL-EQ",
                "token": "10604",
                "exch_seg": "NSE"
            },
            {
                "symbol": "RELIANCE-EQ",
                "token": "2885",
                "exch_seg": "NSE"
            }
        ]

    def get(self, url, timeout=None):

        self.calls += 1

        print(
            f"\n🧪 FAKE REQUEST #{self.calls}"
        )

        print(
            "URL     :",
            url
        )

        print(
            "TIMEOUT :",
            timeout
        )

        # --------------------------------------------------------
        # FIRST REQUEST FAILS
        # --------------------------------------------------------

        if self.calls == 1:

            print(
                "❌ SIMULATED CONNECTION FAILURE"
            )

            raise ConnectionError(
                "Simulated incomplete instrument-master download"
            )

        # --------------------------------------------------------
        # SECOND REQUEST SUCCEEDS
        # --------------------------------------------------------

        print(
            "✅ SIMULATED INSTRUMENT MASTER RESPONSE"
        )

        return FakeResponse(
            data=self.valid_data
        )


# ================================================================
# TEST SETUP
# ================================================================

print("\n")
print("=" * 65)
print(
    "🧪 TEST 21: INSTRUMENT MASTER RETRY + CACHE RECOVERY"
)
print("=" * 65)


fake_requests = FakeRequests()


with tempfile.TemporaryDirectory() as temp_dir:

    cache_file = os.path.join(
        temp_dir,
        "instrument_master.json"
    )

    # ============================================================
    # PATCH REQUESTS + CACHE LOCATION
    # ============================================================

    with patch(
        "instrument_lookup.requests.get",
        side_effect=fake_requests.get
    ), patch.object(
        InstrumentLookup,
        "CACHE_FILE",
        cache_file
    ):

        # ========================================================
        # TEST 21A
        # ========================================================

        print("\n")
        print("-" * 65)
        print(
            "🧪 TEST 21A: INSTRUMENT MASTER DOWNLOAD RETRY"
        )
        print("-" * 65)

        print(
            "\n🧠 Creating InstrumentLookup..."
        )

        lookup = InstrumentLookup()

        print("\n")
        print(
            "Network requests:",
            fake_requests.calls
        )

        assert fake_requests.calls == 2

        print(
            "✅ DOWNLOAD RETRY PASSED"
        )

        # ========================================================
        # TEST 21B
        # ========================================================

        print("\n")
        print("-" * 65)
        print(
            "🧪 TEST 21B: CACHE CREATED"
        )
        print("-" * 65)

        print(
            "\nCache path:"
        )

        print(
            cache_file
        )

        assert os.path.exists(cache_file)

        print(
            "✅ CACHE FILE EXISTS"
        )

        with open(
            cache_file,
            "r",
            encoding="utf-8"
        ) as f:

            cached_data = json.load(f)

        print(
            "\nCached instruments:"
        )

        print(
            cached_data
        )

        assert cached_data == fake_requests.valid_data

        print(
            "✅ CACHE CONTENT PASSED"
        )

        # ========================================================
        # VERIFY TOKEN LOOKUP
        # ========================================================

        print("\n")
        print(
            "🔍 Verifying token lookup..."
        )

        token = lookup.get_token(
            "BHARTIARTL-EQ"
        )

        print(
            "BHARTIARTL-EQ token:",
            token
        )

        assert token == "10604"

        print(
            "✅ TOKEN LOOKUP PASSED"
        )

        # ========================================================
        # TEST 21C
        # ========================================================

        print("\n")
        print("-" * 65)
        print(
            "🧪 TEST 21C: CACHE RECOVERY"
        )
        print("-" * 65)

        calls_before_cache_test = (
            fake_requests.calls
        )

        print(
            "\n🧠 Creating second InstrumentLookup..."
        )

        lookup_cached = InstrumentLookup()

        calls_after_cache_test = (
            fake_requests.calls
        )

        print(
            "\nNetwork requests before:",
            calls_before_cache_test
        )

        print(
            "Network requests after :",
            calls_after_cache_test
        )

        # No new network request should happen.
        assert (
            calls_after_cache_test
            == calls_before_cache_test
        )

        print(
            "✅ CACHE LOAD PASSED"
        )

        cached_token = lookup_cached.get_token(
            "BHARTIARTL-EQ"
        )

        assert cached_token == "10604"

        print(
            "Cached token:",
            cached_token
        )

        print(
            "✅ CACHED TOKEN LOOKUP PASSED"
        )

        # ========================================================
        # TEST 21D
        # ========================================================

        print("\n")
        print("-" * 65)
        print(
            "🧪 TEST 21D: INVALID CACHE FALLBACK"
        )
        print("-" * 65)

        print(
            "\n🧪 Corrupting cache..."
        )

        with open(
            cache_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "{ invalid json"
            )

        calls_before_invalid_cache = (
            fake_requests.calls
        )

        print(
            "\n🧠 Creating third InstrumentLookup..."
        )

        lookup_recovered = InstrumentLookup()

        calls_after_invalid_cache = (
            fake_requests.calls
        )

        print(
            "\nNetwork requests before:",
            calls_before_invalid_cache
        )

        print(
            "Network requests after :",
            calls_after_invalid_cache
        )

        # Network should be used because cache is invalid.
        assert (
            calls_after_invalid_cache
            > calls_before_invalid_cache
        )

        print(
            "✅ INVALID CACHE FALLBACK PASSED"
        )

        recovered_token = lookup_recovered.get_token(
            "BHARTIARTL-EQ"
        )

        print(
            "Recovered token:",
            recovered_token
        )

        assert recovered_token == "10604"

        print(
            "✅ RECOVERED TOKEN LOOKUP PASSED"
        )


# ================================================================
# FINAL RESULT
# ================================================================

print("\n")
print("=" * 65)
print(
    "🔥 TEST 21 PASSED"
)
print("=" * 65)

print(
    """
INSTRUMENT MASTER RELIABILITY WORKS

First startup
      ↓
Instrument master download
      ↓
❌ Simulated connection failure
      ↓
Retry
      ↓
✅ Download succeeds
      ↓
Cache created
      ↓
Next startup
      ↓
📂 Cache loaded
      ↓
No network request
      ↓
Cache corrupted
      ↓
❌ Cache rejected
      ↓
Network download
      ↓
✅ Recovery
"""
)

print("=" * 65)