from risk_manager import RiskManager

rm = RiskManager()

print(rm.can_take_trade())  # Expected: True

rm.record_trade()

print(rm.trades_taken)      # Expected: 1
print(rm.can_take_trade())  # Expected: False (max trades = 1)

rm.update_pnl(-200)

print(rm.daily_pnl)         # Expected: -200

rm.reset()

print(rm.trades_taken)      # Expected: 0
print(rm.daily_pnl)         # Expected: 0
print(rm.can_take_trade())  # Expected: True

rm2 = RiskManager()

rm2.update_pnl(-600)

print(rm2.daily_pnl)
print(rm2.can_take_trade())

rm3 = RiskManager()

rm3.record_trade()
rm3.update_pnl(-100)

print("Before Reset")
print(rm3.trades_taken)
print(rm3.daily_pnl)

rm3.reset()

print("After Reset")
print(rm3.trades_taken)
print(rm3.daily_pnl)