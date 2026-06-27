import os
import pickle
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path

# Scopes needed for YouTube Analytics and Data API
SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly"
]

log = logging.getLogger(__name__)

def get_authenticated_service():
    """
    Authenticate with OAuth and return credentials.
    Requires client_secrets.json in the data directory.
    """
    creds = None
    token_path = Path("data/token.pickle")
    client_secrets_path = Path(os.path.expanduser("~/Downloads/client_secrets.json"))
    
    # Try alternate location if not in downloads
    if not client_secrets_path.exists():
        client_secrets_path = Path("data/client_secrets.json")

    # Load existing token
    if token_path.exists():
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                log.warning(f"Failed to refresh token: {e}")
                creds = None
        
        if not creds:
            if not client_secrets_path.exists():
                raise FileNotFoundError(
                    f"Missing client_secrets.json at {client_secrets_path}. "
                    "Please download it from Google Cloud Console and place it there."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return creds

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        creds = get_authenticated_service()
        log.info("OAuth setup completed successfully. Token saved to data/token.pickle.")
    except Exception as e:
        log.error(f"OAuth setup failed: {e}")
