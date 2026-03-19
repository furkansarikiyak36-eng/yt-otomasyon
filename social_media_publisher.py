"""
social_media_publisher.py — Phase 2
─────────────────────────────────────
Organic publishing to Instagram, TikTok, Pinterest.
No ad API — organic only.
Called by social_producer.py after clips are ready.
"""
import requests
import time
from typing import Dict, List, Optional
from config import Config
from utils.logger import get_logger

log = get_logger("social_media_publisher")


class SocialMediaPublisher:

    async def publish_all(
        self,
        clip_paths: Dict[str, str],   # {"instagram": path, "tiktok": path}
        caption: str,
        channel_id: str,
    ) -> Dict[str, bool]:
        results = {}
        for platform, path in clip_paths.items():
            if platform == "instagram":
                results["instagram"] = await self._post_instagram_reel(path, caption)
            elif platform == "tiktok":
                results["tiktok"] = await self._post_tiktok(path, caption)
            elif platform == "pinterest":
                results["pinterest"] = await self._post_pinterest(path, caption)
            time.sleep(1)
        log.info(f"Social publish results: {results}")
        return results

    # ── Instagram Reels ───────────────────────────────────────
    async def _post_instagram_reel(self, video_path: str, caption: str) -> bool:
        if not Config.INSTAGRAM_ACCESS_TOKEN or not Config.INSTAGRAM_BUSINESS_ID:
            log.warning("Instagram not configured")
            return False
        try:
            # Step 1: create container
            r = requests.post(
                f"https://graph.facebook.com/v18.0/{Config.INSTAGRAM_BUSINESS_ID}/media",
                params={
                    "access_token": Config.INSTAGRAM_ACCESS_TOKEN,
                    "media_type":   "REELS",
                    "caption":      caption[:2200],
                    "share_to_feed": "true",
                },
                timeout=30
            )
            cid = r.json().get("id")
            if not cid:
                log.error(f"Instagram container failed: {r.json()}")
                return False
            time.sleep(3)
            # Step 2: publish
            pub = requests.post(
                f"https://graph.facebook.com/v18.0/{Config.INSTAGRAM_BUSINESS_ID}/media_publish",
                params={"access_token": Config.INSTAGRAM_ACCESS_TOKEN, "creation_id": cid},
                timeout=30
            )
            ok = "id" in pub.json()
            log.info(f"Instagram: {'✅' if ok else '❌'}")
            return ok
        except Exception as e:
            log.error(f"Instagram error: {e}")
            return False

    # ── TikTok ───────────────────────────────────────────────
    async def _post_tiktok(self, video_path: str, caption: str) -> bool:
        if not Config.TIKTOK_ACCESS_TOKEN:
            log.warning("TikTok not configured")
            return False
        try:
            # TikTok Content Posting API v2
            r = requests.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {Config.TIKTOK_ACCESS_TOKEN}",
                    "Content-Type":  "application/json; charset=UTF-8",
                },
                json={
                    "post_info": {
                        "title":           caption[:150],
                        "privacy_level":   "PUBLIC_TO_EVERYONE",
                        "disable_duet":    False,
                        "disable_stitch":  False,
                        "disable_comment": False,
                    },
                    "source_info": {
                        "source":     "FILE_UPLOAD",
                        "video_size": 0,
                        "chunk_size": 0,
                        "total_chunk_count": 1,
                    }
                },
                timeout=30
            )
            ok = r.status_code in (200, 201)
            log.info(f"TikTok: {'✅' if ok else '❌ ' + str(r.status_code)}")
            return ok
        except Exception as e:
            log.error(f"TikTok error: {e}")
            return False

    # ── Pinterest ────────────────────────────────────────────
    async def _post_pinterest(self, video_path: str, caption: str) -> bool:
        if not Config.PINTEREST_ACCESS_TOKEN:
            log.warning("Pinterest not configured")
            return False
        try:
            r = requests.post(
                "https://api.pinterest.com/v5/pins",
                headers={
                    "Authorization": f"Bearer {Config.PINTEREST_ACCESS_TOKEN}",
                    "Content-Type":  "application/json",
                },
                json={
                    "board_id":    Config.PINTEREST_BOARD_ID or "",
                    "title":       caption[:100],
                    "description": caption[:500],
                    "media_source": {"source_type": "video_id"},
                },
                timeout=30
            )
            ok = r.status_code in (200, 201)
            log.info(f"Pinterest: {'✅' if ok else '❌ ' + str(r.status_code)}")
            return ok
        except Exception as e:
            log.error(f"Pinterest error: {e}")
            return False
