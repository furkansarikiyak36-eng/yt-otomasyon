# Shopify Integration — Privacy & Setup

## Can an Outside Party See My Shopify Data?

**No.** Here is the complete technical explanation:

| What | Visible to outsiders? | Why |
|------|----------------------|-----|
| Your product catalog | ❌ No | Admin API key is private, server-to-server HTTPS |
| Your orders | ❌ No | Read-only scope excludes orders entirely |
| Your customer data | ❌ No | Not requested, not stored |
| That you use this system | ❌ No | Looks like normal API calls from your account |
| Public product pages scraped | ✅ Yes* | *These are already public — any browser can see them |

### Technical Guarantees

- **API Key Isolation:** Shopify Admin API keys are per-store. Your key can only access your store.
- **Read-Only Scope:** Key is configured for `read_products` + `read_inventory` only. Cannot place orders, change prices, or access customer PII.
- **Server-Side Only:** All calls happen on your Hetzner server. No browser extensions, no third-party services.
- **HTTPS Encryption:** All API calls use TLS — encrypted in transit.
- **No Data Sharing:** Data stays on your server and in your Google Sheets.
- **Webhook HMAC:** Shopify webhooks include a signature that n8n verifies — prevents fake webhook injection.

---

## Setup (Phase 4)

### Step 1 — Create Shopify API App

1. Shopify Admin → Settings → Apps and sales channels
2. Click **Develop apps** → **Create an app**
3. App name: `yt-otomasyon-analyzer`
4. Click **Configure Admin API scopes**
5. Enable ONLY:
   - ✅ `read_products`
   - ✅ `read_inventory`
   - ❌ Everything else OFF
6. Click **Save** → **Install app**
7. Copy the **Admin API access token**

### Step 2 — Add to `.env`

```
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_API_KEY=shpat_xxxxxxxxxxxxx
```

### Step 3 — Test Connection

```bash
docker compose exec app python3 - <<'EOF'
from shopify_analyzer import ShopifyAnalyzer

analyzer = ShopifyAnalyzer()
products = analyzer.get_products(limit=5)
print(f"Connected — {len(products)} products found")
for p in products:
    print(f"  - {p['title']}")
EOF
```

### Step 4 — Get Product Analysis Report

Via Telegram: the system will offer analysis when Phase 4 is active.  
Or manually:
```bash
docker compose exec app python3 - <<'EOF'
import asyncio
from shopify_analyzer import ShopifyAnalyzer

async def run():
    analyzer = ShopifyAnalyzer()
    report_path = await analyzer.analyze_and_report("SHOP01")
    print(f"Report: {report_path}")

asyncio.run(run())
EOF
```

---

## What the Report Shows

- Your products ranked by trend alignment score (0–100)
- Trend score = how well the product matches current Google Trends + Reddit data
- Recommendations: which products to promote this week based on rising trends

---

## What the System NEVER Does with Shopify

- ❌ Upload new products
- ❌ Change prices
- ❌ Manage inventory
- ❌ Access or store order data
- ❌ Access customer names, emails, or addresses
- ❌ Connect to any store other than yours
