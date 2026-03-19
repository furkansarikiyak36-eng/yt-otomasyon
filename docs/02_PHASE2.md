# Phase 2 — Complex Products & Long Format

**Goal:** $200+/month revenue, 500+ email subscribers.  
**Timeline:** Weeks 6–10  
**Weekly time required:** 3–5 hours

---

## What Gets Activated in Phase 2

| Module | Role |
|--------|------|
| `video_producer.py` | Complex videos (10–20 min) |
| `ambiance_video_producer.py` | Ambient/loop videos (30–60 min) |
| `documentary_producer.py` | Story-driven documentaries |
| `product_producer.py` | Paid PDF products ($19+) |
| `social_producer.py` | Shorts for Instagram/TikTok/Pinterest |
| `email_strategy.py` | Post-purchase email sequences |
| n8n workflow 02 | YouTube 48h performance tracker |

---

## Step 1 — Install Ollama on Server

Ollama runs inside the Docker container but needs models downloaded:

```bash
docker compose exec app bash -c "
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull lightweight models (fits in 4GB RAM)
ollama pull qwen2.5:3b
ollama pull llama3.2:1b

# Test
ollama run qwen2.5:3b 'Say hello in one sentence'
"
```

---

## Step 2 — Install Kokoro TTS

```bash
# Run Kokoro as a separate Docker service
docker run -d \
  --name kokoro-tts \
  -p 8880:8880 \
  --restart always \
  ghcr.io/remsky/kokoro-fastapi-cpu:latest

# Test
curl -X POST http://localhost:8880/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test.", "voice": "af_sky"}' \
  --output test_audio.mp3
```

---

## Step 3 — Produce First Paid PDF Product

```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from ai_synthesizer import AISynthesizer
from product_producer import ProductProducer

async def test():
    synth = AISynthesizer()
    concept = await synth.synthesize_product_idea(
        trend={"topic": "vagus nerve exercises", "popularity": 78},
        product_type="PDF guide",
        job_id="PROD01"
    )
    print("Concept:", concept.get("title"))

    producer = ProductProducer()
    pdf_path = await producer.produce_pdf(
        job_id="PROD01",
        product_concept=concept,
        out_dir="/app/jobs/PROD01"
    )
    print(f"PDF: {pdf_path}")

    # Upload as Gumroad draft
    url = await producer.upload_to_gumroad_draft(
        pdf_path=pdf_path,
        concept=concept,
        price_cents=1900  # $19
    )
    print(f"Gumroad draft: {url}")

asyncio.run(test())
EOF
```

---

## Step 4 — Set Up Post-Purchase Email Sequence

In Kit (ConvertKit):
1. Create a new **Sequence** named "Post-Purchase: [Product Name]"
2. Email 1 (Day 0): Thank you + download link
3. Email 2 (Day 3): First tip from the product
4. Email 3 (Day 7): Related content / upsell

In n8n workflow 01, the buyer tag (`buyer_[product]`) triggers this sequence automatically.

---

## Step 5 — Import n8n YouTube Metrics Workflow

1. n8n UI → Import from file
2. Import `n8n_workflows/02_youtube_metrics.json`
3. Set env vars in n8n: `YOUTUBE_API_KEY`, `TELEGRAM_CHAT_ID`
4. Activate the workflow

Now after every upload, you'll get a Telegram alert if a video performs under 200 views at 48h.

---

## Step 6 — Connect Social Media

Add to `.env`:
```
INSTAGRAM_ACCESS_TOKEN=...
TIKTOK_ACCESS_TOKEN=...
PINTEREST_ACCESS_TOKEN=...
```

Test Instagram posting:
```bash
docker compose exec app python3 -c "
# social_media_publisher.py integration test
print('Social media publisher: Phase 2 activation pending')
print('Configure tokens in .env first')
"
```

---

## Phase 2 Transition Checklist

- [ ] Ollama running with qwen2.5:3b model
- [ ] Kokoro TTS running on port 8880
- [ ] First paid PDF product on Gumroad (draft)
- [ ] Post-purchase email sequence set up in Kit
- [ ] n8n workflow 02 imported and active
- [ ] YouTube 48h alerts arriving via Telegram
- [ ] **$200+/month revenue** ✓
- [ ] **500+ email subscribers** ✓

---

**Next:** [Phase 2.5 — Segmentation & Analysis](03_PHASE2_5.md)
