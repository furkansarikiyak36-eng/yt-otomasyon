"""
manual_email.py — Phase 2.5
─────────────────────────────
Send manual emails via Telegram command.
AI drafts the email, you approve, then it sends.

Telegram command: /email_send <segment> <subject> <body>
"""
from convertkit_api import KitAPI
from ai_synthesizer import AISynthesizer
from utils.logger import get_logger

log = get_logger("manual_email")


class ManualEmail:
    def __init__(self, telegram_handler=None):
        self.tg   = telegram_handler
        self.kit  = KitAPI()
        self.ai   = AISynthesizer()

    async def compose_and_send(
        self,
        segment: str,
        topic: str,
        job_id: str,
        tone: str = "helpful",
    ) -> bool:
        """
        1. AI writes email draft
        2. Preview sent to Telegram
        3. Wait for approval
        4. Send via Kit on approval
        """
        # 1. AI draft
        prompt = f"""Write a short email newsletter.
Segment: {segment}
Topic: {topic}
Tone: {tone}
Max 200 words. No placeholders. Ready to send.
Respond with JSON: {{"subject": "...", "body": "..."}}"""

        draft = self.ai._call_ollama(prompt)
        subject = draft.get("subject", topic)
        body    = draft.get("body", "")

        if not body:
            log.error("Email draft empty")
            return False

        # 2. Preview
        if self.tg:
            await self.tg.send_message(
                f"📧 <b>Email Draft Ready</b>\n\n"
                f"<b>To:</b> {segment}\n"
                f"<b>Subject:</b> {subject}\n\n"
                f"{body[:400]}\n\n"
                f"✅ Continue to send  |  ❌ Cancel"
            )
            action = await self.tg._wait_for_callback(job_id)
            if action != "continue":
                log.info("Email cancelled by user")
                return False

        # 3. Send
        ok = await self.kit.send_broadcast(subject, body)
        if ok:
            log.info(f"Manual email sent: '{subject}' → {segment}")
        return ok
