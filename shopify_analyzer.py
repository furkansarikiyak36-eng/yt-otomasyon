"""
shopify_analyzer.py — Phase 4
───────────────────────────────
Read-only Shopify product analysis.
Connects ONLY to YOUR store with YOUR API key.
No writes, no orders, no customer data.
Invisible to outside parties — all requests are server-to-server HTTPS.
"""
import time
import requests
from typing import List, Dict, Optional

from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("shopify_analyzer")


class ShopifyAnalyzer:
    """
    PRIVACY NOTE:
    ─────────────
    This class connects only to the store configured in SHOPIFY_STORE_URL.
    The Admin API key is scoped to read-only (products + inventory).
    No other store is accessible. No customer data is fetched.
    All API calls are HTTPS server-to-server — invisible to outside parties.
    """

    def __init__(self):
        self.sheets  = SheetsManager()
        self.base_url = f"https://{Config.SHOPIFY_STORE_URL}/admin/api/2024-01"
        self.headers  = {
            "X-Shopify-Access-Token": Config.SHOPIFY_API_KEY,
            "Content-Type": "application/json",
        }

    # ── Fetch your own products ──────────────────────────────────
    def get_products(self, limit: int = 50) -> List[Dict]:
        """Fetch YOUR store's products. Read-only."""
        if not Config.SHOPIFY_STORE_URL or not Config.SHOPIFY_API_KEY:
            log.warning("Shopify not configured — skipping")
            return []
        try:
            time.sleep(0.5)  # 2 req/sec limit
            resp = requests.get(
                f"{self.base_url}/products.json",
                headers=self.headers,
                params={"limit": limit, "fields": "id,title,body_html,tags,variants"},
                timeout=30
            )
            resp.raise_for_status()
            products = resp.json().get("products", [])
            log.info(f"Shopify: fetched {len(products)} products from your store")
            return products
        except Exception as e:
            log.error(f"Shopify products fetch failed: {e}")
            return []

    def get_inventory(self) -> List[Dict]:
        """Fetch inventory levels. Read-only."""
        if not Config.SHOPIFY_STORE_URL:
            return []
        try:
            time.sleep(0.5)
            resp = requests.get(
                f"{self.base_url}/inventory_levels.json",
                headers=self.headers,
                params={"limit": 50},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json().get("inventory_levels", [])
        except Exception as e:
            log.error(f"Shopify inventory fetch failed: {e}")
            return []

    # ── Analysis: cross-reference with trends ────────────────────
    async def analyze_and_report(self, job_id: str) -> Optional[str]:
        """
        Fetch your products, cross-reference with trend data,
        generate PDF report with recommendations.
        """
        products = self.get_products()
        if not products:
            return None

        trends = self.sheets.read_all("trend_data")
        analyzed = []
        for p in products:
            trend_score = self._match_product_to_trends(p, trends)
            analyzed.append({
                "id":          p.get("id"),
                "title":       p.get("title"),
                "trend_score": trend_score,
                "price":       p["variants"][0]["price"] if p.get("variants") else "N/A",
            })

        analyzed.sort(key=lambda x: x["trend_score"], reverse=True)
        return self._generate_report(analyzed, job_id)

    def _match_product_to_trends(self, product: Dict, trends: List[Dict]) -> int:
        title = product.get("title", "").lower()
        tags  = product.get("tags", "").lower()
        score = 0
        for trend in trends:
            topic = trend.get("topic", "").lower()
            if any(w in title or w in tags for w in topic.split()):
                score = max(score, int(trend.get("popularity", 0)))
        return min(score, 100)

    def _generate_report(self, analyzed: List[Dict], job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_shopify_report.pdf")
        doc = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()

        rows = [["Product", "Price", "Trend Score"]]
        for p in analyzed[:20]:
            rows.append([p["title"][:50], f"${p['price']}", f"{p['trend_score']}/100"])

        table = Table(rows, colWidths=[300, 80, 100])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A1A2E")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
        ]))

        story = [
            Paragraph("Shopify Product Analysis — Your Store", styles["Title"]),
            Spacer(1,12),
            Paragraph("Products ranked by trend alignment score.", styles["Normal"]),
            Spacer(1,12),
            table,
        ]
        doc.build(story)
        log.info(f"Shopify report generated: {out_path}")
        return out_path
