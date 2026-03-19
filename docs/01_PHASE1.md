# Phase 1 — Trend Scanning & First Videos

**Goal:** 50 email subscribers, 10 videos produced.  
**Timeline:** Weeks 2–5  
**Weekly time required:** 2–3 hours

---

## What Gets Activated in Phase 1

| Module | Role |
|--------|------|
| `global_scanner.py` | Weekly trend scan (Google Trends, Reddit, YouTube Trending) |
| `ai_synthesizer.py` | Turns trends into video topics and product ideas |
| `video_producer.py` | Short video production (3–5 min) |
| `product_producer.py` | PDF lead magnet creation |
| `youtube_uploader.py` | Uploads video as private draft |
| `email_lead_magnet.py` | Adds Gumroad downloaders to Kit |
| n8n workflow 01 | Gumroad sale/download → Kit + Telegram |

---

## Step 1 — Configure Global Scanner

Edit `global_scanner.py` → `_default_keywords()`:

```python
def _default_keywords(self) -> List[str]:
    return [
        "your niche keyword 1",
        "your niche keyword 2",
        # Add 8–12 keywords relevant to your channel theme
    ]
```

Test the scanner manually:
```bash
docker compose exec app python3 -c "
import asyncio
from global_scanner import GlobalScanner
results = asyncio.run(GlobalScanner().run_weekly_scan())
print(f'Found {len(results)} trends')
for r in results[:3]:
    print(r['topic'], r['popularity'])
"
```

---

## Step 2 — Set Up Gumroad

1. Create account at [gumroad.com](https://gumroad.com)
2. Go to Settings → Advanced → Generate API key
3. Add to `.env`:
   ```
   GUMROAD_ACCESS_TOKEN=your_token_here
   ```
4. Configure Ping URL (for n8n):
   - Gumroad Settings → Advanced → Ping URL
   - Set to: `http://YOUR_SERVER_IP:5678/webhook/gumroad-sale`

---

## Step 3 — Set Up Kit (ConvertKit)

1. Create account at [kit.com](https://kit.com)
2. Settings → Advanced → API keys
3. Add to `.env`:
   ```
   KIT_API_KEY=your_key
   KIT_API_SECRET=your_secret
   ```
4. Test connection:
```bash
docker compose exec app python3 -c "
import asyncio
from convertkit_api import KitAPI
kit = KitAPI()
subs = kit.get_subscribers()
print(f'Kit connected — {len(subs)} subscribers')
"
```

---

## Step 4 — First Video Production (Manual Test)

Run your first video production end-to-end:

```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from global_scanner import GlobalScanner
from ai_synthesizer import AISynthesizer
from video_producer import VideoProducer

async def test():
    # 1. Get a trend
    trends = await GlobalScanner().run_weekly_scan()
    top_trend = trends[0]
    print(f"Top trend: {top_trend['topic']}")

    # 2. Synthesize video concept
    synth = AISynthesizer()
    script = await synth.synthesize_video_topic(
        trend=top_trend,
        channel_theme="wellness",
        job_id="TEST01"
    )
    print(f"Script title: {script.get('title')}")

    # 3. Produce video
    producer = VideoProducer()
    video_path = await producer.produce(
        job_id="TEST01",
        script=script,
        channel_id="channel_1",
        channel_theme="wellness",
        video_type="short"
    )
    print(f"Video: {video_path}")

asyncio.run(test())
EOF
```

---

## Step 5 — Add YouTube Channel

```
/add_channel WellnessChannel https://youtube.com/@yourchannel
```

The bot will guide you through the OAuth flow.  
Your refresh token will be **Fernet-encrypted** and stored in the `channels` Sheets tab.

---

## Step 6 — Upload First Draft

```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from youtube_uploader import YouTubeUploader

async def test():
    uploader = YouTubeUploader()
    video_id = await uploader.upload_draft(
        job_id="TEST01",
        video_path="/app/jobs/TEST01/TEST01_draft.mp4",
        metadata={
            "title": "Your Test Video Title",
            "description": "Test description",
            "tags": ["wellness", "meditation"],
            "thumbnail": "/app/jobs/TEST01/thumbnail.jpg"
        },
        channel_id="channel_1"
    )
    print(f"Draft uploaded: https://studio.youtube.com/video/{video_id}/edit")

asyncio.run(test())
EOF
```

---

## Step 7 — Activate Scheduler

The scheduler is already running. Verify with:
```bash
docker compose exec app python3 -c "
from apscheduler.schedulers.asyncio import AsyncIOScheduler
print('Scheduler jobs:')
# Jobs are configured in scheduler.py
print('  - pending_sync_replay: every 15 min')
print('  - github_backup: daily 02:00')
print('  - sheets_backup: Sunday 03:00')
print('  - weekly_trend_scan: Monday 09:00')
"
```

---

## Phase 1 Transition Checklist

- [ ] Weekly trend scan runs automatically on Mondays
- [ ] At least 1 video produced end-to-end
- [ ] Video appears as draft in YouTube Studio
- [ ] Gumroad account created with API key configured
- [ ] Kit account connected
- [ ] n8n workflow 01 imported and active
- [ ] **50+ email subscribers** ✓
- [ ] **10+ videos produced** ✓

---

**Next:** [Phase 2 — Complex Products & Long Format](02_PHASE2.md)
