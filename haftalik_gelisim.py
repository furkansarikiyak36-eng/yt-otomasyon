"""
haftalik_gelisim.py — Phase 3
───────────────────────────────
Weekly progress analysis and improvement recommendations.
Compares this week vs last week across all channels.
Sent every Sunday at 10:00 via Telegram.
"""
from typing import Dict
from datetime import datetime, timedelta
from sheets_manager import SheetsManager
from ai_synthesizer import AISynthesizer
from config import Config
from utils.logger import get_logger

log = get_logger("haftalik_gelisim")


class HaftalikGelisim:
    def __init__(self, telegram_handler=None):
        self.tg     = telegram_handler
        self.sheets = SheetsManager()
        self.ai     = AISynthesizer()

    async def generate_and_send(self) -> Dict:
        """Full weekly progress report — compare weeks, generate recommendations."""
        now      = datetime.utcnow()
        week_ago = (now - timedelta(days=7)).isoformat()
        two_weeks_ago = (now - timedelta(days=14)).isoformat()

        videos   = self.sheets.read_all(Config.SHEETS_VIDEO_LOG)
        sales    = self.sheets.read_all(Config.SHEETS_SALES)
        subs     = self.sheets.read_all(Config.SHEETS_EMAIL_SUBSCRIBERS)

        # This week vs last week
        this_week_videos  = [v for v in videos if v.get("publish_date","") >= week_ago]
        last_week_videos  = [v for v in videos if two_weeks_ago <= v.get("publish_date","") < week_ago]
        this_week_sales   = sum(float(s.get("amount",0)) for s in sales if s.get("date","") >= week_ago)
        last_week_sales   = sum(float(s.get("amount",0)) for s in sales if two_weeks_ago <= s.get("date","") < week_ago)
        this_week_subs    = len([s for s in subs if s.get("created_at","") >= week_ago])
        last_week_subs    = len([s for s in subs if two_weeks_ago <= s.get("created_at","") < week_ago])

        def pct_change(curr, prev):
            if prev == 0:
                return "+∞" if curr > 0 else "0"
            c = round((curr - prev) / prev * 100)
            return f"+{c}%" if c >= 0 else f"{c}%"

        data = {
            "week":              now.strftime("%Y-W%V"),
            "videos_this_week":  len(this_week_videos),
            "videos_last_week":  len(last_week_videos),
            "videos_change":     pct_change(len(this_week_videos), len(last_week_videos)),
            "revenue_this_week": round(this_week_sales, 2),
            "revenue_last_week": round(last_week_sales, 2),
            "revenue_change":    pct_change(this_week_sales, last_week_sales),
            "new_subs_this":     this_week_subs,
            "new_subs_last":     last_week_subs,
            "subs_change":       pct_change(this_week_subs, last_week_subs),
            "total_subs":        len(subs),
        }

        # AI recommendations
        recommendations = await self._get_recommendations(data)
        data["recommendations"] = recommendations

        if self.tg:
            await self.tg.send_message(self._format_message(data))

        log.info(f"Weekly progress report sent: {data['week']}")
        return data

    async def _get_recommendations(self, data: Dict) -> list:
        prompt = f"""You are a YouTube growth strategist. Analyze this week's performance:
Videos produced: {data['videos_this_week']} (prev: {data['videos_last_week']}, {data['videos_change']})
Revenue: ${data['revenue_this_week']} (prev: ${data['revenue_last_week']}, {data['revenue_change']})
New subscribers: {data['new_subs_this']} (prev: {data['new_subs_last']}, {data['subs_change']})

Give 3 specific, actionable improvement recommendations for next week.
Respond with JSON: {{"recommendations": ["rec 1", "rec 2", "rec 3"]}}"""

        result = self.ai._call_ollama(prompt, model="llama3.2:1b")
        return result.get("recommendations", [
            "Increase posting frequency by 1 video per channel",
            "Add stronger CTA to lead magnet in video descriptions",
            "Test a new content format based on top-performing topics",
        ])

    def _format_message(self, data: Dict) -> str:
        recs = data.get("recommendations", [])
        rec_text = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(recs))
        return (
            f"📈 <b>Weekly Progress — {data['week']}</b>\n\n"
            f"📹 Videos: <b>{data['videos_this_week']}</b> ({data['videos_change']} vs last week)\n"
            f"💰 Revenue: <b>${data['revenue_this_week']}</b> ({data['revenue_change']})\n"
            f"📧 New subs: <b>{data['new_subs_this']}</b> ({data['subs_change']}) | Total: {data['total_subs']}\n\n"
            f"<b>Next week recommendations:</b>\n{rec_text}"
        )
