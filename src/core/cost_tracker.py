import logging
from datetime import datetime
from core.database import Database

log = logging.getLogger(__name__)

class CostTracker:
    def __init__(self):
        self.db = Database()

    def log_usage(self, provider: str, endpoint: str, tokens: int, requests: int, run_id: str = "manual"):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log.info(f"[{provider}] Endpoint: {endpoint} | Tokens: {tokens} | Requests: {requests}")
        with self.db.conn() as c:
            c.execute("""
                INSERT INTO api_usage (provider, endpoint, tokens_used, requests_made, date, run_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (provider, endpoint, tokens, requests, today, run_id))

