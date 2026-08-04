import sys
from datetime import datetime


class TradingSession:

    def __init__(self):
        self.started_at = datetime.now()

    def end(self, reason):
        print(f"\n🏁 SESSION ENDED: {reason}")

        self.print_summary(reason)

        self.shutdown()

    def print_summary(self, reason):
        runtime = datetime.now() - self.started_at

        print("\n========== SESSION SUMMARY ==========")
        print("Reason :", reason)
        print("Runtime:", runtime)
        print("=====================================\n")

    def shutdown(self):
        print("👋 Shutting down trading session...")
        sys.exit(0)