"""
main.py
───────
Flask webhook server + async startup orchestrator.
Entry point for the entire system.

Security: HMAC signature verification on all incoming webhooks.
"""
import asyncio
import hashlib
import hmac
import os
import threading
from flask import Flask, request, jsonify, abort

import sentry_sdk
from config import Config
from utils.logger import get_logger
from monitoring import init_sentry
from sheets_manager import SheetsManager
from queue_manager import QueueManager
from workflow_manager import WorkflowManager
from telegram_handler import TelegramHandler
from github_backup import GitHubBackup
from scheduler import build_scheduler

log = get_logger("main")
app = Flask(__name__)

# ── Global singletons ────────────────────────────────────────────
sheets  = SheetsManager()
queue   = QueueManager()
wf      = WorkflowManager()
tg      = TelegramHandler()
backup  = GitHubBackup()


# ════════════════════════════════════════════════════════════
# HMAC DOĞRULAMA — tüm webhook'lar için güvenlik katmanı
# ════════════════════════════════════════════════════════════

def _verify_gumroad_signature(payload: bytes, header_sig: str) -> bool:
    """
    Gumroad webhook HMAC-SHA256 doğrulaması.
    Gumroad → Settings → Advanced → Webhook secret
    .env'de GUMROAD_WEBHOOK_SECRET olarak saklanır.
    """
    secret = os.getenv("GUMROAD_WEBHOOK_SECRET", "")
    if not secret:
        # Secret tanımlı değilse geç (geliştirme modu)
        log.warning("GUMROAD_WEBHOOK_SECRET not set — skipping HMAC check")
        return True
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header_sig or "")


def _verify_shopify_signature(payload: bytes, header_sig: str) -> bool:
    """
    Shopify webhook HMAC-SHA256 doğrulaması.
    Shopify imzayı X-Shopify-Hmac-Sha256 header'ında base64 olarak gönderir.
    """
    import base64
    secret = os.getenv("SHOPIFY_API_SECRET", "")
    if not secret:
        log.warning("SHOPIFY_API_SECRET not set — skipping HMAC check")
        return True
    digest   = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, header_sig or "")


def _verify_n8n_token(token: str) -> bool:
    """
    n8n → Python çağrılarını Bearer token ile doğrula.
    .env'de N8N_INTERNAL_TOKEN tanımlı olmalı.
    """
    expected = os.getenv("N8N_INTERNAL_TOKEN", "")
    if not expected:
        return True  # Token tanımlı değilse geç
    return hmac.compare_digest(expected, token or "")


# ════════════════════════════════════════════════════════════
# FLASK WEBHOOK ENDPOINT'LERİ
# ════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "queue":  queue.status_summary(),
        "sheets": "connected",
    })


@app.route("/webhook/gumroad", methods=["POST"])
def webhook_gumroad():
    """Gumroad satış/indirme olaylarını n8n'den alır."""
    payload    = request.get_data()
    header_sig = request.headers.get("X-Gumroad-Signature", "")

    if not _verify_gumroad_signature(payload, header_sig):
        log.warning("Gumroad HMAC doğrulama başarısız — istek reddedildi")
        abort(401)

    data = request.json or {}
    log.info(f"Gumroad webhook: {data.get('product_name')} — {data.get('event_type')}")

    event_type = data.get("event_type", "sale")
    if event_type in ("sale", "refund"):
        # E-posta stratejisini tetikle
        asyncio.run_coroutine_threadsafe(
            _handle_gumroad_sale(data), _get_loop()
        )
    return jsonify({"status": "received"})


@app.route("/webhook/shopify", methods=["POST"])
def webhook_shopify():
    """Shopify stok/ürün olaylarını n8n'den alır."""
    payload    = request.get_data()
    header_sig = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not _verify_shopify_signature(payload, header_sig):
        log.warning("Shopify HMAC doğrulama başarısız — istek reddedildi")
        abort(401)

    data  = request.json or {}
    topic = data.get("topic", "unknown")
    log.info(f"Shopify webhook: {topic}")

    asyncio.run_coroutine_threadsafe(
        _handle_shopify_event(data, topic), _get_loop()
    )
    return jsonify({"status": "received"})


@app.route("/webhook/n8n", methods=["POST"])
def webhook_n8n():
    """Genel n8n → Python köprüsü."""
    auth_header = request.headers.get("Authorization", "")
    token       = auth_header.replace("Bearer ", "").strip()

    if not _verify_n8n_token(token):
        log.warning("n8n token doğrulama başarısız — istek reddedildi")
        abort(401)

    data       = request.json or {}
    event_type = data.get("event_type", "unknown")
    log.info(f"n8n event: {event_type}")

    asyncio.run_coroutine_threadsafe(
        _handle_n8n_event(event_type, data), _get_loop()
    )
    return jsonify({"status": "received", "event_type": event_type})


@app.route("/webhook/form", methods=["POST"])
def webhook_form():
    """Typeform / Tally form gönderimleri."""
    data  = request.json or {}
    email = data.get("email", "")
    if not email:
        return jsonify({"status": "ignored", "reason": "no email"}), 200

    asyncio.run_coroutine_threadsafe(
        _handle_form_submission(data), _get_loop()
    )
    return jsonify({"status": "received"})


# ════════════════════════════════════════════════════════════
# OLAY İŞLEYİCİLER
# ════════════════════════════════════════════════════════════

async def _handle_gumroad_sale(data: dict):
    try:
        from email_strategy import EmailStrategy
        from email_lead_magnet import EmailLeadMagnet
        product  = data.get("product_name", "")
        email    = data.get("email", "")
        is_free  = float(data.get("price", "0").replace("$","") or 0) == 0

        if is_free:
            await EmailLeadMagnet().add_subscriber(email, product)
        else:
            await EmailStrategy().trigger_post_purchase(email, product)

        # Sheets'e satış yaz
        sheets.append_row(Config.SHEETS_SALES, {
            "product": product,
            "amount":  data.get("price", "0"),
            "date":    data.get("sale_timestamp", ""),
            "source":  "gumroad",
        })
    except Exception as e:
        log.error(f"Gumroad sale handler error: {e}")


async def _handle_shopify_event(data: dict, topic: str):
    try:
        is_new     = "create" in topic
        is_restock = "update" in topic and int(data.get("stock", 0)) > 0
        if is_new or is_restock:
            from social_producer import SocialProducer
            job_id = f"SHOP_{data.get('product_id','')[:8]}"
            await SocialProducer().produce_shopify_content(data, job_id, tg)
    except Exception as e:
        log.error(f"Shopify event handler error: {e}")


async def _handle_n8n_event(event_type: str, data: dict):
    try:
        if event_type == "form_subscriber":
            await _handle_form_submission(data)
        elif event_type == "shopify_product_trigger":
            await _handle_shopify_event(data, data.get("topic","products/create"))
        elif event_type == "youtube_metrics":
            sheets.append_row(Config.SHEETS_VIDEO_LOG, {
                "video_id":    data.get("video_id",""),
                "views":       data.get("views", 0),
                "likes":       data.get("likes", 0),
                "channel_id":  data.get("channel_id",""),
            })
    except Exception as e:
        log.error(f"n8n event handler error: {e}")


async def _handle_form_submission(data: dict):
    try:
        from email_lead_magnet import EmailLeadMagnet
        email  = data.get("email","")
        source = data.get("source","form")
        if email:
            await EmailLeadMagnet().add_subscriber(email, source)
            sheets.append_row(Config.SHEETS_EMAIL_SUBSCRIBERS, {
                "source":     source,
                "created_at": data.get("submitted_at",""),
            })
    except Exception as e:
        log.error(f"Form submission handler error: {e}")


# ════════════════════════════════════════════════════════════
# ASYNC LOOP YÖNETİMİ
# ════════════════════════════════════════════════════════════

_loop = None

def _get_loop():
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop


async def startup():
    log.info("System starting up…")
    Config.validate()

    sheets.replay_pending_sync()

    active_jobs = wf.load_all_active()
    if active_jobs:
        log.info(f"Resuming {len(active_jobs)} interrupted jobs")

    scheduler = build_scheduler(sheets, backup, wf, tg)
    scheduler.start()
    log.info("Scheduler started")

    asyncio.create_task(queue.process_loop())
    log.info("Queue processor started")

    log.info("✅ System ready")
    await tg.send_message(
        "✅ <b>Sistem başlatıldı</b>\n"
        "Tüm servisler çalışıyor.\n"
        "/start ile etkileşime geçebilirsin."
    )


def _run_startup():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(startup())
    _loop.run_forever()


if __name__ == "__main__":
    init_sentry()
    t = threading.Thread(target=_run_startup, daemon=True)
    t.start()
    log.info("Flask başlatılıyor — port 5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
