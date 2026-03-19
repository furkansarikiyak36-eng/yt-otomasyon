"""
ad_producer.py — Phase 3
──────────────────────────
Ad copy and visual concept suggestions.
NO ad API connection — concepts only.
You publish manually in YouTube Ads Manager.

IMPORTANT: YouTube in-stream ads only for wellness content.
Google Display / Discovery ads: high policy risk — do NOT use.
Meta Ads: NOT recommended for wellness category.
"""
import os
from typing import Dict, Optional
from ai_synthesizer import AISynthesizer
from config import Config
from utils.logger import get_logger

log = get_logger("ad_producer")

AD_POLICY_WARNING = (
    "⚠️ AD POLICY REMINDER:\n"
    "• YouTube in-stream: SAFE for wellness\n"
    "• Google Display / Discovery: HIGH RISK\n"
    "• Meta Ads: NOT RECOMMENDED for wellness\n"
    "• No direct health claims in any ad copy\n"
)


class AdProducer:
    def __init__(self, telegram_handler=None):
        self.tg = telegram_handler
        self.ai = AISynthesizer()

    async def produce_concepts(
        self,
        product_title: str,
        product_description: str,
        target_audience: str,
        job_id: str,
        ad_type: str = "youtube_instream",  # youtube_instream only recommended
    ) -> Optional[str]:
        """
        Generate ad copy concepts. Returns PDF report path.
        Sends policy warning + concepts to Telegram for manual review.
        """
        prompt = f"""You are a YouTube ad copywriter specializing in wellness content.
Product: {product_title}
Description: {product_description}
Target audience: {target_audience}
Ad format: YouTube in-stream (skippable, 15-30 seconds)

IMPORTANT: No direct health claims. No "cure", "treat", "heal", "fix" language.
Use: "support", "help with", "improve", "discover" language only.

Generate 3 ad copy variations. Respond with JSON:
{{
  "concepts": [
    {{
      "variation": "A",
      "hook_0_5s": "first 5 seconds before skip button (must grab attention)",
      "main_message": "15-25 second main message",
      "cta": "call to action (max 5 words)",
      "visual_concept": "brief description of what to show on screen",
      "tone": "emotional | educational | social proof",
      "estimated_ctr": "0.5-2%"
    }}
  ],
  "targeting_suggestions": ["interest 1", "interest 2"],
  "budget_recommendation": "$5-10/day to start"
}}"""

        result = self.ai._call_ollama(prompt)
        if not result or "concepts" not in result:
            log.error("Ad concept generation failed")
            return None

        # Send to Telegram with policy warning
        if self.tg:
            await self.tg.send_message(
                f"🎯 <b>Ad Concepts Ready — {product_title}</b>\n\n"
                f"{AD_POLICY_WARNING}\n"
                f"<b>{len(result['concepts'])} variations generated.</b>\n"
                f"Review the PDF report and publish manually in YouTube Ads Manager."
            )

        return self._generate_pdf(result, product_title, job_id)

    def _generate_pdf(self, data: Dict, product_title: str, job_id: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        out_path = os.path.join(Config.JOBS_DIR, f"{job_id}_ad_concepts.pdf")
        doc    = SimpleDocTemplate(out_path, pagesize=A4)
        styles = getSampleStyleSheet()

        story = [
            Paragraph("Ad Concepts Report", styles["Title"]),
            Paragraph(f"Product: {product_title}", styles["Normal"]),
            Spacer(1, 8),
            Paragraph(AD_POLICY_WARNING.replace("\n", "<br/>"), styles["Normal"]),
            Spacer(1, 12),
        ]

        for concept in data.get("concepts", []):
            story += [
                Paragraph(f"Variation {concept.get('variation')} — {concept.get('tone','').upper()}", styles["Heading2"]),
                Paragraph(f"Hook (0–5s): {concept.get('hook_0_5s')}", styles["Normal"]),
                Paragraph(f"Main message: {concept.get('main_message')}", styles["Normal"]),
                Paragraph(f"CTA: {concept.get('cta')}", styles["Normal"]),
                Paragraph(f"Visual: {concept.get('visual_concept')}", styles["Normal"]),
                Paragraph(f"Est. CTR: {concept.get('estimated_ctr')}", styles["Normal"]),
                Spacer(1, 10),
            ]

        story += [
            Paragraph("Targeting Suggestions", styles["Heading2"]),
            Paragraph(", ".join(data.get("targeting_suggestions", [])), styles["Normal"]),
            Spacer(1, 8),
            Paragraph(f"Budget: {data.get('budget_recommendation')}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("To publish: go to ads.google.com → YouTube campaigns → In-stream ads", styles["Normal"]),
        ]

        doc.build(story)
        log.info(f"Ad concepts PDF: {out_path}")
        return out_path
