# Phase 2.5 — Segmentation, Product Analysis & Style Learning

**Goal:** $500+/month, regular data flow  
**Timeline:** Weeks 11–15  
**Weekly time required:** 2–4 hours

---

## What Gets Activated

| Module | Role |
|--------|------|
| `segmentation_engine.py` | Segment subscribers: hot/warm/cold, remove cold leads |
| `product_analyzer.py` | Analyze competitor product URLs → PDF report |
| `ornek_ogrenme.py` | Learn your title/style preferences |
| `strategy_reporter.py` | Weekly PDF + Telegram summary |

---

## Step 1 — Run Segmentation

```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from segmentation_engine import SegmentationEngine

async def run():
    engine = SegmentationEngine()
    report = await engine.run()
    print(f"Total: {report['total']}")
    print(f"Hot (engaged): {report['hot']}")
    print(f"Warm: {report['warm']}")
    print(f"Cold (removed): {report['removed']}")

asyncio.run(run())
EOF
```

Schedule monthly in `scheduler.py`:
```python
scheduler.add_job(
    segmentation_engine.run,
    trigger=CronTrigger(day=1, hour=4, minute=0),
    id="monthly_segmentation",
)
```

---

## Step 2 — Analyze a Competitor Product

```bash
# Via Telegram
/product_analyze https://gumroad.com/l/some-product
```

Or directly:
```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from product_analyzer import ProductAnalyzer

async def run():
    analyzer = ProductAnalyzer()
    pdf = await analyzer.analyze(
        url="https://example.com/product-page",
        job_id="ANAL01"
    )
    print(f"Report: {pdf}")

asyncio.run(run())
EOF
```

**Important:** Amazon URLs are blocked from scraping. The analyzer will tell you to use PAAPI instead.

---

## Step 3 — Start Style Learning

After editing any AI-generated title or outline, record the edit:

```bash
docker compose exec app python3 - <<'EOF'
from ornek_ogrenme import OrnekOgrenme

learner = OrnekOgrenme()
learner.record_edit(
    job_id="VID042",
    original_title="5 Powerful Vagus Nerve Exercises for Instant Calm and Deep Relaxation",
    edited_title="5 Vagus Nerve Exercises for Instant Calm",
    original_outline=["intro", "exercise 1", "exercise 2", "exercise 3", "exercise 4", "exercise 5", "outro"],
    edited_outline=["hook", "exercise 1", "exercise 2", "exercise 3", "exercise 4", "exercise 5"]
)

hints = learner.get_style_hints()
print("Style hints:", hints)
EOF
```

After 5+ edits, `get_style_hints()` returns your preferences automatically.

---

## Step 4 — Weekly Strategy Reports

Reports start arriving every Sunday at 10:00 (Istanbul time).  
You'll receive:
- Telegram message with key metrics
- PDF report downloadable from jobs folder

---

## Phase 2.5 Checklist

- [ ] Segmentation run — cold leads cleaned
- [ ] At least 3 product URLs analyzed
- [ ] `style_profile.json` created with at least 5 edits recorded
- [ ] Weekly strategy reports arriving
- [ ] **$500+/month revenue** ✓

---

# Phase 3 — Real-Time Trends & Reports

**Goal:** $1,000+/month  
**Timeline:** Weeks 16–20

## What Gets Activated

- `global_scanner.py` → switches to hourly real-time mode
- `haftalik_gelisim.py` → weekly improvement recommendations
- `ad_producer.py` → ad copy concepts (manual publish only)

## Key Change: Real-Time Scanner

In `scheduler.py`, change the trend scan interval:
```python
# Replace weekly scan with hourly
scheduler.add_job(
    global_scanner.run_realtime_scan,
    trigger="interval",
    hours=1,
    id="realtime_trend_scan",
)
```

## Ad Copy Production (Concept Only)

```bash
docker compose exec app python3 - <<'EOF'
# ad_producer.py produces concept text + optional Stable Diffusion visual
# YOU publish manually in Google Ads or Meta Ads
# System has NO ad API connection
print("Ad producer: Phase 3 module — implement when reaching $1K/month")
EOF
```

**Google Ads Safety Note:** Use YouTube in-stream ads only for wellness content.  
Google Display, Discovery, and Search ads carry higher policy risk.

## Phase 3 Checklist

- [ ] Trend scan running hourly
- [ ] Weekly improvement reports arriving
- [ ] **$1,000+/month revenue** ✓

---

# Phase 4 — Shopify & Printify Analysis

**Goal:** $1,500+/month digital, 3,000+ email subscribers  
**Timeline:** Weeks 21–26

## Privacy Note

> The Shopify integration connects **only to your store** using **your API key**.  
> No other store is accessible. All calls are HTTPS server-to-server.  
> Outside parties cannot see this connection.

## Setup

1. Shopify Admin → Apps → Develop apps → Create app
2. Scopes: `read_products`, `read_inventory` (read-only only)
3. Install app → copy Admin API access token

```bash
# Add to .env
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_API_KEY=your_admin_api_token
```

4. Get Printify API key: app.printify.com → My Profile → Connections

```bash
PRINTIFY_API_KEY=your_printify_key
```

## Run Analysis

```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from shopify_analyzer import ShopifyAnalyzer

async def run():
    analyzer = ShopifyAnalyzer()
    report = await analyzer.analyze_and_report("SHOP01")
    print(f"Report: {report}")

asyncio.run(run())
EOF
```

## Phase 4 Checklist

- [ ] Shopify store open with first products uploaded manually
- [ ] shopify_analyzer connected (read-only)
- [ ] First product analysis report received
- [ ] **$1,500+/month digital revenue** ✓
- [ ] **3,000+ email subscribers** ✓

---

# Phase 5 — Full Automation & Strategy Engine

**Goal:** System runs with <1 hour/week of your time  
**Timeline:** Week 27+

## What Changes

- `strategy_engine.py` generates a weekly content calendar
- You approve the plan via Telegram (one button press)
- System executes the full week autonomously

## Activation

```bash
# strategy_engine.py generates:
# - Which topics to cover this week (per channel)
# - Which products to promote
# - Which email to send to which segment
# All presented to you via Telegram for one-tap approval
```

## Phase 5 Checklist

- [ ] All previous phases stable for 4+ weeks
- [ ] Strategy engine generating weekly plans
- [ ] Your weekly time under 1 hour ✓

---

**Back to:** [Setup Guide](00_SETUP.md)
