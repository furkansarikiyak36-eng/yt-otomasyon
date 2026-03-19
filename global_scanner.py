"""
global_scanner.py — Phase 1/2/3
─────────────────────────────────
MINDFULLY BRAND — Channel-aware trend scanner.

Channel 1 (Fitness)     : fitness keywords → Mon/Wed/Fri
Channel 2 (Ambiance)    : ambiance/lofi keywords → Tue/Thu
Channel 3 (Documentary) : health science keywords → Sat

Phase 1: Weekly  | Phase 2: Daily  | Phase 3: Hourly
Sources: Google Trends, YouTube Trending, Reddit
"""
import time
import requests
from datetime import datetime
from typing import List, Dict

from pytrends.request import TrendReq
import praw

from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("global_scanner")


class GlobalScanner:
    def __init__(self):
        self.sheets = SheetsManager()
        self._pytrends = TrendReq(hl="en-US", tz=360)

    # ── Main entry point ─────────────────────────────────────────
    async def run_weekly_scan(self, keywords: List[str] = None,
                              channel_id: str = None) -> List[Dict]:
        """
        Full weekly trend scan. If channel_id given, uses that channel's
        keywords and tags results with channel_id.
        """
        from config import Config
        if channel_id:
            keywords = keywords or Config.get_channel_keywords(channel_id)
            ch_name  = Config.get_channel(channel_id).get("name", channel_id)
            log.info(f"Trend scan for channel: {ch_name} ({len(keywords)} keywords)")
        else:
            keywords = keywords or self._default_keywords()
            channel_id = "all"
            log.info("Trend scan for all channels")

        results = []
        results += self._scan_google_trends(keywords)
        results += self._scan_youtube_trending()
        results += self._scan_reddit()
        results = self._deduplicate_and_score(results)

        # Tag each result with channel_id
        for r in results:
            r["channel_id"] = channel_id

        self._save_to_sheets(results)
        log.info(f"Scan complete for {channel_id}: {len(results)} opportunities")
        return results

    async def run_realtime_scan(self, keywords: List[str] = None) -> List[Dict]:
        """Lightweight hourly scan for Phase 3."""
        results = self._scan_google_trends(keywords or self._default_keywords(), timeframe="now 1-d")
        results = self._deduplicate_and_score(results)
        self._save_to_sheets(results)
        return results

    # ── Google Trends ────────────────────────────────────────────
    def _scan_google_trends(self, keywords: List[str], timeframe: str = "now 7-d") -> List[Dict]:
        results = []
        for kw in keywords:
            try:
                time.sleep(2)  # respectful rate limiting
                self._pytrends.build_payload([kw], timeframe=timeframe, geo="")
                interest = self._pytrends.interest_over_time()
                if interest.empty:
                    continue
                avg_interest = int(interest[kw].mean())
                related = self._pytrends.related_queries()
                rising = []
                if related and kw in related and related[kw].get("rising") is not None:
                    rising = related[kw]["rising"]["query"].head(5).tolist()
                results.append({
                    "source": "google_trends",
                    "topic": kw,
                    "popularity": avg_interest,
                    "related": ", ".join(rising),
                    "date": datetime.utcnow().isoformat(),
                    "growth_rate": "rising" if avg_interest > 50 else "stable",
                    "competition": "medium",
                    "product_potential": "high" if avg_interest > 60 else "medium",
                })
                log.info(f"Google Trends: {kw} → popularity {avg_interest}")
            except Exception as e:
                log.warning(f"Google Trends failed for '{kw}': {e}")
        return results

    # ── YouTube Trending ─────────────────────────────────────────
    def _scan_youtube_trending(self, region_code: str = "US") -> List[Dict]:
        """Uses YouTube Data API to fetch trending videos."""
        if not Config.PEXELS_API_KEY:  # placeholder check
            log.info("YouTube API key not configured — skipping YouTube trending")
            return []
        results = []
        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=Config.PEXELS_API_KEY)
            response = youtube.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=region_code,
                videoCategoryId="26",  # Howto & Style
                maxResults=20
            ).execute()
            for item in response.get("items", []):
                snippet = item["snippet"]
                stats   = item.get("statistics", {})
                results.append({
                    "source": "youtube_trending",
                    "topic": snippet["title"],
                    "popularity": min(int(int(stats.get("viewCount", 0)) / 10000), 100),
                    "related": snippet.get("tags", [""])[0] if snippet.get("tags") else "",
                    "date": datetime.utcnow().isoformat(),
                    "growth_rate": "trending",
                    "competition": "high",
                    "product_potential": "medium",
                })
            log.info(f"YouTube Trending: {len(results)} videos fetched")
        except Exception as e:
            log.warning(f"YouTube Trending scan failed: {e}")
        return results

    # ── Reddit ───────────────────────────────────────────────────
    def _scan_reddit(self, subreddits: List[str] = None) -> List[Dict]:
        subreddits = subreddits or [
            "wellness", "meditation", "fitness", "nutrition",
            "selfimprovement", "productivity", "health"
        ]
        results = []
        try:
            reddit = praw.Reddit(
                client_id="YOUR_CLIENT_ID",       # set in .env
                client_secret="YOUR_SECRET",       # set in .env
                user_agent="yt-automation/1.0"
            )
            for sub in subreddits:
                time.sleep(1)
                try:
                    subreddit = reddit.subreddit(sub)
                    for post in subreddit.hot(limit=5):
                        results.append({
                            "source": f"reddit/{sub}",
                            "topic": post.title,
                            "popularity": min(post.score // 100, 100),
                            "related": sub,
                            "date": datetime.utcnow().isoformat(),
                            "growth_rate": "stable",
                            "competition": "low",
                            "product_potential": "medium",
                        })
                except Exception as e:
                    log.warning(f"Reddit scan failed for r/{sub}: {e}")
            log.info(f"Reddit: {len(results)} posts scanned")
        except Exception as e:
            log.warning(f"Reddit init failed: {e}")
        return results

    # ── Helpers ──────────────────────────────────────────────────
    def _default_keywords(self) -> List[str]:
        return [
            "meditation for anxiety", "vagus nerve exercises",
            "gut health tips", "morning routine", "stress relief",
            "sleep better naturally", "breathwork", "mindfulness",
        ]

    def _deduplicate_and_score(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for r in results:
            key = r["topic"].lower()[:40]
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return sorted(unique, key=lambda x: x.get("popularity", 0), reverse=True)

    def _save_to_sheets(self, results: List[Dict]):
        for r in results:
            self.sheets.append_row(Config.SHEETS_TREND_DATA, r)
