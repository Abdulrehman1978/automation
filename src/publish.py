"""
Standalone publisher script.
Usage:
  python src/publish.py <json_package_file> <video_mp4_file>
"""
import sys
import json
import logging
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from upload.youtube_uploader import YouTubeUploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    if len(sys.argv) < 3:
        print("Usage: python src/publish.py <json_package_file> <video_mp4_file>")
        print("   OR: python src/publish.py link <db_id> <video_mp4_file>")
        sys.exit(1)

    db_id = None
    if sys.argv[1] == "link":
        db_id = sys.argv[2]
        video_file = sys.argv[3]
        if not os.path.exists(video_file):
            log.error(f"Video file not found: {video_file}")
            sys.exit(1)
            
        from core.database import Database
        db = Database()
        with db.conn() as c:
            row = c.execute("SELECT full_data FROM content_memory WHERE id = ?", (db_id,)).fetchone()
        if not row:
            log.error(f"No package found in DB for id {db_id}")
            sys.exit(1)
        package = json.loads(row["full_data"])
    else:
        json_file = sys.argv[1]
        video_file = sys.argv[2]

        if not os.path.exists(json_file):
            log.error(f"JSON file not found: {json_file}")
            sys.exit(1)
            
        if not os.path.exists(video_file):
            log.error(f"Video file not found: {video_file}")
            sys.exit(1)

        with open(json_file, 'r', encoding='utf-8') as f:
            package = json.load(f)

    print(f"Uploading '{package.get('final_title', 'Untitled')}' to YouTube...")
    uploader = YouTubeUploader()
    result = uploader.upload(package, video_file=video_file)

    if result.get("status") == "uploaded":
        print(f"\n✅ SUCCESS! Video is live (Private) at: {result.get('url')}")
        if db_id:
            with db.conn() as c:
                c.execute("""
                    UPDATE content_memory 
                    SET youtube_id = ?, video_path = ?
                    WHERE id = ?
                """, (result.get("id"), video_file, db_id))
            print(f"Database updated for content ID {db_id}")
    else:
        print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
