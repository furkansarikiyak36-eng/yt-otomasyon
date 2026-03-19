"""
youtube_uploader.py — Phase 1/2
─────────────────────────────────
Uploads videos as DRAFT to the correct YouTube channel.
Each channel has its own encrypted OAuth refresh token.
"""
import os
import json
from typing import Optional, Dict

from cryptography.fernet import Fernet
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("youtube_uploader")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    def __init__(self):
        self.sheets = SheetsManager()
        self._fernet = Fernet(Config.FERNET_KEY.encode()) if Config.FERNET_KEY else None

    # ── Main upload ──────────────────────────────────────────────
    async def upload_draft(
        self,
        job_id: str,
        video_path: str,
        metadata: Dict,
        channel_id: str,
    ) -> Optional[str]:
        """
        Upload video as PRIVATE draft to specified channel.
        Returns YouTube video ID or None on failure.
        """
        log.info(f"Uploading draft for job {job_id} → channel {channel_id}")

        # Get channel credentials
        creds = self._get_channel_credentials(channel_id)
        if not creds:
            log.error(f"No credentials found for channel {channel_id}")
            return None

        try:
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title":       metadata.get("title", "Draft Video"),
                    "description": metadata.get("description", ""),
                    "tags":        metadata.get("tags", []),
                    "categoryId":  "26",  # Howto & Style
                },
                "status": {
                    "privacyStatus":  "private",   # Draft — not public
                    "selfDeclaredMadeForKids": False,
                }
            }

            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024 * 10  # 10MB chunks
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    log.info(f"Upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id")
            log.info(f"Uploaded as draft: https://studio.youtube.com/video/{video_id}/edit")

            # Upload thumbnail if available
            thumb = metadata.get("thumbnail")
            if thumb and os.path.exists(thumb):
                self._upload_thumbnail(youtube, video_id, thumb)

            return video_id

        except Exception as e:
            log.error(f"YouTube upload failed for {job_id}: {e}")
            return None

    def _upload_thumbnail(self, youtube, video_id: str, thumb_path: str):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_path, mimetype="image/jpeg")
            ).execute()
            log.info(f"Thumbnail uploaded for {video_id}")
        except Exception as e:
            log.warning(f"Thumbnail upload failed: {e}")

    # ── Channel credential management ────────────────────────────
    def _get_channel_credentials(self, channel_id: str) -> Optional[Credentials]:
        """Load and decrypt OAuth credentials for a channel."""
        channels = self.sheets.read_all(Config.SHEETS_CHANNELS)
        channel = next((c for c in channels if c.get("channel_id") == channel_id), None)
        if not channel:
            log.error(f"Channel {channel_id} not found in database")
            return None

        encrypted_token = channel.get("refresh_token")
        if not encrypted_token or not self._fernet:
            log.error("Cannot decrypt refresh token — FERNET_KEY not set or token missing")
            return None

        try:
            refresh_token = self._fernet.decrypt(encrypted_token.encode()).decode()
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=SCOPES,
            )
            # Refresh to get access token
            creds.refresh(Request())
            log.info(f"Credentials loaded for channel {channel_id}")
            return creds
        except Exception as e:
            log.error(f"Credential decryption/refresh failed: {e}")
            return None

    def save_channel_credentials(self, channel_id: str, channel_name: str, refresh_token: str):
        """Encrypt and save a new channel's refresh token."""
        if not self._fernet:
            raise ValueError("FERNET_KEY not configured")
        encrypted = self._fernet.encrypt(refresh_token.encode()).decode()
        self.sheets.append_row(Config.SHEETS_CHANNELS, {
            "channel_id":   channel_id,
            "channel_name": channel_name,
            "refresh_token": encrypted,
            "status":       "active",
        })
        log.info(f"Channel {channel_name} ({channel_id}) credentials saved")
