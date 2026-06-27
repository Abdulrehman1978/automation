import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from core.database import Database
from utils.notifier import notifier

log = logging.getLogger(__name__)

def run_health_check(hours=26):
    db = Database()
    with db.conn() as c:
        # Check if the last completed run is older than 'hours'
        row = c.execute("""
            SELECT completed_at 
            FROM pipeline_runs 
            WHERE status = 'completed' 
            ORDER BY completed_at DESC 
            LIMIT 1
        """).fetchone()

        if row and row["completed_at"]:
            last_run = datetime.fromisoformat(row["completed_at"])
            delta = datetime.utcnow() - last_run
            if delta.total_seconds() > hours * 3600:
                msg = f"⚠️ <b>Pipeline Health Alert</b>\n"
                msg += f"No successful run in the last {hours} hours!\n"
                msg += f"Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                log.warning("Health check failed. Sending alert.")
                notifier.send_message(msg)
            else:
                log.info("Health check passed. Pipeline is active.")
        else:
            log.info("No completed runs found yet.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_health_check()
