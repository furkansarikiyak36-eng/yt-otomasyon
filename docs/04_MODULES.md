# Module Reference

Quick reference for every module: what it does, inputs, outputs, how to test.

---

## Foundation Modules (Phase 0)

### `main.py`
Flask app + startup orchestrator.  
**Endpoints:**
- `GET /health` — system status + queue summary
- `POST /webhook/gumroad` — receives n8n-forwarded Gumroad events
- `POST /webhook/shopify` — receives n8n-forwarded Shopify events
- `POST /webhook/n8n` — generic n8n → Python bridge

**Test:** `curl http://localhost:5000/health`

---

### `config.py`
All settings from `.env`. Central source of truth.  
**Usage:** `from config import Config; Config.TELEGRAM_BOT_TOKEN`  
**Validation:** `Config.validate()` — call on startup, raises if required vars missing.

---

### `queue_manager.py`
RAM-aware async job queue.  
**Job types:** `HEAVY` (FFmpeg/Ollama/Kokoro), `LIGHT` (API calls), `URGENT` (runs next)  
**Rule:** Only 1 HEAVY job at a time. Max 2 LIGHT jobs simultaneously.  
**Test:** `pytest tests/test_queue.py -v`

---

### `workflow_manager.py`
Job state machine. Every job is a JSON file in `/app/jobs/`.  
**Phases:** `idea → script → assets → produce → upload → approval → published`  
**Crash-safe:** On restart, all `status=running` jobs resume automatically.

---

### `sheets_manager.py`
Google Sheets R/W with SQLite mirror.  
**Read:** Local SQLite first → Sheets fallback  
**Write:** Sheets first → SQLite sync → `pending_sync` on failure  
**Replay:** Every 15 min via scheduler  
**Test:** `pytest tests/test_sheets.py -v`

---

### `telegram_handler.py`
Telegram bot for all user interaction.  
**Commands:** `/start`, `/status`, `/cancel`, `/mode`, `/report`, `/backup`, `/add_channel`, `/list_channels`, `/produce_video`, `/product_analyze`  
**Approval buttons:** Continue / Edit / Cancel / Download / Take Over

---

### `monitoring.py`
Sentry + Telegram critical alerts.  
**Usage:** `from monitoring import capture_exception; capture_exception(e, {"job_id": "ABC"})`

---

### `github_backup.py`
Daily GitHub push of Python files + job JSONs + n8n workflow JSONs.  
**Manual run:** `docker compose exec app python github_backup.py`

---

### `scheduler.py`
APScheduler cron configuration.  
**Jobs:**
| Schedule | Job |
|----------|-----|
| Every 15 min | `pending_sync` replay |
| Daily 02:00 | GitHub backup |
| Sunday 03:00 | Sheets JSON backup |
| Monday 09:00 | Weekly trend scan |
| Sunday 10:00 | Weekly progress report |

---

## Content Production Modules (Phase 1–2)

### `global_scanner.py`
Scans Google Trends, YouTube Trending, Reddit for opportunities.  
**Input:** keyword list (configurable)  
**Output:** ranked list saved to `trend_data` Sheets tab  
**Phase 1:** Weekly. **Phase 3:** Hourly.

---

### `ai_synthesizer.py`
Turns trend data into structured video scripts and product concepts.  
**Default model:** Ollama `qwen2.5:3b` (free, local)  
**Paid option:** Gemini Flash — shown as cost prompt, requires your approval  
**Output:** JSON with title, hook, script_outline, tags, cta

---

### `video_producer.py`
Full video production pipeline: TTS → visuals → FFmpeg assembly.  
**TTS:** Kokoro v1 (port 8880) → Edge-TTS fallback  
**Visuals:** Pexels API  
**Thumbnail:** Pillow template (NOT Stable Diffusion)  
**Output:** `{job_id}_draft.mp4` + `thumbnail.jpg` in `/app/jobs/{job_id}/`

---

### `youtube_uploader.py`
Uploads video as **private draft** to the correct channel.  
**OAuth:** Per-channel Fernet-encrypted refresh tokens in `channels` Sheets tab  
**Output:** YouTube video ID  
**Note:** Always uploads as private — you control when to publish

---

### `product_producer.py`
Generates PDF digital products and uploads as Gumroad draft.  
**PDF engine:** WeasyPrint (primary) → ReportLab (fallback)  
**Output:** PDF file + Gumroad draft URL  
**Note:** No sales tracking — enter sales manually in Sheets

---

### `email_lead_magnet.py`
Adds Gumroad free-product downloaders to Kit.  
**Triggered by:** n8n workflow 01  
**Output:** Kit subscriber with product tag

---

### `convertkit_api.py`
Kit (ConvertKit) API wrapper.  
**Rate limit:** 120 req/min → 0.5s between requests  
**Methods:** `add_subscriber`, `add_tag`, `send_broadcast`, `get_subscribers`

---

## Segmentation & Analysis (Phase 2.5)

### `segmentation_engine.py`
Segments Kit subscribers: hot (≤14 days) / warm (15–45 days) / cold (45+ days).  
Removes cold leads (60+ days inactive) to stay under Kit free tier.  
**Output:** Segment counts in Sheets + Telegram report

---

### `ornek_ogrenme.py`
**Phase 2.5:** Tracks title edits → JSON style profile  
**Phase 3+:** Ollama diff analysis (placeholder, not yet implemented)  
**Profile location:** `/app/backups/style_profile.json`  
**Used by:** `ai_synthesizer.py` to adjust future prompts

---

### `product_analyzer.py`
Scrapes non-Amazon product URLs, cross-references trends, outputs PDF report.  
**Safety:** Amazon URLs blocked — PAAPI only  
**Scraping measures:** cloudscraper, user-agent rotation, 1–3s random delays  
**Output:** PDF report in `/app/jobs/{job_id}_product_report.pdf`

---

### `shopify_analyzer.py`
**Read-only** analysis of YOUR Shopify store products.  
**Privacy:** Connects only to your store via your API key. Invisible to outsiders.  
**Output:** PDF report ranking your products by trend alignment score

---

### `strategy_reporter.py`
Aggregates all data into weekly PDF + Telegram summary.  
**Triggered:** Sunday 10:00 via scheduler  
**Output:** PDF + Telegram message with key metrics

---

## n8n Workflows

### `01_gumroad_sale.json`
**Trigger:** Gumroad sale or free download webhook  
**Actions:** Parse event → Kit tag → Python notification → Telegram alert  
**Setup:** Configure Gumroad Ping URL to `http://YOUR_SERVER:5678/webhook/gumroad-sale`

### `02_youtube_metrics.json`
**Trigger:** Video upload webhook from `youtube_uploader.py`  
**Actions:** Wait 48h → fetch YouTube metrics → update Sheets → alert if low performance  
**Setup:** `youtube_uploader.py` must POST to `http://n8n:5678/webhook/youtube-uploaded` after upload

---

## Adding a New Module

1. Create `your_module.py` in project root
2. Follow pattern: class with `__init__`, async methods, uses `get_logger`
3. Add to `scheduler.py` if time-triggered
4. Add to `main.py` webhook if event-triggered
5. Write tests in `tests/test_your_module.py`
6. Run `docker compose exec app pytest tests/test_your_module.py -v`
7. Commit → GitHub backup runs automatically at 02:00
