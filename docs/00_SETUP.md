# Phase 0 — Setup Guide

Complete step-by-step instructions to get the system running from scratch.

---

## Prerequisites

- A **Hetzner account** (hetzner.com)
- A **Google account** (for Sheets + YouTube API)
- A **GitHub account**
- A **Telegram account**
- Basic SSH knowledge

---

## Step 1 — Rent Hetzner Server

1. Go to [hetzner.com/cloud](https://hetzner.com/cloud)
2. Create project → Add Server
3. Select: **CX23** (4 GB RAM, 2 vCPU, 40 GB SSD — €6/mo)
4. OS: **Ubuntu 22.04**
5. Add your SSH key
6. Note the server IP address

---

## Step 2 — Connect & Install Docker

```bash
ssh root@YOUR_SERVER_IP

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
apt-get install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

---

## Step 3 — Google Cloud Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project: `yt-otomasyon`
3. Enable APIs:
   - Google Sheets API
   - Google Drive API
   - YouTube Data API v3
4. Go to **IAM & Admin → Service Accounts**
5. Create service account: `yt-bot@yt-otomasyon.iam.gserviceaccount.com`
6. Download JSON key → rename to `credentials.json`
7. Upload to server: `scp credentials.json root@YOUR_SERVER_IP:/root/yt-otomasyon/`
8. ✅ Sheet already created: [MINDFULLY BRAND](https://docs.google.com/spreadsheets/d/1OoxhsKaWSPLKaIs0O4klzIjHdwZQoQ7fLidkFkNS2Kg)
Sheet ID: `1OoxhsKaWSPLKaIs0O4klzIjHdwZQoQ7fLidkFkNS2Kg`
**Skip this step** — just share it with the service account email

---

## Step 4 — Telegram Bot

1. Open Telegram → search `@BotFather`
2. Send `/newbot`
3. Follow prompts, note the **Bot Token**
4. Get your Chat ID:
   - Start your bot
   - Visit: `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
   - Note the `chat.id` value

---

## Step 5 — GitHub Repository

```bash
# On your local machine or server
git init yt-otomasyon
cd yt-otomasyon
git remote add origin https://github.com/YOUR_USERNAME/yt-otomasyon.git
```

Generate a GitHub Personal Access Token:
1. GitHub → Settings → Developer settings → Personal access tokens
2. Scopes: `repo` (full)
3. Note the token

---

## Step 6 — Generate Fernet Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Save this key — it encrypts your YouTube OAuth tokens.

---

## Step 7 — Configure Environment

```bash
cd /root/yt-otomasyon
cp .env.example .env
nano .env
```

Fill in at minimum:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
GOOGLE_SHEETS_ID=...
FERNET_KEY=...
GITHUB_TOKEN=...
GITHUB_REPO=YOUR_USERNAME/yt-otomasyon
SENTRY_DSN=...   # optional but recommended
```

---

## Step 8 — Build & Start

```bash
cd /root/yt-otomasyon
docker compose up -d --build

# Check logs
docker compose logs -f app
docker compose logs -f n8n
```

Expected output:
```
✅ System started successfully
All services running. Send /start to interact.
```

---

## Step 9 — Test Sheets Connection

```bash
docker compose exec app python3 -c "
from sheets_manager import SheetsManager
sm = SheetsManager()
sm.append_row('test', {'hello': 'world'})
print('Sheets connection: OK')
"
```

---

## Step 10 — Run Tests

```bash
docker compose exec app pip install pytest pytest-asyncio
docker compose exec app pytest tests/ -v
```

All tests should pass before proceeding to Phase 1.

---

## Step 11 — n8n Setup

1. Open browser: `http://YOUR_SERVER_IP:5678`
2. Create admin account
3. Import workflows from `n8n_workflows/`:
   - Settings → Import from file
   - Import `01_gumroad_sale.json`
   - Import `02_youtube_metrics.json`
4. Set environment variables in n8n:
   - Settings → Variables
   - Add: `KIT_API_SECRET`, `TELEGRAM_CHAT_ID`, `YOUTUBE_API_KEY`

---

## Verification Checklist

- [ ] Server running, SSH accessible
- [ ] `docker compose ps` shows `app` and `n8n` as Up
- [ ] Sheets connection test passes
- [ ] Telegram bot responds to `/start`
- [ ] All pytest tests pass
- [ ] n8n accessible at port 5678
- [ ] GitHub backup pushed at least once (run: `docker compose exec app python github_backup.py`)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container won't start | Check `docker compose logs app` for missing env vars |
| Sheets connection fails | Verify credentials.json is mounted and Sheet ID is correct |
| Telegram bot silent | Verify BOT_TOKEN and CHAT_ID are correct |
| n8n not accessible | Check firewall: `ufw allow 5678` |
| RAM issues | Check `docker stats` — if over 3.5GB, restart container |

---

**Next:** [Phase 1 — Trend Scanning & First Videos](01_PHASE1.md)
