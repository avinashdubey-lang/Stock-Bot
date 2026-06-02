import yfinance as yf
import pandas as pd

# ================= SETTINGS =================

SYMBOL = "NIFTYBEES.NS"
PERIOD = "365d"
INVESTMENT_PER_SIGNAL = 1000

# ============================================

print("Downloading NIFTYBEES data...")

df = yf.download(
    SYMBOL,
    period=PERIOD,
    interval="1d",
    auto_adjust=True
)

df.dropna(inplace=True)

# Fix yfinance MultiIndex issue
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.reset_index(inplace=True)

# ============================================
# STRATEGY
# ============================================

total_invested = 0
total_units = 0

transactions = []

for _, row in df.iterrows():

    open_price = float(row["Open"])
    close_price = float(row["Close"])

    # Red candle condition
    if close_price < open_price:

        amount = INVESTMENT_PER_SIGNAL

        units = amount / close_price

        total_units += units
        total_invested += amount

        transactions.append({
            "Date": row["Date"].date(),
            "Buy Price": round(close_price,2),
            "Amount": amount,
            "Units": round(units,4)
        })


# ============================================
# CURRENT VALUE
# ============================================

current_price = float(df.iloc[-1]["Close"])

current_value = total_units * current_price

profit = current_value - total_invested

roi = (profit / total_invested * 100) if total_invested > 0 else 0


# ============================================
# RESULTS
# ============================================

results = pd.DataFrame(transactions)

print("\n========== TRANSACTIONS ==========\n")

print(results)

print("\n========== SUMMARY ==========\n")

print("Signals triggered:", len(results))

print(
    "Total invested: ₹",
    round(total_invested,2)
)

print(
    "Total units:",
    round(total_units,4)
)

print(
    "Current price: ₹",
    round(current_price,2)
)

print(
    "Current portfolio value: ₹",
    round(current_value,2)
)

print(
    "Profit/Loss: ₹",
    round(profit,2)
)

print(
    "ROI:",
    round(roi,2),
    "%"
)