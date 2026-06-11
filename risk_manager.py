# risk_manager.py

class RiskManager:

    def __init__(self):
        self.max_trades_per_day = 1
        self.max_daily_loss = 500
        self.trades_taken = 0
        self.daily_pnl = 0
        self.trading_blocked = False

    def can_take_trade(self):

        if self.trading_blocked:
            return False

        if self.trades_taken >= self.max_trades_per_day:
            return False

        if self.daily_pnl <= -self.max_daily_loss:
            self.trading_blocked = True
            return False

        return True

    def record_trade(self):
        self.trades_taken += 1

    def update_pnl(self, pnl):
        self.daily_pnl += pnl

        if self.daily_pnl <= -self.max_daily_loss:
            self.trading_blocked = True

    def reset(self):
        self.trades_taken = 0
        self.daily_pnl = 0
        self.trading_blocked = False