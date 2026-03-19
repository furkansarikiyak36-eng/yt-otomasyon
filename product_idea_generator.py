"""
product_idea_generator.py — Phase 2.5
───────────────────────────────────────
Generates digital product ideas based on current trend data.
Cross-references trending topics with audience segments.
Output: PDF report with ranked product ideas.
"""
import os
from typing import List, Dict, Optional
from ai_synthesizer import AISynthesizer
from sheets_manager import SheetsManager
from config import Config
from utils.logger import get_logger

log = get_logger("product_idea_generator")


class ProductIdeaGenerator:
    def __init__(self):
        self.ai     = AISynthesizer()
        self.sheets = SheetsManager()

    async def generate(self, job_id: str, count: int = 5) -> Optional[str]:
        """Generate product ideas from current trends. Returns PDF path."""

        trends   = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        segments = self.sheets.read_all(Config.SHEETS_SEGMENTS)

        top_trends = sorted(trends, key=lambda x: int(x.get("popularity", 0)), reverse=True)[:8]
        trend_list = [f"{t.get('topic')} (popularity: {t.get('popularity')})" for t in top_trends]
        seg_names  = [s.get("segment_name", "") for s in segments]

        prompt = f"""You are a digital product strategist for a wellness/fitness brand.

Current trending topics: {', '.join(trend_list)}
Audience segments: {', '.join(seg_names) or 'general wellness audience'}

Generate {count} digital product ideas. Respond with JSON:
{{
  "products": [
    {{
      "title": "product title",
      "type": "PDF guide | audio pack | video course | checklist | template",
      "trend_match": "which trend this addresses",
      "target_segment": "who will buy this",
      "price_suggestion": 19,
      "lead_magnet_version": "free version title",
      "why_now": "why this is timely",
      "estimated_demand_score": 75,
      "chapters": ["ch1", "ch2", "ch3"]
    }}
  ]
}}"""

        result = self.ai._call_ollama(prompt, model="qwen2.5:3b")
        products = result.get("products", [])
        if not products:
            log.error("No product ideas generated")
            return None

        return self._generate_pdf(products, job_id)

    def _generate_pdf(self, products: List[Dict], job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_product_ideas.pdf")
        doc    = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()
        C      = colors.HexColor

        story = [
            Paragraph("Digital Product Ideas Report", styles["Title"]),
            Paragraph(f"Generated from current trend data — {len(products)} ideas", styles["Normal"]),
            Spacer(1, 16),
        ]

        for i, p in enumerate(products, 1):
            story += [
                Paragraph(f"{i}. {p.get('title')}", styles["Heading2"]),
                Paragraph(f"Type: {p.get('type')}  |  Price: ${p.get('price_suggestion')}  |  Demand: {p.get('estimated_demand_score')}/100", styles["Normal"]),
                Paragraph(f"Trend match: {p.get('trend_match')}", styles["Normal"]),
                Paragraph(f"Target: {p.get('target_segment')}", styles["Normal"]),
                Paragraph(f"Why now: {p.get('why_now')}", styles["Normal"]),
                Paragraph(f"Lead magnet: {p.get('lead_magnet_version')}", styles["Normal"]),
                Spacer(1, 10),
            ]

        doc.build(story)
        log.info(f"Product ideas report: {out_path}")
        return out_path
