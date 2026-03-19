"""
opportunity_reporter.py — Phase 3
───────────────────────────────────
Weekly opportunity digest sent via Telegram.
Aggregates trend data and scores opportunities by channel.
"""
from typing import Dict, List
from datetime import datetime, timedelta
from sheets_manager import SheetsManager
from config import Config
from utils.logger import get_logger

log = get_logger("opportunity_reporter")


class OpportunityReporter:
    def __init__(self, telegram_handler=None):
        self.tg     = telegram_handler
        self.sheets = SheetsManager()

    async def generate_and_send(self) -> Dict:
        """Generate weekly opportunity report and send to Telegram."""
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        trends   = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        recent   = [t for t in trends if t.get("date", "") >= week_ago]

        if not recent:
            recent = trends[:20]

        # Score and rank
        scored = sorted(
            recent,
            key=lambda x: int(x.get("popularity", 0)),
            reverse=True
        )[:10]

        # Group by channel
        opps_by_channel = {cid: [] for cid in Config.get_all_channel_ids()}
        for t in scored:
            channel_id = t.get("channel_id", "all")
            if channel_id == "all":
                for cid in opps_by_channel:
                    ch = Config.get_channel(cid)
                    kws = ch.get("keywords", [])
                    topic_lower = t.get("topic", "").lower()
                    if any(k.lower() in topic_lower for k in kws):
                        opps_by_channel[cid].append(t)
                        break
                else:
                    list(opps_by_channel.values())[0].append(t)
            elif channel_id in opps_by_channel:
                opps_by_channel[channel_id].append(t)

        report = {
            "week":         datetime.utcnow().strftime("%Y-W%V"),
            "total_trends": len(recent),
            "top_scored":   scored[:5],
            "by_channel":   opps_by_channel,
        }

        # Save to Sheets
        for opp in scored[:5]:
            self.sheets.append_row(Config.SHEETS_OPPORTUNITIES, {
                "id":          f"opp_{datetime.utcnow().strftime('%Y%m%d')}_{opp.get('topic','')[:20]}",
                "topic":       opp.get("topic"),
                "score":       opp.get("popularity"),
                "status":      "pending",
                "channel_id":  opp.get("channel_id", "all"),
                "created_at":  datetime.utcnow().isoformat(),
            })

        # Send Telegram message
        if self.tg:
            await self.tg.send_message(self._format_message(report))

        log.info(f"Opportunity report sent: {len(scored)} opportunities")
        return report

    def _format_message(self, report: Dict) -> str:
        lines = [f"📊 <b>Weekly Opportunity Report — {report['week']}</b>\n"]

        for cid in Config.get_all_channel_ids():
            ch   = Config.get_channel(cid)
            opps = report["by_channel"].get(cid, [])[:3]
            if not opps:
                continue
            lines.append(f"\n<b>{ch['name']}</b>")
            for o in opps:
                pop = o.get("popularity", 0)
                stars = "🔥" if int(pop) >= 70 else "📈" if int(pop) >= 40 else "💡"
                lines.append(f"  {stars} {o.get('topic')} ({pop}/100)")

        lines.append(f"\n<i>Total trends analyzed: {report['total_trends']}</i>")
        return "\n".join(lines)
