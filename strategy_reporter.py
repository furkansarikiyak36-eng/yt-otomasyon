"""
strategy_reporter.py — Phase 2.5
──────────────────────────────────
Weekly/monthly strategy report.
Aggregates data from all Sheets tables and sends PDF + Telegram summary.
"""
from datetime import datetime, timedelta
from typing import Dict

from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("strategy_reporter")


class StrategyReporter:
    def __init__(self, telegram_handler=None):
        self.sheets = SheetsManager()
        self.tg = telegram_handler

    async def generate_weekly(self, job_id: str) -> str:
        """Generate weekly report PDF and send Telegram summary."""
        log.info("Generating weekly strategy report…")

        data = self._collect_data()
        pdf_path = self._build_pdf(data, job_id)

        if self.tg:
            await self.tg.send_message(self._build_summary(data))

        return pdf_path

    def _collect_data(self) -> Dict:
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        videos   = self.sheets.read_all(Config.SHEETS_VIDEO_LOG)
        trends   = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        sales    = self.sheets.read_all(Config.SHEETS_SALES)
        subs     = self.sheets.read_all(Config.SHEETS_EMAIL_SUBSCRIBERS)

        weekly_videos = [v for v in videos if v.get("publish_date", "") >= week_ago]
        weekly_sales  = [s for s in sales  if s.get("date", "") >= week_ago]
        total_revenue = sum(float(s.get("amount", 0)) for s in weekly_sales)

        return {
            "week_of":        datetime.utcnow().strftime("%Y-%m-%d"),
            "videos_produced": len(weekly_videos),
            "total_subscribers": len(subs),
            "weekly_revenue":   total_revenue,
            "top_trends":       trends[:5],
        }

    def _build_summary(self, data: Dict) -> str:
        return (
            f"📊 <b>Weekly Strategy Report — {data['week_of']}</b>\n\n"
            f"📹 Videos produced: <b>{data['videos_produced']}</b>\n"
            f"📧 Total subscribers: <b>{data['total_subscribers']}</b>\n"
            f"💰 Weekly revenue: <b>${data['weekly_revenue']:.2f}</b>\n\n"
            f"🔥 Top trends this week:\n" +
            "\n".join(f"  • {t.get('topic')} ({t.get('popularity')}/100)"
                      for t in data["top_trends"])
        )

    def _build_pdf(self, data: Dict, job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_weekly_report.pdf")
        doc = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(f"Weekly Strategy Report — {data['week_of']}", styles["Title"]),
            Spacer(1, 12),
            Paragraph(f"Videos produced this week: {data['videos_produced']}", styles["Normal"]),
            Paragraph(f"Total email subscribers: {data['total_subscribers']}", styles["Normal"]),
            Paragraph(f"Weekly revenue: ${data['weekly_revenue']:.2f}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("Top Trends", styles["Heading2"]),
        ]
        for t in data["top_trends"]:
            story.append(Paragraph(f"• {t.get('topic')} — {t.get('popularity')}/100", styles["Normal"]))
        doc.build(story)
        return out_path
