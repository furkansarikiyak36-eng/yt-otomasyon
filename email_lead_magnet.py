"""
email_lead_magnet.py — Phase 1
────────────────────────────────
Adds lead magnet downloaders to Kit (ConvertKit) with appropriate tags.
Called by n8n after Gumroad free-product download webhook.
"""
from typing import Optional
from convertkit_api import KitAPI
from utils.logger import get_logger
from utils.helpers import hash_email
from config import Config
from sheets_manager import SheetsManager

log = get_logger("email_lead_magnet")


class EmailLeadMagnet:
    def __init__(self):
        self.kit = KitAPI()
        self.sheets = SheetsManager()

    async def add_lead(
        self,
        email: str,
        product_name: str,
        source: str = "gumroad",
    ) -> bool:
        """Add a new lead to Kit with product tag. Returns success."""
        tag_name = f"lead_magnet_{product_name.lower().replace(' ', '_')[:30]}"

        # Add to Kit
        subscriber_id = await self.kit.add_subscriber(email, tags=[tag_name])
        if not subscriber_id:
            log.error(f"Failed to add {hash_email(email)} to Kit")
            return False

        # Record in Sheets (hashed email only — no PII stored)
        self.sheets.append_row(Config.SHEETS_EMAIL_SUBSCRIBERS, {
            "email_hash": hash_email(email),
            "tags": tag_name,
            "source": source,
            "product": product_name,
        })
        log.info(f"Lead added: {hash_email(email)} via {product_name}")
        return True
