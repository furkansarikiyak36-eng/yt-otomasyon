"""
config.py — MINDFULLY BRAND Automation System
──────────────────────────────────────────────
3 YouTube Channels:
  1. Ambiance  : Telifsiz müzik loop'ları + arka plan animasyonu
  2. Fitness   : Yoga / workout / HIIT / spor egzersiz videoları
  3. Documentary: Yiyecek / bilim / tarih / konu bazlı uzun belgeseller

2 Social Media Pipelines:
  1. Organic   : YouTube içeriklerinden günlük kısa klipler
  2. Shopify   : Ürün tanıtım içeriği (webhook tetikleyici)
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    # ── Telegram ─────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

    # ── Google ───────────────────────────────────────────────────
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/credentials.json")
    GOOGLE_SHEETS_ID          = os.getenv("GOOGLE_SHEETS_ID", "1OoxhsKaWSPLKaIs0O4klzIjHdwZQoQ7fLidkFkNS2Kg")

    # ── GitHub ───────────────────────────────────────────────────
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO  = os.getenv("GITHUB_REPO")

    # ── Sentry ───────────────────────────────────────────────────
    SENTRY_DSN = os.getenv("SENTRY_DSN")

    # ── Encryption ───────────────────────────────────────────────
    FERNET_KEY = os.getenv("FERNET_KEY")

    # ── Optional Cloud LLMs ──────────────────────────────────────
    GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
    CLAUDE_API_KEY   = os.getenv("CLAUDE_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    # ── Email ────────────────────────────────────────────────────
    KIT_API_KEY    = os.getenv("KIT_API_KEY")
    KIT_API_SECRET = os.getenv("KIT_API_SECRET")

    # ── Gumroad ──────────────────────────────────────────────────
    GUMROAD_ACCESS_TOKEN = os.getenv("GUMROAD_ACCESS_TOKEN")

    # ── Pexels ───────────────────────────────────────────────────
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

    # ── Freesound (telifsiz müzik) ───────────────────────────────
    FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")

    # ── Social Media ─────────────────────────────────────────────
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    INSTAGRAM_BUSINESS_ID  = os.getenv("INSTAGRAM_BUSINESS_ID")
    TIKTOK_ACCESS_TOKEN    = os.getenv("TIKTOK_ACCESS_TOKEN")
    PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
    PINTEREST_BOARD_ID     = os.getenv("PINTEREST_BOARD_ID")

    # ── Shopify ──────────────────────────────────────────────────
    SHOPIFY_STORE_URL  = os.getenv("SHOPIFY_STORE_URL")
    SHOPIFY_API_KEY    = os.getenv("SHOPIFY_API_KEY")
    SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")

    # ── Printify ─────────────────────────────────────────────────
    PRINTIFY_API_KEY = os.getenv("PRINTIFY_API_KEY")

    # ── Paths ────────────────────────────────────────────────────
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/yt-otomasyon.sqlite")
    JOBS_DIR       = os.getenv("JOBS_DIR",        "/app/jobs")
    LOG_DIR        = os.getenv("LOG_DIR",          "/app/logs")
    BACKUP_DIR     = os.getenv("BACKUP_DIR",       "/app/backups")

    # ── Server limits ────────────────────────────────────────────
    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", 2))
    RAM_LIMIT_GB        = float(os.getenv("RAM_LIMIT_GB", 3.5))
    LOG_LEVEL           = os.getenv("LOG_LEVEL", "INFO")

    # ════════════════════════════════════════════════════════════
    # 3 YOUTUBE CHANNELS — MINDFULLY BRAND
    # ════════════════════════════════════════════════════════════
    CHANNELS = {

        # ── KANAL 1: AMBİANS ────────────────────────────────────
        # Format   : 30–60 dk loop videoları
        # İçerik   : Telifsiz müzik birleştirme (lo-fi, motivasyon,
        #             sakinleştirici, çalışma, uyku müziği)
        #             + arka plan animasyonu (partiküller, doğa, soyut)
        # Kaynak   : Freesound API + Pixabay Music (telifsiz)
        #             Pexels video (arka plan görseli)
        # Yayın    : Salı, Perşembe, Cumartesi 18:00
        "channel_ambiance": {
            "name":           "Mindfully Ambiance",
            "theme":          "ambiance",
            "video_types":    ["ambient"],
            "duration_min":   30,
            "duration_max":   60,
            "music_style":    "lofi_relaxing",
            "color_palette":  ["#7EB8B3", "#0D0D0D"],
            "target_audience":"Öğrenciler, uzaktan çalışanlar, uyku sorunu yaşayanlar",
            "schedule":       {"days": ["tue", "thu", "sat"], "hour": 18},
            "max_per_day":    1,
            "music_moods":    ["lofi", "motivational", "relaxing", "sleep", "study", "focus", "meditation"],
            "animation_types":["particles", "nature_loop", "abstract_waves", "starfield", "aurora"],
            "music_sources":  ["freesound", "pixabay_music"],
            "keywords": [
                "lofi hip hop study", "relaxing music sleep", "motivational background music",
                "focus music work", "calm music anxiety", "sleep music 8 hours",
                "study music concentration", "meditation music", "spa relaxing music",
                "deep focus music", "lofi beats chill", "ambient music relax",
                "nature sounds sleep", "rain sounds study", "white noise focus"
            ],
        },

        # ── KANAL 2: FİTNESS ────────────────────────────────────
        # Format   : Kısa (5–10 dk) + Orta (15–20 dk) videolar
        # İçerik   : Egzersiz nasıl yapılır videoları
        #             - Yoga (başlangıç, orta, ileri)
        #             - HIIT (evde, spor salonu)
        #             - Workout (karın, sırt, bacak, kol)
        #             - Stretching / esneme
        #             - Spor türü tanıtımları ve faydaları
        # Yayın    : Pazartesi, Çarşamba, Cuma 09:00
        "channel_fitness": {
            "name":           "Mindfully Fitness",
            "theme":          "fitness",
            "video_types":    ["short", "tutorial"],
            "duration_min":   5,
            "duration_max":   20,
            "music_style":    "energetic",
            "color_palette":  ["#FF6B35", "#1C1C1C"],
            "target_audience":"18–45 sağlık odaklı bireyler, ev egzersizi arayanlar",
            "schedule":       {"days": ["mon", "wed", "fri"], "hour": 9},
            "max_per_day":    2,
            "exercise_types": [
                "yoga", "hiit", "workout", "stretching", "pilates",
                "cardio", "strength_training", "abs", "back", "legs", "arms"
            ],
            "content_formats": [
                "how_to_exercise",   # nasıl yapılır adım adım
                "benefits_video",    # faydaları anlat
                "beginner_guide",    # başlangıç rehberi
                "full_routine",      # tam antrenman rutini
                "sport_intro",       # spor türü tanıtımı
            ],
            "keywords": [
                "yoga for beginners", "home workout no equipment", "HIIT cardio workout",
                "how to do push ups correctly", "yoga benefits", "stretching routine morning",
                "abs workout 10 minutes", "full body workout beginner", "pilates for flexibility",
                "back pain exercises", "leg day workout home", "how to lose weight exercise",
                "yoga poses for anxiety", "HIIT for weight loss", "workout motivation",
                "gym exercises tutorial", "strength training beginners", "daily exercise routine"
            ],
        },

        # ── KANAL 3: BELGESEL ───────────────────────────────────
        # Format   : Uzun (20–40 dk) belgesel videolar
        # İçerik   : Konu odaklı derinlemesine anlatım
        #             - Yiyecek tarihi (pizzanın tarihi, baharatlar, vb.)
        #             - Bilim belgeselleri (evren, DNA, sinir sistemi)
        #             - Tarih belgeselleri (uygarlıklar, keşifler)
        #             - Konu başlıkları AI tarafından seçilir, onaylanır
        # Yayın    : Pazar 14:00
        "channel_documentary": {
            "name":           "Mindfully Docs",
            "theme":          "documentary",
            "video_types":    ["documentary"],
            "duration_min":   20,
            "duration_max":   40,
            "music_style":    "cinematic",
            "color_palette":  ["#E94560", "#1A1A2E"],
            "target_audience":"25–55 meraklı, bilim ve tarih ilgilileri",
            "schedule":       {"days": ["sun"], "hour": 14},
            "max_per_day":    1,
            "documentary_categories": [
                "food_history",      # yiyeceklerin tarihi ve kültürü
                "science",           # bilim konuları (evren, biyoloji, fizik)
                "history",           # tarihsel olaylar ve uygarlıklar
                "nature",            # doğa ve hayvanlar
                "psychology",        # insan psikolojisi ve davranışı
                "technology",        # teknoloji tarihi ve geleceği
            ],
            "topic_selection":  "ai_generated_approved",  # AI önerir, sen onaylarsın
            "keywords": [
                "history of pizza documentary", "science of sleep explained",
                "how the universe began", "history of spices trade",
                "human brain documentary", "ancient civilizations explained",
                "how food shapes culture", "DNA science explained simply",
                "history of bread making", "solar system documentary",
                "psychology of habits", "history of medicine",
                "how coffee changed the world", "evolution explained",
                "climate science documentary", "deep sea mysteries"
            ],
        },
    }

    # ════════════════════════════════════════════════════════════
    # AMBIANCE KANAL — TELİFSİZ MÜZİK KAYNAKLARI
    # ════════════════════════════════════════════════════════════
    ROYALTY_FREE_SOURCES = {
        "freesound": {
            "api_url":  "https://freesound.org/apiv2",
            "license":  ["Creative Commons 0", "Attribution"],
            "formats":  ["mp3", "wav"],
        },
        "pixabay_music": {
            "api_url":  "https://pixabay.com/api/",
            "license":  "Pixabay License (commercial use ok)",
            "formats":  ["mp3"],
        },
        "youtube_audio_library": {
            "url":      "https://studio.youtube.com/channel/music",
            "license":  "YouTube Audio Library (free, no attribution)",
            "note":     "Manuel indirme gerektirir — API yok",
        },
        "incompetech": {
            "url":      "https://incompetech.com/music/royalty-free/",
            "license":  "CC BY 4.0 — attribution gerektirir",
            "note":     "Kevin MacLeod — yüksek kalite, geniş kategori",
        },
    }

    # ════════════════════════════════════════════════════════════
    # FITNESS KANAL — EGZERSİZ VİDEO YAPISI
    # ════════════════════════════════════════════════════════════
    FITNESS_VIDEO_STRUCTURE = {
        "how_to_exercise": [
            "intro_hook",        # 15 sn — bu videoyu neden izlemeli?
            "exercise_overview", # 30 sn — egzersiz tanıtımı
            "step_by_step",      # ana bölüm — adım adım gösterim
            "common_mistakes",   # 60 sn — yapılan hatalar
            "benefits",          # 60 sn — faydaları
            "outro_cta",         # 30 sn — CTA + abone ol
        ],
        "benefits_video": [
            "hook",              # 15 sn
            "benefit_1",         # 90 sn
            "benefit_2",         # 90 sn
            "benefit_3",         # 90 sn
            "science_behind",    # 60 sn — bilimsel arka plan
            "how_to_start",      # 60 sn — nasıl başlanır
            "outro_cta",         # 30 sn
        ],
        "full_routine": [
            "intro_warmup",      # 2 dk
            "main_exercises",    # 10–15 dk
            "cooldown",          # 3 dk
            "recap",             # 60 sn
        ],
    }

    # ════════════════════════════════════════════════════════════
    # BELGESEL KANAL — KONU SEÇİM KATEGORİLERİ
    # ════════════════════════════════════════════════════════════
    DOCUMENTARY_TOPIC_TEMPLATES = {
        "food_history": "The history and cultural journey of {food_item} — from ancient origins to modern day",
        "science":      "How {science_topic} actually works — explained simply and visually",
        "history":      "The untold story of {historical_topic} — what really happened",
        "nature":       "The secret world of {nature_topic} — a deep dive",
        "psychology":   "The psychology of {behavior} — what science says",
        "technology":   "How {technology} changed the world — a documentary",
    }

    DOCUMENTARY_STRUCTURE = [
        "cold_open",       # 60 sn — en çarpıcı gerçek ile başla
        "context",         # 3 dk — konu bağlamı
        "chapter_1",       # 6–8 dk — ana bölüm 1
        "chapter_2",       # 6–8 dk — ana bölüm 2
        "chapter_3",       # 6–8 dk — ana bölüm 3
        "surprising_fact", # 2 dk — beklenmedik bilgi
        "conclusion",      # 3 dk — sonuç ve etki
        "outro",           # 60 sn — CTA
    ]

    # ════════════════════════════════════════════════════════════
    # 2 SOCIAL MEDIA PIPELINES
    # ════════════════════════════════════════════════════════════
    SOCIAL_PIPELINES = {
        "social_organic": {
            "name":        "Organic Social",
            "platforms":   ["instagram", "tiktok", "pinterest"],
            "source":      "youtube_clips",
            "schedule":    {"days": ["mon","tue","wed","thu","fri","sat","sun"], "hour": 12},
            "clip_length": {"instagram": 30, "tiktok": 60, "pinterest": 15},
            "auto_post":   True,
            "per_channel_content": {
                "channel_ambiance":    "aesthetic mood clip — 30 sn müzik önizlemesi",
                "channel_fitness":     "exercise tip clip — 60 sn egzersiz ipucu",
                "channel_documentary": "mind-blowing fact clip — 30 sn ilginç bilgi",
            }
        },
        "social_shopify": {
            "name":        "Shopify Product Social",
            "platforms":   ["instagram", "pinterest"],
            "source":      "shopify_products",
            "schedule":    {"trigger": "shopify_webhook"},
            "clip_length": {"instagram": 15, "pinterest": 10},
            "auto_post":   False,
            "description": "Shopify ürün içeriği — yeni ürün veya stok yenilemede tetiklenir"
        },
    }

    # ════════════════════════════════════════════════════════════
    # SHEETS TAB NAMES
    # ════════════════════════════════════════════════════════════
    SHEETS_VIDEO_LOG         = "video_log"
    SHEETS_TREND_DATA        = "trend_data"
    SHEETS_OPPORTUNITIES     = "opportunities"
    SHEETS_EMAIL_SUBSCRIBERS = "email_subscribers"
    SHEETS_SALES             = "sales"
    SHEETS_SEGMENTS          = "segments"
    SHEETS_CHANNELS          = "channels"
    SHEETS_CONTENT_CALENDAR  = "content_calendar"
    SHEETS_ERRORS            = "errors"
    SHEETS_USER_PREFERENCES  = "user_preferences"
    SHEETS_PENDING_SYNC      = "pending_sync"
    SHEETS_SOCIAL_LOG        = "social_log"
    SHEETS_SHOPIFY_PRODUCTS  = "shopify_products"
    SHEETS_MUSIC_LOG         = "music_log"       # telifsiz müzik takibi
    SHEETS_DOCUMENTARY_TOPICS = "documentary_topics"  # onaylanan belgesel konuları

    # ── Helpers ──────────────────────────────────────────────────
    @classmethod
    def get_channel(cls, channel_id: str) -> dict:
        return cls.CHANNELS.get(channel_id, {})

    @classmethod
    def get_all_channel_ids(cls) -> list:
        return list(cls.CHANNELS.keys())

    @classmethod
    def get_channel_keywords(cls, channel_id: str) -> list:
        return cls.CHANNELS.get(channel_id, {}).get("keywords", [])

    @classmethod
    def get_channel_by_theme(cls, theme: str) -> dict:
        for cid, ch in cls.CHANNELS.items():
            if ch["theme"] == theme:
                return {**ch, "channel_id": cid}
        return {}

    @classmethod
    def validate(cls):
        required = [
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHAT_ID",   cls.TELEGRAM_CHAT_ID),
            ("GOOGLE_SHEETS_ID",   cls.GOOGLE_SHEETS_ID),
            ("FERNET_KEY",         cls.FERNET_KEY),
            ("GITHUB_TOKEN",       cls.GITHUB_TOKEN),
            ("GITHUB_REPO",        cls.GITHUB_REPO),
        ]
        missing = [name for name, val in required if not val]
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
        return True
