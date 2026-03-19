"""
convertkit_api.py — Phase 1/2
───────────────────────────────
Kit (ConvertKit) API wrapper.
Rate limit: 120 req/min → 0.5s between requests.
"""
import time
import requests
from typing import Optional, List

from config import Config
from utils.logger import get_logger

log = get_logger("convertkit_api")

BASE_URL = "https://api.convertkit.com/v3"


class KitAPI:
    def __init__(self):
        self.api_key    = Config.KIT_API_KEY
        self.api_secret = Config.KIT_API_SECRET

    def _get(self, endpoint: str, params: dict = None) -> dict:
        time.sleep(0.5)
        params = params or {}
        params["api_key"] = self.api_key
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        time.sleep(0.5)
        data["api_secret"] = self.api_secret
        resp = requests.post(f"{BASE_URL}/{endpoint}", json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    async def add_subscriber(self, email: str, tags: List[str] = None, first_name: str = "") -> Optional[int]:
        """Add or update a subscriber. Returns subscriber ID."""
        try:
            result = self._post("subscribers", {
                "email":      email,
                "first_name": first_name,
            })
            subscriber_id = result.get("subscriber", {}).get("id")
            if subscriber_id and tags:
                for tag in tags:
                    await self.add_tag(email, tag)
            log.info(f"Subscriber added/updated: ID {subscriber_id}")
            return subscriber_id
        except Exception as e:
            log.error(f"Kit add_subscriber failed: {e}")
            return None

    async def add_tag(self, email: str, tag_name: str) -> bool:
        """Add a tag to a subscriber. Creates tag if it doesn't exist."""
        try:
            # Get or create tag
            tags = self._get("tags").get("tags", [])
            tag = next((t for t in tags if t["name"] == tag_name), None)
            if not tag:
                tag = self._post("tags", {"name": tag_name}).get("tag", {})
            tag_id = tag.get("id")
            if not tag_id:
                return False
            self._post(f"tags/{tag_id}/subscribe", {"email": email})
            log.info(f"Tag '{tag_name}' applied to {email[:4]}***")
            return True
        except Exception as e:
            log.error(f"Kit add_tag failed: {e}")
            return False

    async def send_broadcast(self, subject: str, body: str, segment_id: Optional[int] = None) -> bool:
        """Send a broadcast email. Returns success."""
        try:
            payload = {
                "subject":    subject,
                "content":    body,
                "email_layout_template": "default",
            }
            if segment_id:
                payload["subscriber_filter"] = [{"all": [{"type": "segment", "value": segment_id}]}]
            self._post("broadcasts", payload)
            log.info(f"Broadcast sent: {subject[:50]}")
            return True
        except Exception as e:
            log.error(f"Kit send_broadcast failed: {e}")
            return False

    def get_subscribers(self, tag: str = None) -> List[dict]:
        """Fetch subscriber list, optionally filtered by tag."""
        try:
            params = {}
            if tag:
                params["tag_name"] = tag
            return self._get("subscribers", params).get("subscribers", [])
        except Exception as e:
            log.error(f"Kit get_subscribers failed: {e}")
            return []
