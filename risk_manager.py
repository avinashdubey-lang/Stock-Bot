# risk_manager.py

class RiskManager:

    def __init__(self):
        self.max_trades_per_day = 1
        self.max_daily_loss = 500

        self.trades_taken = 0
        self.daily_pnl = 0
        self.trading_blocked = False

    # ==========================
    # MAIN RISK CHECK
    # ==========================
    def can_take_trade(self, entry=None, quantity=None, capital=None):

        if self.trading_blocked:
            return False

        if self.trades_taken >= self.max_trades_per_day:
            return False


        # --------------------------
        # OPTIONAL MARGIN CHECK
        # --------------------------
        if entry is not None and quantity is not None and capital is not None:

            required_margin = entry * quantity

            if required_margin > capital:
                return False

        return True

    # ==========================
    # RECORD TRADE
    # ==========================
    def record_trade(self):
        self.trades_taken += 1

    # ==========================
    # UPDATE PNL
    # ==========================
    def update_pnl(self, pnl):
        self.daily_pnl += pnl

        if self.daily_pnl <= -self.max_daily_loss:
            self.trading_blocked = True


    # ==========================
    # RESET DAY
    # ==========================
    def reset(self):
        self.trades_taken = 0
        self.daily_pnl = 0
        self.trading_blocked = False