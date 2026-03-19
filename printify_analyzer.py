"""
printify_analyzer.py — Phase 4
────────────────────────────────
Read-only Printify catalog analysis.
Connects to Printify API, fetches your products,
cross-references with trend data, outputs PDF report.
No orders, no uploads — analysis only.
"""
import time
import requests
from typing import List, Dict, Optional
from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("printify_analyzer")

PRINTIFY_BASE = "https://api.printify.com/v1"


class PrintifyAnalyzer:
    """
    Read-only Printify product analysis.
    Connects to YOUR account only. No other shop accessible.
    """
    def __init__(self):
        self.sheets = SheetsManager()
        self.headers = {
            "Authorization": f"Bearer {Config.PRINTIFY_API_KEY}",
            "Content-Type":  "application/json",
        }

    def get_shops(self) -> List[Dict]:
        if not Config.PRINTIFY_API_KEY:
            log.warning("Printify API key not configured")
            return []
        try:
            r = requests.get(f"{PRINTIFY_BASE}/shops.json", headers=self.headers, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error(f"Printify shops fetch failed: {e}")
            return []

    def get_products(self, shop_id: str, limit: int = 50) -> List[Dict]:
        if not Config.PRINTIFY_API_KEY:
            return []
        try:
            time.sleep(1)
            r = requests.get(
                f"{PRINTIFY_BASE}/shops/{shop_id}/products.json",
                headers=self.headers,
                params={"limit": limit},
                timeout=20
            )
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            log.error(f"Printify products fetch failed: {e}")
            return []

    async def analyze_and_report(self, job_id: str) -> Optional[str]:
        shops = self.get_shops()
        if not shops:
            log.warning("No Printify shops found")
            return None

        shop_id  = shops[0].get("id")
        products = self.get_products(str(shop_id))
        if not products:
            return None

        trends = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        analyzed = []
        for p in products:
            score = self._match_trends(p, trends)
            analyzed.append({
                "id":          p.get("id"),
                "title":       p.get("title"),
                "trend_score": score,
                "variants":    len(p.get("variants", [])),
                "category":    p.get("tags", ["unknown"])[0] if p.get("tags") else "unknown",
            })
        analyzed.sort(key=lambda x: x["trend_score"], reverse=True)
        return self._generate_report(analyzed, job_id)

    def _match_trends(self, product: Dict, trends: List[Dict]) -> int:
        title = (product.get("title") or "").lower()
        tags  = " ".join(product.get("tags") or []).lower()
        score = 0
        for t in trends:
            topic = (t.get("topic") or "").lower()
            if any(w in title or w in tags for w in topic.split()):
                score = max(score, int(t.get("popularity", 0)))
        return min(score, 100)

    def _generate_report(self, analyzed: List[Dict], job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_printify_report.pdf")
        doc    = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()

        rows = [["Product", "Category", "Variants", "Trend Score"]]
        for p in analyzed[:20]:
            rows.append([
                p["title"][:45],
                p["category"],
                str(p["variants"]),
                f"{p['trend_score']}/100"
            ])

        table = Table(rows, colWidths=[240, 80, 60, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#1A1A2E")),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8.5),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#F0F0F0")]),
            ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#C0C0C0")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))

        story = [
            Paragraph("Printify Catalog Analysis", styles["Title"]),
            Paragraph("Products ranked by trend alignment — read-only analysis", styles["Normal"]),
            Spacer(1, 12),
            table,
        ]
        doc.build(story)
        log.info(f"Printify report: {out_path}")
        return out_path
