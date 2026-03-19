"""
product_producer.py — Phase 1/2
─────────────────────────────────
Generates PDF digital products and uploads as Gumroad draft.
Uses WeasyPrint for HTML→PDF conversion.
"""
import os
import requests
from typing import Dict, Optional

from config import Config
from utils.logger import get_logger

log = get_logger("product_producer")

GUMROAD_API = "https://api.gumroad.com/v2/products"


class ProductProducer:

    # ── Main entry ───────────────────────────────────────────────
    async def produce_pdf(
        self,
        job_id: str,
        product_concept: Dict,
        out_dir: str,
    ) -> Optional[str]:
        """Generate PDF from product concept. Returns file path."""
        os.makedirs(out_dir, exist_ok=True)
        html = self._build_html(product_concept)
        pdf_path = os.path.join(out_dir, f"{job_id}_product.pdf")

        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(pdf_path)
            log.info(f"PDF generated: {pdf_path}")
            return pdf_path
        except ImportError:
            log.warning("WeasyPrint not available — using reportlab fallback")
            return self._reportlab_fallback(product_concept, pdf_path)
        except Exception as e:
            log.error(f"PDF generation failed: {e}")
            return None

    # ── HTML template ────────────────────────────────────────────
    def _build_html(self, concept: Dict) -> str:
        chapters_html = ""
        for i, ch in enumerate(concept.get("chapters", []), 1):
            chapters_html += f"<h2>Chapter {i}: {ch}</h2><p>Content for this chapter goes here.</p>\n"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Georgia, serif; margin: 60px; color: #2D2D2D; line-height: 1.7; }}
  h1   {{ color: #1A1A2E; font-size: 2.2em; border-bottom: 3px solid #E94560; padding-bottom: 10px; }}
  h2   {{ color: #16213E; font-size: 1.4em; margin-top: 30px; }}
  .subtitle {{ color: #666; font-size: 1.1em; margin-bottom: 30px; }}
  .cover {{ text-align: center; padding: 80px 40px; }}
  .audience {{ background: #F0F0F0; padding: 15px; border-left: 4px solid #E94560; margin: 20px 0; }}
  @page {{ size: A4; margin: 2cm; }}
</style>
</head>
<body>
  <div class="cover">
    <h1>{concept.get('title', 'Digital Guide')}</h1>
    <p class="subtitle">{concept.get('subtitle', '')}</p>
    <p>{concept.get('description', '')}</p>
  </div>
  <div class="audience">
    <strong>Who this is for:</strong> {concept.get('target_audience', 'Anyone interested in wellness')}
  </div>
  <h2>Table of Contents</h2>
  <ol>
    {''.join(f"<li>{ch}</li>" for ch in concept.get('chapters', []))}
  </ol>
  {chapters_html}
  <hr>
  <p><em>Price suggestion: ${concept.get('price_suggestion', 19)}</em></p>
</body>
</html>"""

    # ── ReportLab fallback ───────────────────────────────────────
    def _reportlab_fallback(self, concept: Dict, pdf_path: str) -> Optional[str]:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet

            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [
                Paragraph(concept.get("title", "Guide"), styles["Title"]),
                Spacer(1, 20),
                Paragraph(concept.get("description", ""), styles["Normal"]),
            ]
            for ch in concept.get("chapters", []):
                story += [Spacer(1, 12), Paragraph(ch, styles["Heading2"])]
            doc.build(story)
            log.info(f"ReportLab PDF fallback: {pdf_path}")
            return pdf_path
        except Exception as e:
            log.error(f"ReportLab fallback failed: {e}")
            return None

    # ── Gumroad draft upload ──────────────────────────────────────
    async def upload_to_gumroad_draft(
        self,
        pdf_path: str,
        concept: Dict,
        price_cents: int = 1900,
    ) -> Optional[str]:
        """Upload PDF as a private Gumroad draft. Returns product URL."""
        if not Config.GUMROAD_ACCESS_TOKEN:
            log.warning("GUMROAD_ACCESS_TOKEN not set — skipping upload")
            return None
        try:
            # Create product
            resp = requests.post(
                GUMROAD_API,
                data={
                    "access_token": Config.GUMROAD_ACCESS_TOKEN,
                    "name":         concept.get("title"),
                    "description":  concept.get("description"),
                    "price":        price_cents,
                    "published":    "false",  # draft
                },
                timeout=30
            )
            resp.raise_for_status()
            product_id = resp.json()["product"]["id"]

            # Upload file
            with open(pdf_path, "rb") as f:
                requests.put(
                    f"{GUMROAD_API}/{product_id}/files",
                    data={"access_token": Config.GUMROAD_ACCESS_TOKEN},
                    files={"file": f},
                    timeout=60
                )

            product_url = f"https://gumroad.com/products/{product_id}/edit"
            log.info(f"Gumroad draft created: {product_url}")
            return product_url
        except Exception as e:
            log.error(f"Gumroad upload failed: {e}")
            return None
