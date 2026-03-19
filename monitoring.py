"""
monitoring.py — Sentry integration + Telegram critical alerts
"""
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from config import Config
from utils.logger import get_logger

log = get_logger("monitoring")


def init_sentry():
    if not Config.SENTRY_DSN:
        log.warning("SENTRY_DSN not set — error tracking disabled")
        return
    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        environment="production",
    )
    log.info("Sentry initialized")


def capture_exception(exc: Exception, context: dict = None):
    log.error(f"Exception: {exc}", exc_info=True)
    with sentry_sdk.push_scope() as scope:
        if context:
            for k, v in context.items():
                scope.set_extra(k, v)
        sentry_sdk.capture_exception(exc)


async def send_critical_alert(message: str):
    """Send a critical alert to Telegram. Called from anywhere in the system."""
    try:
        from telegram_handler import TelegramHandler
        handler = TelegramHandler()
        await handler.send_message(f"🚨 CRITICAL: {message}")
    except Exception as e:
        log.error(f"Failed to send critical alert: {e}")
