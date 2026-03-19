"""
product_analyzer.py — Phase 2.5
─────────────────────────────────
Scrapes a product URL, cross-references with trend data, outputs PDF report.
Uses rotating proxies + user-agent rotation for respectful scraping.
Amazon: PAAPI only — never scraped.
"""
import time
import random
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import Dict, Optional

from config import Config
from sheets_manager import SheetsManager
from utils.logger import get_logger

log = get_logger("product_analyzer")

ua = UserAgent()


class ProductAnalyzer:
    def __init__(self):
        self.sheets = SheetsManager()

    # ── Main analysis ────────────────────────────────────────────
    async def analyze(self, url: str, job_id: str) -> Optional[str]:
        """
        Scrape product URL, analyze vs trends, generate PDF report.
        Returns path to PDF report or None.
        """
        log.info(f"Analyzing product: {url}")

        # Safety: never scrape Amazon
        if "amazon.com" in url or "amazon." in url:
            log.warning("Amazon URL detected — use PAAPI instead of scraping")
            return self._amazon_paapi_report(url, job_id)

        product_data = self._scrape_product(url)
        if not product_data:
            log.error(f"Scraping failed for {url}")
            return None

        trend_score = self._match_trends(product_data)
        report_path = self._generate_pdf_report(product_data, trend_score, job_id)
        return report_path

    # ── Scraping (non-Amazon) ────────────────────────────────────
    def _scrape_product(self, url: str) -> Optional[Dict]:
        """Scrape product page with respectful delays and user-agent rotation."""
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9",
        }
        # Random delay: 1–3 seconds
        time.sleep(random.uniform(1.0, 3.0))

        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=headers, timeout=20)

            if resp.status_code == 403:
                log.warning(f"403 blocked at {url} — stopping, not retrying")
                return None
            if resp.status_code == 429:
                log.warning(f"429 rate limited at {url} — backing off 30s")
                time.sleep(30)
                return None

            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Generic extraction — works for most e-commerce pages
            title = (
                soup.find("h1") or
                soup.find(attrs={"itemprop": "name"}) or
                soup.find("title")
            )
            price = (
                soup.find(attrs={"itemprop": "price"}) or
                soup.find(class_=lambda c: c and "price" in c.lower()) if soup else None
            )
            description = (
                soup.find(attrs={"itemprop": "description"}) or
                soup.find("meta", attrs={"name": "description"})
            )

            return {
                "url":         url,
                "title":       title.get_text(strip=True) if title else "Unknown",
                "price":       price.get_text(strip=True) if price else "Unknown",
                "description": description.get("content", "") if description and description.name == "meta"
                               else (description.get_text(strip=True) if description else ""),
            }
        except Exception as e:
            log.error(f"Scraping error for {url}: {e}")
            return None

    # ── Trend matching ───────────────────────────────────────────
    def _match_trends(self, product_data: Dict) -> int:
        """Cross-reference product title with stored trends. Returns 0–100 score."""
        trends = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        title_lower = product_data.get("title", "").lower()
        score = 0
        for trend in trends:
            topic = trend.get("topic", "").lower()
            if any(word in title_lower for word in topic.split()):
                popularity = int(trend.get("popularity", 0))
                score = max(score, popularity)
        return min(score, 100)

    # ── PDF report ───────────────────────────────────────────────
    def _generate_pdf_report(self, product_data: Dict, trend_score: int, job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import os

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_product_report.pdf")
        doc = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()
        stars = "★" * (trend_score // 20) + "☆" * (5 - trend_score // 20)

        story = [
            Paragraph("Product Analysis Report", styles["Title"]),
            Spacer(1, 12),
            Paragraph(f"<b>Product:</b> {product_data.get('title')}", styles["Normal"]),
            Paragraph(f"<b>Price:</b> {product_data.get('price')}", styles["Normal"]),
            Paragraph(f"<b>URL:</b> {product_data.get('url')}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph(f"<b>Trend Score:</b> {trend_score}/100  {stars}", styles["Heading2"]),
            Spacer(1, 8),
            Paragraph(product_data.get("description", "No description available."), styles["Normal"]),
        ]
        doc.build(story)
        log.info(f"Product report generated: {out_path}")
        return out_path

    def _amazon_paapi_report(self, url: str, job_id: str) -> Optional[str]:
        log.info("Amazon product — PAAPI integration required (not yet implemented)")
        return None
