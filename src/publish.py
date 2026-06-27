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
        sys.exit(1)

    json_file = sys.argv[1]
    video_file = sys.argv[2]

    if not os.path.exists(json_file):
        print(f"Error: JSON file not found: {json_file}")
        sys.exit(1)
        
    if not os.path.exists(video_file):
        print(f"Error: Video file not found: {video_file}")
        sys.exit(1)

    with open(json_file, 'r', encoding='utf-8') as f:
        package = json.load(f)

    print(f"Uploading '{package.get('final_title', 'Untitled')}' to YouTube...")
    uploader = YouTubeUploader()
    result = uploader.upload(package, video_file=video_file)

    if result.get("status") == "uploaded":
        print(f"\n✅ SUCCESS! Video is live (Private) at: {result.get('url')}")
    else:
        print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
