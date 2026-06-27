import os
import sys
import logging
from pathlib import Path

src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from apscheduler.schedulers.background import BackgroundScheduler
import time
from core.orchestrator import Orchestrator

log = logging.getLogger(__name__)

def run_pipeline_job():
    log.info("Starting scheduled pipeline run...")
    orchestrator = Orchestrator()
    try:
        orchestrator.run()
    except Exception as e:
        log.error(f"Scheduled pipeline run failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    scheduler = BackgroundScheduler()
    # Schedule the pipeline to run twice a day
    scheduler.add_job(run_pipeline_job, 'cron', hour='9,17', minute=0)
    scheduler.start()
    
    log.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        log.info("Scheduler shutdown.")
