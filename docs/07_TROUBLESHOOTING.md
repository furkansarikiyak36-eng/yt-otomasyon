# Troubleshooting Guide

---

## Container Issues

### Container won't start
```bash
docker compose logs app
```
Most common causes:
- Missing `.env` variable → add it, restart: `docker compose restart app`
- `credentials.json` not found → verify volume mount in `docker-compose.yml`
- Port 5000 in use → `lsof -i :5000` then kill the process

### Container keeps restarting
```bash
docker compose logs app --tail=50
```
Look for the last error before `Restarting`.  
Common: Sentry DSN invalid, Sheets credentials expired.

### RAM issues
```bash
docker stats
```
If app container exceeds 3.5 GB:
- `queue_manager.py` should prevent this
- If it happens: `docker compose restart app`
- Long-term: upgrade to CX33

---

## Google Sheets Issues

### `APIError: [429]` — Rate limited
System handles this automatically with `pending_sync`.  
Check pending entries:
```bash
docker compose exec app python3 -c "
import sqlite3
conn = sqlite3.connect('/app/yt-otomasyon.sqlite')
rows = conn.execute('SELECT * FROM pending_sync').fetchall()
print(f'Pending sync entries: {len(rows)}')
for r in rows:
    print(r)
"
```
These replay automatically every 15 minutes.

### Sheets tab missing
The system auto-creates missing tabs. If it fails:
1. Manually create the tab in Google Sheets with the expected name
2. Restart the container

### `credentials.json` expired
Service account credentials don't expire. If you see auth errors:
1. Go to Google Cloud Console → Service Accounts
2. Re-download the JSON key
3. Replace `/root/yt-otomasyon/credentials.json`
4. `docker compose restart app`

---

## Telegram Issues

### Bot not responding
1. Verify `TELEGRAM_BOT_TOKEN` in `.env`
2. Check bot is started: send `/start` to the bot
3. Check `TELEGRAM_CHAT_ID` matches your chat

### Getting `CHAT_ID`:
```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates" | python3 -m json.tool | grep '"id"'
```

---

## YouTube Issues

### Upload fails with auth error
Refresh token may have expired. Re-add the channel:
```
/add_channel ChannelName https://youtube.com/@channel
```
This triggers a new OAuth flow and saves fresh encrypted token.

### YouTube API quota exceeded (10,000 units/day)
- Uploading 1 video costs 1,600 units
- Max 6 uploads/day total (recommended: 2/day/channel)
- System tracks daily count — waits until midnight PT to retry
- Check in Sheets → `video_log` for today's upload count

---

## Ollama Issues

### Ollama not responding
```bash
docker compose exec app curl http://localhost:11434/api/tags
```
If not running:
```bash
docker compose exec app ollama serve &
docker compose exec app ollama pull qwen2.5:3b
```

### Ollama too slow
- `qwen2.5:3b` is the recommended lightweight model for 4GB RAM
- Avoid `llama3.2:8b` or larger on CX23
- Check if FFmpeg is running simultaneously (`docker stats`) — it may be competing for CPU

---

## Kokoro TTS Issues

### Port 8880 not responding
```bash
docker ps | grep kokoro
docker restart kokoro-tts
```

### Audio quality poor
Try different voice:
```bash
curl -X POST http://localhost:8880/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test", "voice": "en_us_001"}' \
  --output test.mp3
```
Available voices: `af_sky`, `en_us_001`, `en_us_002`

---

## n8n Issues

### Workflow not triggering
1. Check n8n is running: `http://YOUR_SERVER:5678`
2. Verify workflow is **Active** (toggle in n8n UI)
3. Check webhook URL is correctly set in Gumroad/Shopify
4. Test manually: n8n UI → workflow → Execute Workflow

### n8n lost all workflows
Workflows are backed up to GitHub daily.  
Restore:
```bash
# Download from GitHub
git clone https://github.com/YOUR_USERNAME/yt-otomasyon.git /tmp/restore
# Import each JSON file in n8n UI
```

---

## FFmpeg Issues

### Video assembly hangs
FFmpeg has a 600s timeout. If it times out:
- Check visual files are valid: `ffprobe /app/jobs/JOB_ID/visual_0.mp4`
- Reduce number of visuals (try `count=3` in `_fetch_visuals`)
- Check disk space: `df -h`

### No audio in output video
Verify Kokoro/Edge-TTS generated the audio file:
```bash
ls -la /app/jobs/JOB_ID/*.mp3
```

---

## Scraping Issues

### 403 Forbidden
Site blocked the request. System stops immediately (doesn't retry).  
Try again tomorrow with a different user-agent (handled automatically next run).

### Amazon URL blocked
Expected behavior. Never scrape Amazon — use PAAPI instead.  
Message: `"Amazon URL detected — use PAAPI instead of scraping"`

---

## Common Commands

```bash
# View all container logs
docker compose logs -f

# Restart specific service
docker compose restart app

# Enter app container
docker compose exec app bash

# Run tests
docker compose exec app pytest tests/ -v

# Manual backup
docker compose exec app python3 github_backup.py

# Check SQLite pending sync
docker compose exec app python3 -c "
import sqlite3
c = sqlite3.connect('/app/yt-otomasyon.sqlite')
print('pending_sync:', c.execute('SELECT COUNT(*) FROM pending_sync').fetchone()[0])
print('cache entries:', c.execute('SELECT COUNT(*) FROM cache').fetchone()[0])
"

# Force replay pending sync
docker compose exec app python3 -c "
from sheets_manager import SheetsManager
SheetsManager().replay_pending_sync()
print('Replay complete')
"
```
