import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from googleapiclient.discovery import build
from analytics.oauth_setup import get_authenticated_service
from core.database import Database
from core.config import Config

log = logging.getLogger(__name__)

class AnalyticsIngester:
    def __init__(self):
        self.db = Database()
        self.youtube_data = None
        self.youtube_analytics = None
        self._init_services()

    def _init_services(self):
        """Initialize OAuth services, fallback to API key for Data API"""
        try:
            creds = get_authenticated_service()
            self.youtube_data = build("youtube", "v3", credentials=creds)
            self.youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)
            log.info("Initialized YouTube APIs with OAuth credentials.")
        except Exception as e:
            log.warning(f"OAuth failed ({e}). Falling back to public API key for Data API.")
            if Config.YOUTUBE_API_KEY:
                self.youtube_data = build("youtube", "v3", developerKey=Config.YOUTUBE_API_KEY)
            else:
                log.error("No YOUTUBE_API_KEY available. Analytics ingestion will fail.")

    def ingest_metrics(self):
        """Fetch metrics for videos uploaded within the last 30 days and update the database."""
        with self.db.conn() as c:
            # Get videos that have a youtube_id and were uploaded relatively recently
            videos = c.execute("""
                SELECT id, youtube_id, title 
                FROM content_memory 
                WHERE youtube_id IS NOT NULL 
                ORDER BY created_at DESC 
                LIMIT 50
            """).fetchall()

        if not videos:
            log.info("No videos with youtube_id found in database.")
            return

        for video in videos:
            metrics = self._fetch_video_metrics(video["youtube_id"])
            if metrics:
                self._update_db(video["id"], metrics)
                log.info(f"Updated metrics for '{video['title']}': {metrics}")
            else:
                log.warning(f"Could not fetch metrics for video: {video['youtube_id']}")

    def _fetch_video_metrics(self, video_id: str) -> dict:
        """Fetch view count, CTR, and AVD for a specific video"""
        metrics = {
            "views_30d": 0,
            "likes": 0,
            "comments": 0,
            "ctr": 0.0,
            "avg_watch_pct": 0.0
        }

        # 1. Fetch public stats using Data API
        if self.youtube_data:
            try:
                response = self.youtube_data.videos().list(
                    part="statistics",
                    id=video_id
                ).execute()
                
                if response.get("items"):
                    stats = response["items"][0]["statistics"]
                    metrics["views_30d"] = int(stats.get("viewCount", 0))
                    metrics["likes"] = int(stats.get("likeCount", 0))
                    metrics["comments"] = int(stats.get("commentCount", 0))
            except Exception as e:
                log.error(f"Data API error for {video_id}: {e}")

        # 2. Fetch advanced metrics using Analytics API (if OAuth available)
        if self.youtube_analytics:
            try:
                # Analytics API requires date ranges
                end_date = datetime.utcnow().strftime('%Y-%m-%d')
                start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                response = self.youtube_analytics.reports().query(
                    ids="channel==MINE",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="annotationClickThroughRate,averageViewPercentage", # approximating CTR
                    filters=f"video=={video_id}"
                ).execute()
                
                if response.get("rows"):
                    row = response["rows"][0]
                    # Note: YouTube API CTR is annotationClickThroughRate or impression click through rate (which might not be available directly).
                    # We'll map what we can.
                    metrics["ctr"] = float(row[0]) if len(row) > 0 else 0.0
                    metrics["avg_watch_pct"] = float(row[1]) if len(row) > 1 else 0.0
            except Exception as e:
                log.warning(f"Analytics API failed for {video_id}. (May require channel owner OAuth). {e}")

        return metrics

    def _update_db(self, db_id: int, metrics: dict):
        with self.db.conn() as c:
            c.execute("""
                UPDATE content_memory 
                SET views_30d = ?, likes = ?, comments = ?, ctr = ?, avg_watch_pct = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                metrics["views_30d"],
                metrics["likes"],
                metrics["comments"],
                metrics["ctr"],
                metrics["avg_watch_pct"],
                db_id
            ))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingester = AnalyticsIngester()
    ingester.ingest_metrics()
