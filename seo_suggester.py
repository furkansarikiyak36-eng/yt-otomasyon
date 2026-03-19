"""
seo_suggester.py — Phase 2.5
──────────────────────────────
SEO keyword and meta tag suggestions for videos and products.
Uses Ollama + trend data from Sheets. Outputs PDF report.
"""
import os
from typing import Dict, Optional
from ai_synthesizer import AISynthesizer
from sheets_manager import SheetsManager
from config import Config
from utils.logger import get_logger

log = get_logger("seo_suggester")


class SEOSuggester:
    def __init__(self):
        self.ai     = AISynthesizer()
        self.sheets = SheetsManager()

    async def suggest(
        self,
        title: str,
        content_type: str,   # "video" | "product" | "blog"
        channel_id: str,
        job_id: str,
    ) -> Optional[str]:
        """Generate SEO suggestions and return PDF report path."""

        # Get recent trend keywords for context
        trends = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        top_keywords = [t.get("topic", "") for t in trends[:10]]

        prompt = f"""You are an SEO specialist for YouTube and e-commerce.
Content type: {content_type}
Title: {title}
Channel: {channel_id}
Trending keywords context: {', '.join(top_keywords)}

Provide comprehensive SEO suggestions. Respond with JSON:
{{
  "optimized_title": "SEO-optimized title (max 70 chars for video, 60 for blog)",
  "meta_description": "155-char description with primary keyword",
  "primary_keyword": "main target keyword",
  "secondary_keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "thumbnail_text": "3-5 words for thumbnail overlay",
  "youtube_description_template": "First 200 chars with keyword, then bullets",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
  "estimated_monthly_searches": 1000,
  "competition_level": "low|medium|high",
  "seo_score": 75
}}"""

        result = self.ai._call_ollama(prompt)
        if not result:
            return None

        return self._generate_pdf(result, title, job_id)

    def _generate_pdf(self, data: Dict, title: str, job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_seo_report.pdf")
        doc = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()
        C = colors.HexColor

        story = [
            Paragraph("SEO Report", styles["Title"]),
            Paragraph(f"Content: {title}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph(f"SEO Score: {data.get('seo_score', 0)}/100", styles["Heading2"]),
            Spacer(1, 8),
        ]

        # Key metrics table
        rows = [
            ["Primary keyword",   data.get("primary_keyword", "")],
            ["Competition",       data.get("competition_level", "")],
            ["Est. monthly searches", str(data.get("estimated_monthly_searches", ""))],
            ["Optimized title",   data.get("optimized_title", "")],
            ["Thumbnail text",    data.get("thumbnail_text", "")],
        ]
        t = Table(rows, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), C("#1A1A2E")),
            ("TEXTCOLOR",  (0,0), (0,-1), colors.white),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("GRID",       (0,0), (-1,-1), 0.4, C("#C0C0C0")),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, C("#F0F0F0")]),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        story += [t, Spacer(1,12)]

        # Tags
        story.append(Paragraph("Recommended Tags", styles["Heading2"]))
        tags = data.get("tags", [])
        story.append(Paragraph("  ".join(f"#{t}" for t in tags), styles["Normal"]))
        story += [Spacer(1,8)]

        # Description template
        story.append(Paragraph("YouTube Description Template", styles["Heading2"]))
        story.append(Paragraph(data.get("youtube_description_template", ""), styles["Normal"]))

        doc.build(story)
        log.info(f"SEO report: {out_path}")
        return out_path
