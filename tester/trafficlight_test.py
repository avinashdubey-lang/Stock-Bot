"""
=================================================================
🧪 TEST 23: CONFIGURABLE TRAFFIC LIGHT STRATEGY
=================================================================

Purpose:
    Verify that the traffic-light behavior can be enabled/disabled.

When USE_TRAFFIC_LIGHT = True:

    same_colour = True
        BUY breakout  -> BUY
        SELL breakout -> SELL

    same_colour = False
        BUY breakout  -> SELL
        SELL breakout -> BUY


When USE_TRAFFIC_LIGHT = False:

    same_colour = True
        BUY breakout  -> BUY
        SELL breakout -> SELL

    same_colour = False
        BUY breakout  -> BUY
        SELL breakout -> SELL

The test modifies config.USE_TRAFFIC_LIGHT dynamically so that
both modes can be tested in one run.
"""

import sys
from pathlib import Path


# ================================================================
# PROJECT ROOT
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ================================================================
# IMPORT CONFIG
# ================================================================

import config


# ================================================================
# IMPORT STRATEGY
# ================================================================

from strategy import Strategy


# ================================================================
# HELPER
# ================================================================

def create_strategy(
    traffic_light,
    same_colour
):

    config.USE_TRAFFIC_LIGHT = traffic_light

    strategy = Strategy()

    strategy.set_levels(
        high_level=100.0,
        low_level=90.0,
        same_colour=same_colour
    )

    return strategy


# ================================================================
# CANDLE HELPER
# ================================================================

def candle(
    close,
    timestamp="2026-08-24 10:15:00"
):

    import pandas as pd

    return {
        "time": pd.Timestamp(timestamp),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 10000
    }


# ================================================================
# HEADER
# ================================================================

print()
print("=" * 65)
print("🧪 TEST 23: CONFIGURABLE TRAFFIC LIGHT STRATEGY")
print("=" * 65)


# ================================================================
# 23A
# TRAFFIC LIGHT ON + SAME COLOUR
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23A: TRAFFIC LIGHT ON + SAME COLOUR")
print("-" * 65)


strategy = create_strategy(
    traffic_light=True,
    same_colour=True
)


print()
print("Traffic Light : ON")
print("Same Colour   : True")
print("Breakout      : BUY")


signal = strategy.on_candle(
    candle(101.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "BUY"
assert signal["entry"] == 101.0

print("✅ BUY BREAKOUT → BUY PASSED")


# ================================================================
# 23B
# TRAFFIC LIGHT ON + OPPOSITE COLOUR
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23B: TRAFFIC LIGHT ON + OPPOSITE COLOUR")
print("-" * 65)


strategy = create_strategy(
    traffic_light=True,
    same_colour=False
)


print()
print("Traffic Light : ON")
print("Same Colour   : False")
print("Breakout      : BUY")


signal = strategy.on_candle(
    candle(101.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "SELL"
assert signal["entry"] == 101.0

print("✅ BUY BREAKOUT → REVERSE SELL PASSED")


# ================================================================
# 23C
# TRAFFIC LIGHT OFF + SAME COLOUR
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23C: TRAFFIC LIGHT OFF + SAME COLOUR")
print("-" * 65)


strategy = create_strategy(
    traffic_light=False,
    same_colour=True
)


print()
print("Traffic Light : OFF")
print("Same Colour   : True")
print("Breakout      : BUY")


signal = strategy.on_candle(
    candle(101.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "BUY"
assert signal["entry"] == 101.0

print("✅ TRAFFIC LIGHT IGNORED → BUY PASSED")


# ================================================================
# 23D
# TRAFFIC LIGHT OFF + OPPOSITE COLOUR
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23D: TRAFFIC LIGHT OFF + OPPOSITE COLOUR")
print("-" * 65)


strategy = create_strategy(
    traffic_light=False,
    same_colour=False
)


print()
print("Traffic Light : OFF")
print("Same Colour   : False")
print("Breakout      : BUY")


signal = strategy.on_candle(
    candle(101.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "BUY"
assert signal["entry"] == 101.0

print("✅ TRAFFIC LIGHT IGNORED → BUY PASSED")


# ================================================================
# 23E
# TRAFFIC LIGHT ON + SAME COLOUR + SELL
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23E: TRAFFIC LIGHT ON + SAME COLOUR + SELL")
print("-" * 65)


strategy = create_strategy(
    traffic_light=True,
    same_colour=True
)


print()
print("Traffic Light : ON")
print("Same Colour   : True")
print("Breakout      : SELL")


signal = strategy.on_candle(
    candle(89.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "SELL"
assert signal["entry"] == 89.0

print("✅ SELL BREAKOUT → SELL PASSED")


# ================================================================
# 23F
# TRAFFIC LIGHT ON + OPPOSITE COLOUR + SELL
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23F: TRAFFIC LIGHT ON + OPPOSITE COLOUR + SELL")
print("-" * 65)


strategy = create_strategy(
    traffic_light=True,
    same_colour=False
)


print()
print("Traffic Light : ON")
print("Same Colour   : False")
print("Breakout      : SELL")


signal = strategy.on_candle(
    candle(89.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "BUY"
assert signal["entry"] == 89.0

print("✅ SELL BREAKOUT → REVERSE BUY PASSED")


# ================================================================
# 23G
# TRAFFIC LIGHT OFF + SAME COLOUR + SELL
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23G: TRAFFIC LIGHT OFF + SAME COLOUR + SELL")
print("-" * 65)


strategy = create_strategy(
    traffic_light=False,
    same_colour=True
)


print()
print("Traffic Light : OFF")
print("Same Colour   : True")
print("Breakout      : SELL")


signal = strategy.on_candle(
    candle(89.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "SELL"
assert signal["entry"] == 89.0

print("✅ TRAFFIC LIGHT IGNORED → SELL PASSED")


# ================================================================
# 23H
# TRAFFIC LIGHT OFF + OPPOSITE COLOUR + SELL
# ================================================================

print()
print("-" * 65)
print("🧪 TEST 23H: TRAFFIC LIGHT OFF + OPPOSITE COLOUR + SELL")
print("-" * 65)


strategy = create_strategy(
    traffic_light=False,
    same_colour=False
)


print()
print("Traffic Light : OFF")
print("Same Colour   : False")
print("Breakout      : SELL")


signal = strategy.on_candle(
    candle(89.0)
)


print()
print("Signal:")
print(signal)


assert signal is not None
assert signal["type"] == "ENTRY"
assert signal["action"] == "SELL"
assert signal["entry"] == 89.0

print("✅ TRAFFIC LIGHT IGNORED → SELL PASSED")


# ================================================================
# RESTORE CONFIG
# ================================================================

config.USE_TRAFFIC_LIGHT = True


# ================================================================
# FINAL RESULT
# ================================================================

print()
print("=" * 65)
print("🔥 TEST 23 PASSED")
print("=" * 65)

print(
    """
TRAFFIC LIGHT CONFIGURATION VERIFIED

TRAFFIC LIGHT ON
    ↓
Same colour
    BUY breakout  → BUY
    SELL breakout → SELL

Opposite colour
    BUY breakout  → SELL
    SELL breakout → BUY


TRAFFIC LIGHT OFF
    ↓
Candle colour ignored

    BUY breakout  → BUY
    SELL breakout → SELL

Both modes work independently.
"""
)

print("=" * 65)