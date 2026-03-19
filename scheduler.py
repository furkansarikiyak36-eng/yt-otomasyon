"""
scheduler.py — MINDFULLY BRAND
────────────────────────────────
Her kanal için ayrı içerik takvimi:
  Channel 1 (Fitness)     : Pazartesi, Çarşamba, Cuma  10:00
  Channel 2 (Ambiance)    : Salı, Perşembe             18:00
  Channel 3 (Documentary) : Cumartesi                  11:00
  Social Organic          : Her gün                    12:00
  Social Shopify          : n8n webhook tetikleyici
  Sistem görevleri        : Backup, sync, raporlar
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import Config
from utils.logger import get_logger

log = get_logger("scheduler")


def build_scheduler(sheets_manager, github_backup,
                    workflow_manager=None, telegram_handler=None) -> AsyncIOScheduler:

    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

    # ════════════════════════════════════════════════════════════
    # SİSTEM GÖREVLERİ
    # ════════════════════════════════════════════════════════════

    # Her 15 dk: pending_sync replay
    scheduler.add_job(
        sheets_manager.replay_pending_sync,
        trigger="interval", minutes=15,
        id="pending_sync_replay",
        name="Sheets pending sync replay",
    )

    # Her gün 02:00: GitHub backup
    scheduler.add_job(
        github_backup.run_full_backup,
        trigger=CronTrigger(hour=2, minute=0),
        id="github_backup",
        name="Daily GitHub backup",
    )

    # Pazar 03:00: Sheets JSON backup
    async def sheets_backup():
        import os
        sheets_manager.backup_all_to_json(os.path.join("/app/backups", "sheets"))
        log.info("Weekly Sheets backup complete")

    scheduler.add_job(
        sheets_backup,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="sheets_backup",
        name="Weekly Sheets JSON backup",
    )

    # Pazar 10:00: Haftalık strateji raporu
    async def weekly_report():
        log.info("Weekly strategy report triggered")
        if telegram_handler:
            await telegram_handler.send_message(
                "📊 <b>Haftalık Rapor Başlıyor...</b>\n"
                "Tüm kanallar için performans analizi hazırlanıyor."
            )

    scheduler.add_job(
        weekly_report,
        trigger=CronTrigger(day_of_week="sun", hour=10, minute=0),
        id="weekly_report",
        name="Weekly strategy report",
    )

    # ════════════════════════════════════════════════════════════
    # KANAL 2: FİTNESS — Yoga/workout/HIIT — Pazartesi, Çarşamba, Cuma 09:00
    # ════════════════════════════════════════════════════════════
    async def fitness_content_trigger():
        ch = Config.get_channel("channel_fitness")
        log.info(f"Content trigger: {ch['name']}")
        if telegram_handler:
            await telegram_handler.send_message(
                f"🏋️ <b>{ch['name']} — İçerik Üretimi Başlıyor</b>\n"
                f"Tema: Fitness | Format: Kısa + Uzun Video\n"
                f"Trend taraması yapılıyor..."
            )
        # Phase 1+ aktivasyon:
        # from global_scanner import GlobalScanner
        # from ai_synthesizer import AISynthesizer
        # trends = await GlobalScanner().run_weekly_scan(
        #     keywords=Config.get_channel_keywords("channel_fitness")
        # )
        # script = await AISynthesizer().synthesize_video_topic(
        #     trend=trends[0], channel_theme="fitness", job_id=...
        # )

    scheduler.add_job(
        fitness_content_trigger,
        trigger=CronTrigger(day_of_week="mon,wed,fri", hour=9, minute=0),
        id="fitness_content",
        name="Fitness Channel — content production",
    )

    # ════════════════════════════════════════════════════════════
    # KANAL 1: AMBİYANS — Telifsiz müzik loop — Salı, Perşembe, Cumartesi 18:00
    # ════════════════════════════════════════════════════════════
    async def ambiance_content_trigger():
        ch = Config.get_channel("channel_ambiance")
        log.info(f"Content trigger: {ch['name']}")
        if telegram_handler:
            await telegram_handler.send_message(
                f"🎵 <b>{ch['name']} — Ambiyans Video Üretimi</b>\n"
                f"Format: 30-60 dk loop video\n"
                f"Müzik stili: Calm / Lofi"
            )
        # Phase 2+ aktivasyon:
        # from ambiance_video_producer import AmbianceVideoProducer
        # await AmbianceVideoProducer().produce(
        #     job_id=..., channel_id="channel_ambiance", theme="lofi_study"
        # )

    scheduler.add_job(
        ambiance_content_trigger,
        trigger=CronTrigger(day_of_week="tue,thu,sat", hour=18, minute=0),
        id="ambiance_content",
        name="Ambiance Channel — content production",
    )

    # ════════════════════════════════════════════════════════════
    # KANAL 3: BELGESEL — Yiyecek/bilim/tarih — Pazar 14:00
    # ════════════════════════════════════════════════════════════
    async def documentary_content_trigger():
        ch = Config.get_channel("channel_documentary")
        log.info(f"Content trigger: {ch['name']}")
        if telegram_handler:
            await telegram_handler.send_message(
                f"🎬 <b>{ch['name']} — Belgesel Üretimi</b>\n"
                f"Format: 15-30 dk story-driven video\n"
                f"Müzik stili: Sinematik"
            )
        # Phase 2+ aktivasyon:
        # from documentary_producer import DocumentaryProducer
        # await DocumentaryProducer().produce(
        #     job_id=..., channel_id="channel_documentary"
        # )

    scheduler.add_job(
        documentary_content_trigger,
        trigger=CronTrigger(day_of_week="sun", hour=14, minute=0),
        id="documentary_content",
        name="Documentary Channel — content production",
    )

    # ════════════════════════════════════════════════════════════
    # SOCIAL 1: ORGANIC — Her gün 12:00
    # ════════════════════════════════════════════════════════════
    async def social_organic_trigger():
        pipeline = Config.SOCIAL_PIPELINES["social_organic"]
        log.info(f"Social trigger: {pipeline['name']}")
        if telegram_handler:
            await telegram_handler.send_message(
                f"📱 <b>Günlük Sosyal Medya İçeriği</b>\n"
                f"Platformlar: Instagram · TikTok · Pinterest\n"
                f"YouTube kliplerinden kısa format üretiliyor..."
            )
        # Phase 2+ aktivasyon:
        # from social_producer import SocialProducer
        # await SocialProducer().produce_daily_clips(pipeline)

    scheduler.add_job(
        social_organic_trigger,
        trigger=CronTrigger(hour=12, minute=0),
        id="social_organic",
        name="Social Organic — daily clips",
    )

    # ════════════════════════════════════════════════════════════
    # SOCIAL 2: SHOPİFY — n8n webhook tetikleyici
    # Manuel burada değil, n8n'den Flask'a /webhook/shopify geliyor
    # main.py içinde handle ediliyor
    # ════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════
    # HAFTALIK TREND TARAMASI — Pazartesi 09:00 (tüm kanallar)
    # ════════════════════════════════════════════════════════════
    async def weekly_trend_scan():
        log.info("Weekly trend scan — all channels")
        for channel_id in Config.get_all_channel_ids():
            ch = Config.get_channel(channel_id)
            log.info(f"  Scanning trends for: {ch['name']}")
            # Phase 1+ aktivasyon:
            # from global_scanner import GlobalScanner
            # await GlobalScanner().run_weekly_scan(
            #     keywords=Config.get_channel_keywords(channel_id)
            # )

    scheduler.add_job(
        weekly_trend_scan,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_trend_scan",
        name="Weekly trend scan — all channels",
    )


    # ── Haftalık disk temizleme ──────────────────────────────────
    async def disk_cleanup():
        import os, shutil
        jobs_dir = Config.JOBS_DIR
        cleaned  = 0
        freed_mb = 0
        if not os.path.exists(jobs_dir):
            return
        for job_dir in os.listdir(jobs_dir):
            full_path = os.path.join(jobs_dir, job_dir)
            if not os.path.isdir(full_path):
                continue
            # 14 günden eski job klasörlerini temizle
            import time
            age_days = (time.time() - os.path.getmtime(full_path)) / 86400
            if age_days > 14:
                size_mb = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, files in os.walk(full_path)
                    for f in files
                ) / 1024 / 1024
                shutil.rmtree(full_path, ignore_errors=True)
                cleaned  += 1
                freed_mb += size_mb

        # Disk durumu kontrolü
        total, used, free = shutil.disk_usage("/")
        free_gb  = free  / 1024**3
        used_pct = used / total * 100

        msg = (
            f"🧹 <b>Haftalık Disk Temizleme</b>\n"
            f"Temizlenen: {cleaned} job klasörü ({freed_mb:.0f} MB)\n"
            f"Disk durumu: {free_gb:.1f} GB boş ({used_pct:.0f}% kullanımda)"
        )
        if free_gb < 5:
            msg += "\n\n⚠️ <b>UYARI: Disk alanı kritik seviyede!</b>"
        if telegram_handler:
            await telegram_handler.send_message(msg)
        log.info(f"Disk cleanup: {cleaned} dirs removed, {freed_mb:.0f}MB freed, {free_gb:.1f}GB free")

    scheduler.add_job(
        disk_cleanup,
        trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),
        id="disk_cleanup",
        name="Weekly disk cleanup",
    )

    log.info(
        "Scheduler ready:\n"
        "  Fitness  : Mon/Wed/Fri 10:00\n"
        "  Ambiance : Tue/Thu 18:00\n"
        "  Docs     : Sat 11:00\n"
        "  Social   : Daily 12:00\n"
        "  Trends   : Mon 09:00\n"
        "  Report   : Sun 10:00\n"
        "  Backup   : Daily 02:00"
    )
    return scheduler
