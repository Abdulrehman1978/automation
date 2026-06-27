"""
YouTube Uploader
----------------
Uploads video files to YouTube using the YouTube Data API v3.
Also saves approved content packages as JSON output ready for
manual upload or downstream automation.

Required for live uploads:
  YOUTUBE_API_KEY or OAuth2 credentials in credentials/youtube_oauth.json

For MVP without credentials: saves packages to outputs/ only.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "credentials"


class YouTubeUploader:
    """
    Handles both mock uploads (save to disk) and real YouTube API uploads.

    Real upload requires:
      1. YouTube Data API v3 enabled in Google Cloud Console
      2. OAuth2 credentials downloaded as credentials/youtube_oauth.json
      3. Run with --auth flag once to complete OAuth flow
    """

    def __init__(self):
        self._youtube = None
        self._init_api()
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    def _init_api(self):
        """Try to initialise the YouTube API client."""
        creds_file = CREDENTIALS_DIR / "youtube_oauth.json"
        token_file = CREDENTIALS_DIR / "youtube_token.json"

        if not creds_file.exists():
            log.info(
                "YouTube OAuth credentials not found at credentials/youtube_oauth.json. "
                "Running in save-only mode (outputs will be saved as JSON)."
            )
            return

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
            creds = None

            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(token_file, "w") as tf:
                    tf.write(creds.to_json())

            self._youtube = build("youtube", "v3", credentials=creds)
            log.info("YouTube API client initialised (live uploads enabled)")

        except Exception as e:
            log.warning(f"Could not init YouTube API: {e}. Using save-only mode.")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def upload(self, package: dict, video_file: str = None) -> dict:
        """
        Upload a content package to YouTube or save it for manual upload.

        Args:
            package: SEO package dict with final_title, description, tags, etc.
            video_file: Path to the video file. If None, saves package JSON only.

        Returns:
            Dict with 'status', 'video_id' (if live), 'saved_path'.
        """
        title = package.get("final_title", "Untitled")

        # Always save the package JSON
        saved_path = self._save_package(package)

        if self._youtube and video_file and os.path.exists(video_file):
            return self._upload_live(package, video_file, saved_path)

        log.info(f"[YouTube] Saved package for manual upload: {title}")
        return {
            "status": "saved",
            "video_id": None,
            "saved_path": str(saved_path),
            "title": title,
        }

    def upload_batch(self, seo_packages: list, video_files: dict = None) -> list:
        """
        Upload or save a batch of SEO packages.

        Args:
            seo_packages: List of SEO package dicts.
            video_files: Optional dict mapping title → video file path.

        Returns:
            List of upload result dicts.
        """
        results = []
        video_files = video_files or {}
        for pkg in seo_packages:
            title = pkg.get("final_title", "")
            video_file = video_files.get(title)
            result = self.upload(pkg, video_file)
            results.append(result)
        return results

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _save_package(self, package: dict) -> Path:
        """Save the content package as a JSON file in outputs/."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in package.get("final_title", "untitled")
                             if c.isalnum() or c in " _-")[:40].strip().replace(" ", "_")
        filename = f"upload_{safe_title}_{timestamp}.json"
        file_path = OUTPUTS_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, ensure_ascii=False, default=str)
        return file_path

    def _upload_live(self, package: dict, video_file: str, saved_path: Path) -> dict:
        """Perform the actual YouTube API upload."""
        try:
            from googleapiclient.http import MediaFileUpload

            title = package.get("final_title", "Untitled")
            description = package.get("description", "")
            tags = package.get("tags", [])
            # Add hashtags to description
            hashtags = " ".join(package.get("hashtags", []))
            full_description = f"{description}\n\n{hashtags}"

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": full_description[:5000],
                    "tags": tags[:30],
                    "categoryId": "28",   # Science & Technology
                    "defaultLanguage": "en",
                },
                "status": {
                    "privacyStatus": "private",   # Start as private — review before publishing
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(
                video_file,
                mimetype="video/*",
                resumable=True,
                chunksize=1024 * 1024 * 5,  # 5MB chunks
            )

            request = self._youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                _, response = request.next_chunk()

            video_id = response.get("id")
            log.info(f"[YouTube] Uploaded '{title}' as private → https://youtu.be/{video_id}")
            return {
                "status": "uploaded",
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
                "saved_path": str(saved_path),
                "title": title,
            }

        except Exception as e:
            log.error(f"[YouTube] Upload failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "saved_path": str(saved_path),
                "title": package.get("final_title"),
            }
