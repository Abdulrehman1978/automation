"""
Run this script manually in your terminal to authenticate with YouTube.
Usage: python auth_youtube.py
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def main():
    from upload.youtube_uploader import YouTubeUploader
    print("="*60)
    print("YouTube Authentication Setup")
    print("="*60)
    print("Starting YouTube client. If a browser window opens, please log in.")
    
    uploader = YouTubeUploader()
    
    token_file = Path("credentials/youtube_token.json")
    if token_file.exists():
        print("\n✅ Authentication successful! Token saved to credentials/youtube_token.json")
        print("You can now use Viral OS to upload videos directly to YouTube.")
    else:
        print("\n❌ Authentication failed or was skipped.")

if __name__ == "__main__":
    main()
