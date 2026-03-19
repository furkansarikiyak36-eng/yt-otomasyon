# MINDFULLY BRAND — YouTube & E-Commerce Automation System

**Version:** 6  
**Project:** MINDFULLY BRAND  
**Sheet:** [Open Spreadsheet](https://docs.google.com/spreadsheets/d/1OoxhsKaWSPLKaIs0O4klzIjHdwZQoQ7fLidkFkNS2Kg)  
**Server:** Hetzner CX23 (€6/month)  
**Control:** Telegram bot  
**Stack:** Python · Docker · n8n · Ollama · Kokoro TTS · Google Sheets

---

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/yt-otomasyon.git
cd yt-otomasyon

# 2. Configure environment
cp .env.example .env
nano .env  # fill in required values

# 3. Start system
docker compose up -d --build

# 4. Send /start to your Telegram bot
```

Full setup instructions → [docs/00_SETUP.md](docs/00_SETUP.md)

---

## Project Structure

```
yt-otomasyon/
├── main.py                    # Flask app + startup
├── config.py                  # All settings from .env
├── queue_manager.py           # RAM-aware async job queue
├── workflow_manager.py        # Job state machine (idea→published)
├── sheets_manager.py          # Google Sheets + SQLite mirror
├── telegram_handler.py        # Telegram bot + approval buttons
├── scheduler.py               # APScheduler cron jobs
├── monitoring.py              # Sentry + Telegram alerts
├── github_backup.py           # Daily GitHub backup
│
├── global_scanner.py          # Phase 1: trend scanning
├── ai_synthesizer.py          # Phase 1: topic/product synthesis
├── video_producer.py          # Phase 1: video production
├── youtube_uploader.py        # Phase 1: YouTube draft upload
├── product_producer.py        # Phase 1: PDF product generation
├── email_lead_magnet.py       # Phase 1: Kit subscriber adding
├── convertkit_api.py          # Phase 1: Kit API wrapper
│
├── segmentation_engine.py     # Phase 2.5: subscriber segmentation
├── ornek_ogrenme.py           # Phase 2.5: style preference learning
├── product_analyzer.py        # Phase 2.5: competitor product analysis
├── shopify_analyzer.py        # Phase 4: your Shopify store analysis
├── strategy_reporter.py       # Phase 2.5: weekly reports
│
├── n8n_workflows/
│   ├── 01_gumroad_sale.json   # Gumroad → Kit + Sheets + Telegram
│   └── 02_youtube_metrics.json # 48h performance tracking
│
├── utils/
│   ├── logger.py
│   └── helpers.py
│
├── tests/
│   ├── test_sheets.py
│   └── test_queue.py
│
└── docs/
    ├── 00_SETUP.md            # Phase 0: server setup
    ├── 01_PHASE1.md           # Phase 1: first videos
    ├── 02_PHASE2.md           # Phase 2: complex products
    ├── 03_PHASE2_5_TO_5.md    # Phases 2.5 through 5
    ├── 04_MODULES.md          # Complete module reference
    ├── 05_N8N.md              # n8n integration guide
    ├── 06_SHOPIFY.md          # Shopify privacy & setup
    └── 07_TROUBLESHOOTING.md  # Common issues & fixes
```

---

## System Architecture

```
External Events (Gumroad, Shopify, Forms)
        │
       n8n  (event bridge — port 5678)
        │
  Python App  (workflow_manager — port 5000)
        │
    Telegram  (you — approvals)
```

**n8n role:** External webhook routing ONLY. Does not produce content.  
**Shopify:** Read-only, your store only, invisible to outsiders.

---

## Phase Overview

| Phase | Goal | Transition |
|-------|------|------------|
| 0 | Server + infrastructure | Container running |
| 1 | Trends + first videos | 50 subs, 10 videos |
| 2 | Paid products + long format | $200/mo, 500 subs |
| 2.5 | Segmentation + analysis | $500/mo |
| 3 | Real-time trends + reports | $1,000/mo |
| 4 | Shopify + Printify analysis | $1,500/mo, 3K subs |
| 5 | Full automation | <1hr/week |

---

## Critical Rules (Never Skip)

1. Every YouTube video: **50% uniqueness + human voice hook + AI disclosure**
2. Wellness content: **zero direct health claims**
3. Ads: **YouTube in-stream only** — no Meta Ads, no Google Display
4. Amazon: **PAAPI only** — never scrape
5. TikTok: **official API only, Phase 3+** — always keep Instagram/Pinterest as fallback

---

## Documentation

| Guide | Contents |
|-------|----------|
| [Setup](docs/00_SETUP.md) | Server, Docker, credentials, first run |
| [Phase 1](docs/01_PHASE1.md) | Trend scanning, first video, Kit setup |
| [Phase 2](docs/02_PHASE2.md) | Ollama, Kokoro, paid products, n8n metrics |
| [Phases 2.5–5](docs/03_PHASE2_5_TO_5.md) | Segmentation through full automation |
| [Modules](docs/04_MODULES.md) | Every module: inputs, outputs, test commands |
| [n8n](docs/05_N8N.md) | Workflow setup and maintenance |
| [Shopify](docs/06_SHOPIFY.md) | Privacy guarantees + setup |
| [Troubleshooting](docs/07_TROUBLESHOOTING.md) | Fixes for common issues |

---

## Financial Reality

| Scenario | 12-month net |
|----------|-------------|
| Pessimistic (most likely) | ~$400 |
| Moderate (target) | ~$2,600 |
| First 6 months | Likely $0 — normal |

Fixed cost: **€6/month**. Everything else optional and user-approved.

---

*System designed to grow with you — start Phase 0, validate, then scale.*
