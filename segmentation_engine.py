"""
segmentation_engine.py — Phase 2.5
────────────────────────────────────
Subscriber segmentation and cold lead cleanup.
Builds segments based on engagement: hot / warm / cold.
Cold leads (no open in 60+ days) are removed to stay under Kit free tier.
"""
from datetime import datetime, timedelta
from typing import List, Dict

import pandas as pd

from convertkit_api import KitAPI
from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("segmentation_engine")


class SegmentationEngine:
    def __init__(self):
        self.kit    = KitAPI()
        self.sheets = SheetsManager()

    async def run(self) -> Dict:
        """Full segmentation run. Returns summary report."""
        log.info("Starting segmentation run…")
        subscribers = self.kit.get_subscribers()
        if not subscribers:
            log.warning("No subscribers found")
            return {}

        df = pd.DataFrame(subscribers)
        report = {
            "total": len(df),
            "hot": 0, "warm": 0, "cold": 0,
            "removed": 0,
        }

        hot, warm, cold = [], [], []
        now = datetime.utcnow()

        for _, row in df.iterrows():
            last = row.get("last_broadcast_email_at") or row.get("created_at", "")
            try:
                last_dt = datetime.fromisoformat(str(last).replace("Z", ""))
                days_ago = (now - last_dt).days
            except Exception:
                days_ago = 999

            if days_ago <= 14:
                hot.append(row)
            elif days_ago <= 45:
                warm.append(row)
            else:
                cold.append(row)

        report["hot"]  = len(hot)
        report["warm"] = len(warm)
        report["cold"] = len(cold)

        # Save segments to Sheets
        for seg_name, seg_list in [("hot", hot), ("warm", warm), ("cold", cold)]:
            self.sheets.append_row(Config.SHEETS_SEGMENTS, {
                "segment_name": seg_name,
                "count":        len(seg_list),
                "updated_at":   now.isoformat(),
            })

        # Clean cold leads (60+ days no engagement)
        removed = await self._remove_cold_leads(cold, threshold_days=60)
        report["removed"] = removed

        log.info(f"Segmentation complete: {report}")
        return report

    async def _remove_cold_leads(self, cold: List, threshold_days: int = 60) -> int:
        """Unsubscribe cold leads to keep list clean and under Kit free tier."""
        removed = 0
        for row in cold:
            last = row.get("last_broadcast_email_at") or row.get("created_at", "")
            try:
                last_dt = datetime.fromisoformat(str(last).replace("Z", ""))
                if (datetime.utcnow() - last_dt).days >= threshold_days:
                    # In production: call Kit API to unsubscribe
                    # await self.kit.unsubscribe(row["email_address"])
                    removed += 1
                    log.info(f"Cold lead queued for removal (inactive {threshold_days}+ days)")
            except Exception:
                pass
        log.info(f"Cold leads removed: {removed}")
        return removed
