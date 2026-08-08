import sys
from datetime import datetime


class TradingSession:

    def __init__(self):
        self.started_at = datetime.now()
        self.ended = False
        self.end_reason = None
        self.feed = None

    def attach_feed(self, feed):
        self.feed = feed

    def end(self, reason):

        # Prevent multiple shutdown attempts
        if self.ended:
            return

        self.ended = True
        self.end_reason = reason

        print("\n" + "=" * 45)
        print(f"🏁 TRADING SESSION ENDED: {reason}")
        print("=" * 45)

        self.print_summary()

        self.shutdown()

    def print_summary(self):

        runtime = datetime.now() - self.started_at

        print("\n========== SESSION SUMMARY ==========")
        print(f"Started : {self.started_at}")
        print(f"Ended   : {datetime.now()}")
        print(f"Reason  : {self.end_reason}")
        print(f"Runtime : {runtime}")
        print("=====================================\n")

    def shutdown(self):

        print("🛑 Shutting down trading session...")

        if self.feed:
            self.feed.stop()

        sys.exit(0)