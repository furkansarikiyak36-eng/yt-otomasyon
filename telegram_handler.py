"""
telegram_handler.py
───────────────────
Telegram bot for:
  - Sending notifications with approval buttons
  - Receiving button responses
  - Cost-aware prompts before paid API use
  - Command handling (/status, /cancel, /mode, /report, etc.)
"""
import asyncio
from typing import Optional, Callable

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from config import Config
from utils.logger import get_logger

log = get_logger("telegram_handler")

# ── Callback data constants ──────────────────────────────────────
CB_CONTINUE  = "continue"
CB_EDIT      = "edit"
CB_CANCEL    = "cancel"
CB_DOWNLOAD  = "download"
CB_TAKEOVER  = "takeover"
CB_YES       = "yes"
CB_NO        = "no"


class TelegramHandler:
    def __init__(self):
        self.app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self._pending_callbacks: dict[str, asyncio.Future] = {}
        self._register_handlers()

    # ── Send helpers ─────────────────────────────────────────────
    async def send_message(self, text: str, parse_mode: str = "HTML") -> None:
        await self.app.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode
        )

    async def send_job_notification(
        self,
        job_id: str,
        phase: str,
        summary: str,
        score: Optional[int] = None,
        model_used: Optional[str] = None,
        cost_estimate: Optional[str] = None,
    ) -> str:
        """
        Send a job phase completion notification with action buttons.
        Returns the user's chosen action (continue/edit/cancel/download/takeover).
        """
        score_line = f"Score: <b>{score}/100</b>\n" if score else ""
        model_line = f"Model: {model_used}" if model_used else ""
        cost_line  = f" (est. {cost_estimate})" if cost_estimate else ""

        text = (
            f"🎬 <b>Job #{job_id} — {phase.upper()} COMPLETE</b>\n"
            f"{score_line}"
            f"{model_line}{cost_line}\n\n"
            f"{summary}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Continue",  callback_data=f"{job_id}:{CB_CONTINUE}"),
                InlineKeyboardButton("✏️ Edit",      callback_data=f"{job_id}:{CB_EDIT}"),
            ],
            [
                InlineKeyboardButton("❌ Cancel",    callback_data=f"{job_id}:{CB_CANCEL}"),
                InlineKeyboardButton("⬇️ Download",  callback_data=f"{job_id}:{CB_DOWNLOAD}"),
            ],
            [
                InlineKeyboardButton("🔀 Take Over", callback_data=f"{job_id}:{CB_TAKEOVER}"),
            ],
        ])
        await self.app.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return await self._wait_for_callback(job_id)

    async def send_cost_prompt(
        self,
        job_id: str,
        model_name: str,
        estimated_cost: str,
        reason: str,
    ) -> bool:
        """
        Ask user whether to use a paid API.
        Returns True (proceed) or False (use Ollama instead).
        """
        text = (
            f"💰 <b>Paid API Request — Job #{job_id}</b>\n\n"
            f"Model: <b>{model_name}</b>\n"
            f"Estimated cost: <b>{estimated_cost}</b>\n"
            f"Reason: {reason}\n\n"
            f"Proceed with paid model or use Ollama (free)?"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"✅ Use {model_name}", callback_data=f"{job_id}:cost_yes"),
            InlineKeyboardButton("🆓 Use Ollama",        callback_data=f"{job_id}:cost_no"),
        ]])
        await self.app.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        result = await self._wait_for_callback(f"{job_id}_cost")
        return result == "cost_yes"

    async def send_opportunity_notification(
        self,
        topic: str,
        popularity: int,
        channel_name: str,
        suggested_video: str,
        suggested_product: str,
    ) -> str:
        text = (
            f"📊 <b>New Opportunity Found</b>\n\n"
            f"Trend: <b>{topic}</b> (Popularity: {popularity}/100)\n"
            f"Channel: {channel_name}\n\n"
            f"📹 Suggested video: {suggested_video}\n"
            f"📦 Suggested product: {suggested_product}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Produce", callback_data=f"opp:{topic}:produce"),
            InlineKeyboardButton("✏️ Details", callback_data=f"opp:{topic}:detail"),
            InlineKeyboardButton("❌ Skip",    callback_data=f"opp:{topic}:skip"),
        ]])
        await self.app.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return await self._wait_for_callback(f"opp_{topic}")

    # ── Callback waiting ─────────────────────────────────────────
    async def _wait_for_callback(self, key: str, timeout: int = 86400) -> str:
        """Block until user presses a button (or timeout after 24h)."""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_callbacks[key] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            log.warning(f"Callback timeout for key: {key}")
            return CB_CANCEL

    # ── Handlers ─────────────────────────────────────────────────
    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start",           self._cmd_start))
        self.app.add_handler(CommandHandler("status",         self._cmd_status))
        self.app.add_handler(CommandHandler("cancel",         self._cmd_cancel))
        self.app.add_handler(CommandHandler("mode",           self._cmd_mode))
        self.app.add_handler(CommandHandler("report",         self._cmd_report))
        self.app.add_handler(CommandHandler("backup",         self._cmd_backup))
        self.app.add_handler(CommandHandler("add_channel",    self._cmd_add_channel))
        self.app.add_handler(CommandHandler("list_channels",  self._cmd_list_channels))
        self.app.add_handler(CommandHandler("produce_video",  self._cmd_produce_video))
        self.app.add_handler(CommandHandler("product_analyze",self._cmd_product_analyze))
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 <b>YouTube & E-Commerce Automation System</b>\n\n"
            "Commands:\n"
            "/mode standard|creative|urgent\n"
            "/status &lt;job_id&gt;\n"
            "/cancel &lt;job_id&gt;\n"
            "/report weekly|opportunity\n"
            "/produce_video &lt;topic&gt;\n"
            "/product_analyze &lt;url&gt;\n"
            "/add_channel &lt;name&gt; &lt;url&gt;\n"
            "/list_channels\n"
            "/backup",
            parse_mode="HTML"
        )

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args
        if not args:
            await update.message.reply_text("Usage: /status <job_id>")
            return
        job_id = args[0].upper()
        await update.message.reply_text(f"🔍 Checking status for job #{job_id}…")
        # workflow_manager integration handled via main.py

    async def _cmd_cancel(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args
        if not args:
            await update.message.reply_text("Usage: /cancel <job_id>")
            return
        await update.message.reply_text(f"❌ Cancellation requested for job #{args[0].upper()}")

    async def _cmd_mode(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args
        if not args or args[0] not in ("standard", "creative", "urgent"):
            await update.message.reply_text("Usage: /mode standard|creative|urgent")
            return
        mode = args[0]
        await update.message.reply_text(f"✅ Mode set to: <b>{mode}</b>", parse_mode="HTML")

    async def _cmd_report(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args
        rtype = args[0] if args else "weekly"
        await update.message.reply_text(f"📊 Generating {rtype} report…")

    async def _cmd_backup(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("💾 Manual backup started…")

    async def _cmd_add_channel(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        args = ctx.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /add_channel <name> <youtube_url>")
            return
        name, url = args[0], args[1]
        await update.message.reply_text(
            f"🔐 Starting OAuth flow for channel: <b>{name}</b>\n"
            f"URL: {url}\n\n"
            f"A browser link will be sent shortly…",
            parse_mode="HTML"
        )

    async def _cmd_list_channels(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📋 Fetching channel list…")

    async def _cmd_produce_video(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        topic = " ".join(ctx.args) if ctx.args else ""
        if not topic:
            await update.message.reply_text("Usage: /produce_video <topic>")
            return
        await update.message.reply_text(f"🎬 Video production queued for: <b>{topic}</b>", parse_mode="HTML")

    async def _cmd_product_analyze(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        url = ctx.args[0] if ctx.args else ""
        if not url:
            await update.message.reply_text("Usage: /product_analyze <url>")
            return
        await update.message.reply_text(f"🔍 Product analysis queued for:\n{url}")

    async def _handle_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data  # format: "JOB_ID:action" or "opp:topic:action"

        parts = data.split(":", 1)
        if len(parts) == 2:
            key, action = parts
            if key in self._pending_callbacks:
                future = self._pending_callbacks.pop(key)
                if not future.done():
                    future.set_result(action)
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"✅ Action recorded: <b>{action}</b>", parse_mode="HTML")

    # ── Run ──────────────────────────────────────────────────────
    def run(self):
        log.info("Telegram bot starting…")
        self.app.run_polling(drop_pending_updates=True)


# ── EKLENEN ÖZELLİKLER ───────────────────────────────────────────
# 1. Doğal dil düzenleme mesajlarını dinle
# 2. Resim / video referans al
# 3. Bekleyen text_* callback'leri çöz


def _register_extra_handlers(self):
    """
    Bu metodu __init__ içinde çağır.
    Metin mesajları ve medya dosyaları için handler ekler.
    """
    # Düz metin mesajları — düzenleme talimatları için
    self.app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message)
    )
    # Fotoğraf — referans görsel
    self.app.add_handler(
        MessageHandler(filters.PHOTO, self._handle_photo)
    )
    # Video / belge (mp4 vs.)
    self.app.add_handler(
        MessageHandler(filters.VIDEO | filters.Document.VIDEO, self._handle_video_file)
    )


async def _handle_text_message(self, update, ctx):
    """
    Kullanıcı düz metin mesajı gönderdi.
    Eğer bekleyen bir text_* callback varsa çöz.
    Yoksa genel bir yanıt ver.
    """
    text    = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # Bekleyen text callback var mı?
    pending_key = None
    for key in list(self._pending_callbacks.keys()):
        if key.startswith("text_"):
            pending_key = key
            break

    if pending_key:
        future = self._pending_callbacks.pop(pending_key)
        if not future.done():
            future.set_result(text)
        await update.message.reply_text(
            f"✏️ Düzenleme talimatı alındı:\n<i>{text}</i>\n\nUygulanıyor...",
            parse_mode="HTML"
        )
    else:
        # Aktif iş yoksa komut önerisi sun
        await update.message.reply_text(
            "💡 Komutlar için /start yazabilirsin.\n"
            "Aktif bir iş düzenlemek için önce bir iş başlat.",
            parse_mode="HTML"
        )


async def _handle_photo(self, update, ctx):
    """
    Kullanıcı referans resim gönderdi.
    Dosyayı indir, stil analizi yap, profili kaydet.
    """
    import os
    photo   = update.message.photo[-1]  # En yüksek kalite
    caption = update.message.caption or ""

    await update.message.reply_text(
        "🖼️ Referans görsel alındı. Stil analizi yapılıyor..."
    )

    try:
        file = await ctx.bot.get_file(photo.file_id)
        save_path = f"/app/jobs/ref_image_{photo.file_id[:8]}.jpg"
        os.makedirs("/app/jobs", exist_ok=True)
        await file.download_to_drive(save_path)

        # Stil analizi
        from ai_synthesizer import AISynthesizer
        synth = AISynthesizer(self)
        style = synth.analyze_reference_image(save_path, caption or "reference image")

        if style:
            # Stil profilini kaydet
            import json
            profile_path = "/app/backups/reference_style_profile.json"
            os.makedirs("/app/backups", exist_ok=True)
            with open(profile_path, "w") as f:
                json.dump(style, f, indent=2)

            await update.message.reply_text(
                f"✅ <b>Stil Profili Çıkarıldı</b>\n\n"
                f"🎨 Stil: <b>{style.get('style_name','')}</b>\n"
                f"🌡️ Ruh hali: <b>{style.get('mood','')}</b>\n"
                f"🎨 Renkler: {', '.join(style.get('dominant_colors',[])[:3])}\n"
                f"🔑 Anahtar kelimeler: {', '.join(style.get('style_keywords',[])[:4])}\n\n"
                f"⚖️ <b>Etki ağırlığı: %35</b>\n"
                f"<i>Sistem kendi kararının %65'ini korur. Referansın etkisi hafif yönlendirme olarak uygulanır.\n"
                f"Sonraki video/thumbnail üretimlerinde bu stil referans alınacak.</i>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                "⚠️ Stil analizi yapılamadı. Görsel kaydedildi ama profil çıkarılamadı."
            )

        # Bekleyen ref_image callback varsa çöz
        for key in list(self._pending_callbacks.keys()):
            if key.startswith("ref_image"):
                future = self._pending_callbacks.pop(key)
                if not future.done():
                    future.set_result(save_path)
                break

    except Exception as e:
        log.error(f"Photo handling failed: {e}")
        await update.message.reply_text(f"❌ Görsel işlenemedi: {e}")


async def _handle_video_file(self, update, ctx):
    """
    Kullanıcı referans video gönderdi.
    İlk kareyi çıkar, stil analizi yap.
    """
    import os
    video = update.message.video or update.message.document

    await update.message.reply_text(
        "🎬 Referans video alındı. İlk kare analiz ediliyor..."
    )

    try:
        file      = await ctx.bot.get_file(video.file_id)
        save_path = f"/app/jobs/ref_video_{video.file_id[:8]}.mp4"
        os.makedirs("/app/jobs", exist_ok=True)
        await file.download_to_drive(save_path)

        from ai_synthesizer import AISynthesizer
        synth = AISynthesizer(self)
        style = synth.analyze_reference_image(save_path, "video reference")  # frame çıkarır içeride

        if style:
            import json
            with open("/app/backups/reference_style_profile.json", "w") as f:
                json.dump(style, f, indent=2)

            await update.message.reply_text(
                f"✅ <b>Video Stil Profili Çıkarıldı</b>\n\n"
                f"🎨 Stil: <b>{style.get('style_name','')}</b>\n"
                f"🌡️ Ruh hali: <b>{style.get('mood','')}</b>\n\n"
                f"<i>Sonraki üretimlerde bu stil referans alınacak.</i>",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("⚠️ Video analiz edilemedi.")

    except Exception as e:
        log.error(f"Video handling failed: {e}")
        await update.message.reply_text(f"❌ Video işlenemedi: {e}")


# Handler'ları TelegramHandler sınıfına ekle
TelegramHandler._handle_text_message = _handle_text_message
TelegramHandler._handle_photo        = _handle_photo
TelegramHandler._handle_video_file   = _handle_video_file
TelegramHandler._register_extra_handlers = _register_extra_handlers

# __init__ içinde extra handler'ları da kaydet
_original_init = TelegramHandler.__init__
def _new_init(self):
    _original_init(self)
    _register_extra_handlers(self)
TelegramHandler.__init__ = _new_init
