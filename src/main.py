"""
Viral OS — Main Pipeline Runner
---------------------------------
Usage:
  python src/main.py                          # Single run (full pipeline)
  python src/main.py --workflow research idea judge script seo
  python src/main.py --schedule 6h            # Run every 6 hours
  python src/main.py --schedule 09:00         # Run daily at 9AM
  python src/main.py --channel my_channel     # Named channel
  python src/main.py --upload                 # Auto-save output packages
  python src/main.py --dashboard              # Start dashboard instead
"""
import argparse
import logging
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ensure src/ is in the Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("viral_os")

FULL_WORKFLOW = ["research", "idea", "judge", "script", "seo"]
FULL_WORKFLOW_WITH_LEARNING = ["learning", "research", "idea", "judge", "script", "seo", "experiment"]


def run_pipeline(
    channel_id: str = "main",
    workflow: list = None,
    save_output: bool = True,
    upload: bool = False,
    resume_run_id: str = None,
) -> dict:
    """Run the full pipeline once and return results."""
    from core.orchestrator import Orchestrator
    from upload.youtube_uploader import YouTubeUploader
    from core.database import Database

    workflow = workflow or FULL_WORKFLOW
    
    if resume_run_id == "latest":
        # Find latest incomplete run for this channel
        db = Database()
        with db.conn() as c:
            row = c.execute(
                "SELECT run_id FROM pipeline_runs WHERE channel_id = ? AND status = 'running' ORDER BY started_at DESC LIMIT 1",
                (channel_id,)
            ).fetchone()
            if row:
                resume_run_id = row["run_id"]
                log.info(f"Resuming latest incomplete run: {resume_run_id}")
            else:
                log.info("No incomplete run found to resume. Starting new run.")
                resume_run_id = None
                
    log.info(f"\n{'='*60}")
    log.info(f"  Viral OS Pipeline  |  Channel: {channel_id}")
    log.info(f"  Workflow: {' → '.join(workflow)}")
    if resume_run_id:
        log.info(f"  Resuming : {resume_run_id}")
    log.info(f"{'='*60}")

    orch = Orchestrator(channel_id=channel_id, resume_run_id=resume_run_id)
    results = orch.execute_workflow(workflow)

    # Print summary
    seo_packages = results.get("seo", {}).get("seo_packages", [])
    approved_ideas = results.get("judge", {}).get("approved_ideas", [])
    learning_summary = results.get("learning", {}).get("analysis_summary", "")

    log.info(f"\n  Results Summary:")
    log.info(f"   Ideas approved  : {len(approved_ideas)}")
    log.info(f"   Packages ready  : {len(seo_packages)}")
    if learning_summary:
        log.info(f"   Learning insight: {learning_summary[:100]}...")

    for pkg in seo_packages:
        log.info(f"\n   [{pkg.get('final_title')}]")
        log.info(f"     Tags    : {pkg.get('tags', [])[:5]}")
        log.info(f"     Post at : {pkg.get('best_posting_time', '—')}")
        log.info(f"     Hashtags: {' '.join(pkg.get('hashtags', []))}")

    # Save / upload
    if save_output and seo_packages:
        from upload.youtube_uploader import YouTubeUploader
        uploader = YouTubeUploader()
        upload_results = uploader.upload_batch(seo_packages)
        log.info(f"\n  Saved {len(upload_results)} package(s) to outputs/")
        for r in upload_results:
            status = r.get("status")
            if status == "uploaded":
                log.info(f"   LIVE  {r['title']} → {r['url']}")
            else:
                log.info(f"   SAVED {r['title']} → {r.get('saved_path','')}")

    log.info(f"\n  Pipeline complete at {datetime.now().strftime('%H:%M:%S')}")
    return results


def run_scheduled(
    interval_str: str,
    channel_id: str,
    workflow: list,
    save_output: bool,
):
    """Run the pipeline on a recurring schedule."""

    def parse_interval(s: str):
        """Parse '6h', '30m', '1d', or 'HH:MM' into seconds."""
        s = s.strip().lower()
        if s.endswith("h"):
            return int(s[:-1]) * 3600
        if s.endswith("m"):
            return int(s[:-1]) * 60
        if s.endswith("d"):
            return int(s[:-1]) * 86400
        if ":" in s:
            # Run daily at a specific time — calculate seconds until next occurrence
            h, m = map(int, s.split(":"))
            now = datetime.now()
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return (target - now).seconds
        raise ValueError(f"Cannot parse interval: {s}")

    log.info(f"Scheduled mode: {interval_str}")

    while True:
        run_pipeline(channel_id=channel_id, workflow=workflow, save_output=save_output)

        interval_secs = parse_interval(interval_str)
        next_run = datetime.now() + timedelta(seconds=interval_secs)
        log.info(f"  Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"  Sleeping for {interval_secs // 3600}h {(interval_secs % 3600) // 60}m...")
        time.sleep(interval_secs)


def start_dashboard(host: str = "0.0.0.0", port: int = 5000):
    """Start the Flask dashboard."""
    from dashboard.app import app
    log.info(f"\n  Viral OS Dashboard → http://localhost:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)


def main():
    parser = argparse.ArgumentParser(description="Viral OS — Content Generation Pipeline")
    parser.add_argument("--channel", default="main", help="Channel ID (default: main)")
    parser.add_argument("--workflow", nargs="+", default=None,
                        help="Steps to run (default: full pipeline)")
    parser.add_argument("--with-learning", action="store_true",
                        help="Include learning and experiment steps")
    parser.add_argument("--schedule", default=None,
                        help="Run on a schedule: e.g. 6h, 30m, 1d, or 09:00")
    parser.add_argument("--upload", action="store_true",
                        help="Save output packages (default: True)")
    parser.add_argument("--no-save", action="store_true",
                        help="Don't save output packages")
    parser.add_argument("--dashboard", action="store_true",
                        help="Start the web dashboard instead of running the pipeline")
    parser.add_argument("--resume", nargs="?", const="latest", default=None,
                        help="Resume an incomplete run (optionally pass run_id, otherwise finds latest)")
    parser.add_argument("--port", type=int, default=5000,
                        help="Dashboard port (default: 5000)")
    args = parser.parse_args()

    if args.dashboard:
        start_dashboard(port=args.port)
        return

    workflow = args.workflow
    if workflow is None:
        workflow = FULL_WORKFLOW_WITH_LEARNING if args.with_learning else FULL_WORKFLOW

    save_output = not args.no_save

    if args.schedule:
        run_scheduled(
            interval_str=args.schedule,
            channel_id=args.channel,
            workflow=workflow,
            save_output=save_output,
        )
    else:
        run_pipeline(
            channel_id=args.channel,
            workflow=workflow,
            save_output=save_output,
            resume_run_id=args.resume,
        )


if __name__ == "__main__":
    main()
