"""
traffic_analyzer.py — Phase 2.5
─────────────────────────────────
UTM-based traffic source analysis.
Reads UTM parameters from Sheets (logged by n8n) and generates source report.
Google Analytics API is optional — works with manual UTM data too.
"""
from typing import Dict, List
from datetime import datetime, timedelta
from sheets_manager import SheetsManager
from config import Config
from utils.logger import get_logger

log = get_logger("traffic_analyzer")


class TrafficAnalyzer:
    def __init__(self):
        self.sheets = SheetsManager()

    def analyze(self, days: int = 30) -> Dict:
        """Analyze traffic sources from UTM data in Sheets."""
        subscribers = self.sheets.read_all(Config.SHEETS_EMAIL_SUBSCRIBERS)
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        recent = [s for s in subscribers if s.get("created_at", "") >= cutoff]

        sources: Dict[str, int] = {}
        for s in recent:
            src = s.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1

        total = len(recent)
        report = {
            "period_days":   days,
            "total_new":     total,
            "by_source":     sources,
            "top_source":    max(sources, key=sources.get) if sources else "none",
            "generated_at":  datetime.utcnow().isoformat(),
        }
        log.info(f"Traffic report: {total} new subscribers in {days} days")
        return report

    def format_telegram_message(self, report: Dict) -> str:
        lines = [
            f"📊 <b>Traffic Report — Last {report['period_days']} Days</b>\n",
            f"Total new subscribers: <b>{report['total_new']}</b>",
            f"Top source: <b>{report['top_source']}</b>\n",
            "<b>By source:</b>",
        ]
        for src, count in sorted(report["by_source"].items(), key=lambda x: -x[1]):
            pct = round(count / report["total_new"] * 100) if report["total_new"] else 0
            lines.append(f"  • {src}: {count} ({pct}%)")
        return "\n".join(lines)
