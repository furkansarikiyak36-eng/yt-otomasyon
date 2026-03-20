"""
test_tokens.py
──────────────
.env dosyasındaki tüm token ve API key'leri test eder.
YouTube hariç her servisi kontrol eder.

Kullanım:
    python test_tokens.py
    python test_tokens.py --service telegram
    python test_tokens.py --service sheets
"""
import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv

load_dotenv()

# Renk kodları
OK   = "\033[92m✅\033[0m"
FAIL = "\033[91m❌\033[0m"
WARN = "\033[93m⚠️ \033[0m"
INFO = "\033[94mℹ️ \033[0m"
SKIP = "\033[90m⏭  \033[0m"

results = []

def log(status, service, message):
    icons = {"ok": OK, "fail": FAIL, "warn": WARN, "info": INFO, "skip": SKIP}
    print(f"  {icons.get(status, '')} [{service}] {message}")
    results.append({"status": status, "service": service, "message": message})


# ════════════════════════════════════════════════════════════
# TELEGRAM
# ════════════════════════════════════════════════════════════
async def test_telegram():
    print("\n📱 TELEGRAM")
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token:
        log("fail", "Telegram", "TELEGRAM_BOT_TOKEN tanımlı değil")
        return
    if not chat_id:
        log("fail", "Telegram", "TELEGRAM_CHAT_ID tanımlı değil")
        return

    try:
        import requests
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10
        )
        data = r.json()
        if data.get("ok"):
            bot_name = data["result"]["username"]
            log("ok", "Telegram", f"Bot bağlı: @{bot_name}")
        else:
            log("fail", "Telegram", f"Token geçersiz: {data.get('description')}")
            return

        # Chat ID test
        r2 = requests.get(
            f"https://api.telegram.org/bot{token}/getChat",
            params={"chat_id": chat_id},
            timeout=10
        )
        if r2.json().get("ok"):
            log("ok", "Telegram", f"Chat ID geçerli: {chat_id}")
        else:
            log("warn", "Telegram", f"Chat ID doğrulanamadı — bota /start gönder")

    except Exception as e:
        log("fail", "Telegram", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# GOOGLE SHEETS
# ════════════════════════════════════════════════════════════
def test_sheets():
    print("\n📊 GOOGLE SHEETS")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/credentials.json")
    sheet_id   = os.getenv("GOOGLE_SHEETS_ID", "")

    if not os.path.exists(creds_path):
        log("fail", "Sheets", f"credentials.json bulunamadı: {creds_path}")
        return
    else:
        log("ok", "Sheets", f"credentials.json mevcut: {creds_path}")

    if not sheet_id:
        log("fail", "Sheets", "GOOGLE_SHEETS_ID tanımlı değil")
        return

    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_id)
        tabs = [ws.title for ws in spreadsheet.worksheets()]
        log("ok", "Sheets", f"Bağlantı başarılı: '{spreadsheet.title}'")
        log("ok", "Sheets", f"Mevcut tab'lar ({len(tabs)}): {', '.join(tabs[:5])}{'...' if len(tabs)>5 else ''}")

        if len(tabs) < 10:
            log("warn", "Sheets", f"Sadece {len(tabs)} tab var — setup_sheets.py çalıştırıldı mı?")
    except Exception as e:
        log("fail", "Sheets", f"Bağlantı hatası: {e}")
        if "PERMISSION_DENIED" in str(e):
            log("info", "Sheets", "Sheet'i service account email ile paylaş (Editor erişimi)")


# ════════════════════════════════════════════════════════════
# GITHUB
# ════════════════════════════════════════════════════════════
def test_github():
    print("\n🐙 GITHUB")
    token = os.getenv("GITHUB_TOKEN", "")
    repo  = os.getenv("GITHUB_REPO", "")

    if not token:
        log("fail", "GitHub", "GITHUB_TOKEN tanımlı değil")
        return
    if not repo:
        log("fail", "GitHub", "GITHUB_REPO tanımlı değil (format: username/repo-name)")
        return

    try:
        from github import Github
        g = Github(token)
        user = g.get_user()
        log("ok", "GitHub", f"Token geçerli — kullanıcı: {user.login}")

        try:
            r = g.get_repo(repo)
            log("ok", "GitHub", f"Repo erişimi var: {r.full_name}")
        except Exception:
            log("warn", "GitHub", f"Repo bulunamadı: {repo} — önce repo'yu oluştur")
    except Exception as e:
        log("fail", "GitHub", f"Token hatası: {e}")


# ════════════════════════════════════════════════════════════
# KIT (CONVERTKIT)
# ════════════════════════════════════════════════════════════
def test_kit():
    print("\n📧 KIT (ConvertKit)")
    api_key    = os.getenv("KIT_API_KEY", "")
    api_secret = os.getenv("KIT_API_SECRET", "")

    if not api_key:
        log("skip", "Kit", "KIT_API_KEY tanımlı değil — Faz 1'de gerekli")
        return

    try:
        import requests
        r = requests.get(
            "https://api.convertkit.com/v3/account",
            params={"api_secret": api_secret or api_key},
            timeout=10
        )
        data = r.json()
        if "name" in data:
            log("ok", "Kit", f"Bağlantı başarılı: {data.get('name')} ({data.get('primary_email_address')})")
            log("ok", "Kit", f"Plan: {data.get('plan_type','unknown')}")
        else:
            log("fail", "Kit", f"API hatası: {data}")
    except Exception as e:
        log("fail", "Kit", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# GUMROAD
# ════════════════════════════════════════════════════════════
def test_gumroad():
    print("\n🛒 GUMROAD")
    token = os.getenv("GUMROAD_ACCESS_TOKEN", "")

    if not token:
        log("skip", "Gumroad", "GUMROAD_ACCESS_TOKEN tanımlı değil — Faz 1'de gerekli")
        return

    try:
        import requests
        r = requests.get(
            "https://api.gumroad.com/v2/user",
            params={"access_token": token},
            timeout=10
        )
        data = r.json()
        if data.get("success"):
            user = data.get("user", {})
            log("ok", "Gumroad", f"Bağlantı başarılı: {user.get('name')} ({user.get('email')})")
        else:
            log("fail", "Gumroad", f"Token geçersiz: {data.get('message')}")
    except Exception as e:
        log("fail", "Gumroad", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# PEXELS
# ════════════════════════════════════════════════════════════
def test_pexels():
    print("\n📸 PEXELS")
    key = os.getenv("PEXELS_API_KEY", "")

    if not key:
        log("skip", "Pexels", "PEXELS_API_KEY tanımlı değil — video görselleri için gerekli")
        return

    try:
        import requests
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": key},
            params={"query": "nature", "per_page": 1},
            timeout=10
        )
        if r.status_code == 200:
            log("ok", "Pexels", "API key geçerli")
        elif r.status_code == 401:
            log("fail", "Pexels", "API key geçersiz")
        else:
            log("warn", "Pexels", f"HTTP {r.status_code}")
    except Exception as e:
        log("fail", "Pexels", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# FREESOUND
# ════════════════════════════════════════════════════════════
def test_freesound():
    print("\n🎵 FREESOUND")
    key = os.getenv("FREESOUND_API_KEY", "")

    if not key:
        log("skip", "Freesound", "FREESOUND_API_KEY tanımlı değil — Ambiance kanalı için gerekli")
        return

    try:
        import requests
        r = requests.get(
            "https://freesound.org/apiv2/search/text/",
            params={"query": "ambient", "token": key, "page_size": 1},
            timeout=10
        )
        if r.status_code == 200:
            count = r.json().get("count", 0)
            log("ok", "Freesound", f"API key geçerli — {count} ses bulundu")
        elif r.status_code == 401:
            log("fail", "Freesound", "API key geçersiz")
        else:
            log("warn", "Freesound", f"HTTP {r.status_code}")
    except Exception as e:
        log("fail", "Freesound", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# OPENROUTER
# ════════════════════════════════════════════════════════════
def test_openrouter():
    print("\n🤖 OPENROUTER")
    key   = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

    if not key:
        log("skip", "OpenRouter", "OPENROUTER_API_KEY tanımlı değil — opsiyonel")
        return

    try:
        import requests
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":    model,
                "messages": [{"role": "user", "content": "Say OK in one word."}],
                "max_tokens": 5,
            },
            timeout=20
        )
        if r.status_code == 200:
            reply = r.json()["choices"][0]["message"]["content"].strip()
            log("ok", "OpenRouter", f"API key geçerli — model: {model}")
            log("ok", "OpenRouter", f"Test yanıtı: {reply}")
        elif r.status_code == 401:
            log("fail", "OpenRouter", "API key geçersiz")
        elif r.status_code == 402:
            log("warn", "OpenRouter", "Kredi yetersiz — ücretsiz model seç")
        else:
            log("warn", "OpenRouter", f"HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        log("fail", "OpenRouter", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# GEMINI (opsiyonel)
# ════════════════════════════════════════════════════════════
def test_gemini():
    print("\n✨ GEMINI (opsiyonel)")
    key = os.getenv("GEMINI_API_KEY", "")

    if not key:
        log("skip", "Gemini", "Tanımlı değil — Ollama varsayılan, bu opsiyonel")
        return

    try:
        import requests
        r = requests.get(
            f"https://generativelanguage.googleapis.com/v1/models?key={key}",
            timeout=10
        )
        if r.status_code == 200:
            log("ok", "Gemini", "API key geçerli")
        elif r.status_code == 400:
            log("fail", "Gemini", "API key geçersiz")
        else:
            log("warn", "Gemini", f"HTTP {r.status_code}")
    except Exception as e:
        log("fail", "Gemini", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# FERNET KEY
# ════════════════════════════════════════════════════════════
def test_fernet():
    print("\n🔐 FERNET KEY")
    key = os.getenv("FERNET_KEY", "")

    if not key:
        log("fail", "Fernet", "FERNET_KEY tanımlı değil — YouTube token şifrelemesi için zorunlu")
        log("info", "Fernet", "Üretmek için: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        return

    try:
        from cryptography.fernet import Fernet, InvalidToken
        f = Fernet(key.encode())
        # Şifrele + çöz testi
        test_data = b"mindfully_brand_test"
        encrypted = f.encrypt(test_data)
        decrypted = f.decrypt(encrypted)
        if decrypted == test_data:
            log("ok", "Fernet", f"Key geçerli — şifreleme/çözme çalışıyor")
            log("ok", "Fernet", f"Key uzunluğu: {len(key)} karakter")
        else:
            log("fail", "Fernet", "Şifreleme/çözme tutarsız")
    except Exception as e:
        log("fail", "Fernet", f"Geçersiz key: {e}")


# ════════════════════════════════════════════════════════════
# SENTRY (opsiyonel)
# ════════════════════════════════════════════════════════════
def test_sentry():
    print("\n🚨 SENTRY (opsiyonel)")
    dsn = os.getenv("SENTRY_DSN", "")

    if not dsn:
        log("skip", "Sentry", "Tanımlı değil — hata takibi için opsiyonel")
        return

    if dsn.startswith("https://") and "@sentry.io" in dsn:
        log("ok", "Sentry", "DSN formatı geçerli")
    else:
        log("warn", "Sentry", "DSN formatı beklenmedik — kontrol et")


# ════════════════════════════════════════════════════════════
# SHOPIFY (Faz 4 — opsiyonel)
# ════════════════════════════════════════════════════════════
def test_shopify():
    print("\n🛍️  SHOPIFY (Faz 4 — opsiyonel)")
    url = os.getenv("SHOPIFY_STORE_URL", "")
    key = os.getenv("SHOPIFY_API_KEY", "")

    if not url or not key:
        log("skip", "Shopify", "Tanımlı değil — Faz 4'te gerekli")
        return

    try:
        import requests
        r = requests.get(
            f"https://{url}/admin/api/2024-01/products.json?limit=1",
            headers={"X-Shopify-Access-Token": key},
            timeout=10
        )
        if r.status_code == 200:
            count = len(r.json().get("products", []))
            log("ok", "Shopify", f"Bağlantı başarılı — {count} ürün döndü")
        elif r.status_code == 401:
            log("fail", "Shopify", "API key geçersiz veya yetkisi yok")
        elif r.status_code == 404:
            log("fail", "Shopify", f"Store URL yanlış: {url}")
        else:
            log("warn", "Shopify", f"HTTP {r.status_code}")
    except Exception as e:
        log("fail", "Shopify", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# INSTAGRAM (opsiyonel)
# ════════════════════════════════════════════════════════════
def test_instagram():
    print("\n📸 INSTAGRAM (opsiyonel)")
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    biz_id = os.getenv("INSTAGRAM_BUSINESS_ID", "")

    if not token:
        log("skip", "Instagram", "Tanımlı değil — Faz 2'de gerekli")
        return

    try:
        import requests
        r = requests.get(
            f"https://graph.facebook.com/v18.0/me",
            params={"access_token": token, "fields": "id,name"},
            timeout=10
        )
        data = r.json()
        if "id" in data:
            log("ok", "Instagram", f"Token geçerli: {data.get('name','')}")
            if not biz_id:
                log("warn", "Instagram", "INSTAGRAM_BUSINESS_ID tanımlı değil")
        elif "error" in data:
            log("fail", "Instagram", f"{data['error'].get('message','')}")
    except Exception as e:
        log("fail", "Instagram", f"Bağlantı hatası: {e}")


# ════════════════════════════════════════════════════════════
# ÖZET
# ════════════════════════════════════════════════════════════
def print_summary():
    print("\n" + "="*50)
    print("ÖZET")
    print("="*50)

    ok_count   = sum(1 for r in results if r["status"] == "ok")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    warn_count = sum(1 for r in results if r["status"] == "warn")
    skip_count = sum(1 for r in results if r["status"] == "skip")

    print(f"  {OK} Başarılı : {ok_count}")
    print(f"  {FAIL} Başarısız: {fail_count}")
    print(f"  {WARN} Uyarı    : {warn_count}")
    print(f"  {SKIP} Atlandı  : {skip_count}")

    if fail_count > 0:
        print(f"\n❌ Başarısız servisler:")
        for r in results:
            if r["status"] == "fail":
                print(f"   • [{r['service']}] {r['message']}")

    if warn_count > 0:
        print(f"\n⚠️  Uyarılar:")
        for r in results:
            if r["status"] == "warn":
                print(f"   • [{r['service']}] {r['message']}")

    if fail_count == 0:
        print(f"\n🎉 Tüm zorunlu servisler çalışıyor!")
    else:
        print(f"\n⚠️  {fail_count} servis düzeltilmeli.")

    print()


# ════════════════════════════════════════════════════════════
# ANA
# ════════════════════════════════════════════════════════════
async def main():
    parser = argparse.ArgumentParser(description="Token test aracı")
    parser.add_argument("--service", help="Sadece belirli servisi test et", default="all")
    args = parser.parse_args()

    print("\n" + "="*50)
    print("  MINDFULLY BRAND — Token Test Aracı")
    print("="*50)

    service = args.service.lower()

    test_map = {
        "telegram":   lambda: asyncio.create_task(test_telegram()),
        "sheets":     test_sheets,
        "github":     test_github,
        "kit":        test_kit,
        "gumroad":    test_gumroad,
        "pexels":     test_pexels,
        "freesound":  test_freesound,
        "openrouter": test_openrouter,
        "gemini":     test_gemini,
        "fernet":     test_fernet,
        "sentry":     test_sentry,
        "shopify":    test_shopify,
        "instagram":  test_instagram,
    }

    if service != "all" and service in test_map:
        fn = test_map[service]
        if asyncio.iscoroutinefunction(fn):
            await fn()
        else:
            fn()
    else:
        # Hepsini çalıştır
        await test_telegram()
        test_sheets()
        test_github()
        test_kit()
        test_gumroad()
        test_pexels()
        test_freesound()
        test_openrouter()
        test_gemini()
        test_fernet()
        test_sentry()
        test_shopify()
        test_instagram()

    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
