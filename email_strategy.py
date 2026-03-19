"""
email_strategy.py — Phase 2
────────────────────────────
Post-purchase email sequences and nurture content via Kit API.
Triggered by n8n after a Gumroad sale is confirmed.

Sequences:
  - post_purchase : thank you + download + 7-day nurture
  - lead_nurture  : lead magnet followup → convert to buyer
  - re_engagement : cold subscribers reactivation
"""
from typing import Optional
from convertkit_api import KitAPI
from config import Config
from utils.logger import get_logger

log = get_logger("email_strategy")


class EmailStrategy:
    def __init__(self):
        self.kit = KitAPI()

    # ── Post-purchase sequence ────────────────────────────────
    async def trigger_post_purchase(self, email: str, product_name: str) -> bool:
        """
        Tag buyer so Kit sequence auto-triggers.
        Sequence must be pre-built in Kit dashboard.
        """
        tag = f"buyer_{product_name.lower().replace(' ', '_')[:30]}"
        ok = await self.kit.add_tag(email, tag)
        if ok:
            log.info(f"Post-purchase sequence triggered: {tag}")
        return ok

    # ── Lead nurture ──────────────────────────────────────────
    async def trigger_lead_nurture(self, email: str, lead_source: str) -> bool:
        tag = f"nurture_{lead_source[:20]}"
        return await self.kit.add_tag(email, tag)

    # ── Re-engagement broadcast ───────────────────────────────
    async def send_reengagement(self, segment_id: int, subject: str, body: str) -> bool:
        return await self.kit.send_broadcast(subject, body, segment_id)

    # ── Manual campaign (from Telegram /email_send command) ──
    async def send_manual_campaign(
        self,
        segment: str,
        subject: str,
        body: str,
        telegram_handler=None,
        job_id: str = ""
    ) -> bool:
        """Draft email → Telegram approval → send."""
        if telegram_handler:
            preview = (
                f"📧 <b>Email Campaign Draft</b>\n\n"
                f"Segment: <b>{segment}</b>\n"
                f"Subject: <b>{subject}</b>\n\n"
                f"{body[:300]}{'...' if len(body) > 300 else ''}\n\n"
                f"Send this campaign?"
            )
            await telegram_handler.send_message(preview)
            action = await telegram_handler._wait_for_callback(f"{job_id}_email")
            if action != "continue":
                log.info("Email campaign cancelled by user")
                return False

        return await self.kit.send_broadcast(subject, body)
