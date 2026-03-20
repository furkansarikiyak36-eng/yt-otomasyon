cat > /root/yt-otomasyon/test_tokens.py << 'HEREDOC'
import os, asyncio
from dotenv import load_dotenv
load_dotenv()

OK="\033[92m✅\033[0m"; FAIL="\033[91m❌\033[0m"; WARN="\033[93m⚠️ \033[0m"; SKIP="\033[90m⏭  \033[0m"

def log(s,svc,msg):
    icons={"ok":OK,"fail":FAIL,"warn":WARN,"skip":SKIP}
    print(f"  {icons.get(s,'')} [{svc}] {msg}")

def test_fernet():
    print("\n🔐 FERNET KEY")
    key=os.getenv("FERNET_KEY","")
    if not key: return log("fail","Fernet","FERNET_KEY tanımlı değil")
    try:
        from cryptography.fernet import Fernet
        f=Fernet(key.encode()); d=f.decrypt(f.encrypt(b"test"))
        log("ok","Fernet",f"Geçerli — {len(key)} karakter")
    except Exception as e: log("fail","Fernet",str(e))

def test_sheets():
    print("\n📊 GOOGLE SHEETS")
    creds=os.getenv("GOOGLE_APPLICATION_CREDENTIALS","credentials.json")
    sid=os.getenv("GOOGLE_SHEETS_ID","")
    # Docker dışında çalışıyoruz — local path'e bak
    local=creds.replace("/app/","./")
    path=local if os.path.exists(local) else creds
    if not os.path.exists(path): return log("fail","Sheets",f"credentials.json yok: {path}")
    log("ok","Sheets",f"credentials.json mevcut")
    if not sid: return log("fail","Sheets","GOOGLE_SHEETS_ID eksik")
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        crd=Credentials.from_service_account_file(path,scopes=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"])
        gc=gspread.authorize(crd); sp=gc.open_by_key(sid)
        tabs=[w.title for w in sp.worksheets()]
        log("ok","Sheets",f"Bağlandı: '{sp.title}' — {len(tabs)} tab")
    except Exception as e:
        log("fail","Sheets",str(e))
        if "PERMISSION_DENIED" in str(e): log("warn","Sheets","Sheet'i service account email ile paylaş (Editor)")

async def test_telegram():
    print("\n📱 TELEGRAM")
    token=os.getenv("TELEGRAM_BOT_TOKEN",""); chat=os.getenv("TELEGRAM_CHAT_ID","")
    if not token: return log("fail","Telegram","TELEGRAM_BOT_TOKEN eksik")
    try:
        import requests
        r=requests.get(f"https://api.telegram.org/bot{token}/getMe",timeout=10).json()
        if r.get("ok"): log("ok","Telegram",f"Bot: @{r['result']['username']}")
        else: log("fail","Telegram",r.get("description",""))
        if chat:
            r2=requests.get(f"https://api.telegram.org/bot{token}/getChat",params={"chat_id":chat},timeout=10).json()
            log("ok" if r2.get("ok") else "warn","Telegram",f"Chat ID {'geçerli' if r2.get('ok') else 'doğrulanamadı — bota /start gönder'}")
    except Exception as e: log("fail","Telegram",str(e))

def test_github():
    print("\n🐙 GITHUB")
    token=os.getenv("GITHUB_TOKEN",""); repo=os.getenv("GITHUB_REPO","")
    if not token: return log("skip","GitHub","GITHUB_TOKEN eksik")
    try:
        from github import Github
        g=Github(token); u=g.get_user()
        log("ok","GitHub",f"Kullanıcı: {u.login}")
        try: r=g.get_repo(repo); log("ok","GitHub",f"Repo: {r.full_name}")
        except: log("warn","GitHub",f"Repo bulunamadı: {repo} — önce oluştur")
    except Exception as e: log("fail","GitHub",str(e))

def test_openrouter():
    print("\n🤖 OPENROUTER")
    key=os.getenv("OPENROUTER_API_KEY","")
    model=os.getenv("OPENROUTER_MODEL","meta-llama/llama-3.1-8b-instruct:free")
    if not key: return log("skip","OpenRouter","OPENROUTER_API_KEY eksik — opsiyonel")
    try:
        import requests
        r=requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
            json={"model":model,"messages":[{"role":"user","content":"Say OK"}],"max_tokens":5},timeout=20)
        if r.status_code==200: log("ok","OpenRouter",f"Geçerli — model: {model}")
        elif r.status_code==401: log("fail","OpenRouter","API key geçersiz")
        else: log("warn","OpenRouter",f"HTTP {r.status_code}: {r.text[:80]}")
    except Exception as e: log("fail","OpenRouter",str(e))

def test_pexels():
    print("\n📸 PEXELS")
    key=os.getenv("PEXELS_API_KEY","")
    if not key: return log("skip","Pexels","Eksik — video görselleri için gerekli")
    try:
        import requests
        r=requests.get("https://api.pexels.com/v1/search",headers={"Authorization":key},params={"query":"nature","per_page":1},timeout=10)
        log("ok" if r.status_code==200 else "fail","Pexels","Geçerli" if r.status_code==200 else f"HTTP {r.status_code}")
    except Exception as e: log("fail","Pexels",str(e))

def test_freesound():
    print("\n🎵 FREESOUND")
    key=os.getenv("FREESOUND_API_KEY","")
    if not key: return log("skip","Freesound","Eksik — Ambiance kanalı için gerekli")
    try:
        import requests
        r=requests.get("https://freesound.org/apiv2/search/text/",params={"query":"ambient","token":key,"page_size":1},timeout=10)
        log("ok" if r.status_code==200 else "fail","Freesound","Geçerli" if r.status_code==200 else f"HTTP {r.status_code}")
    except Exception as e: log("fail","Freesound",str(e))

def test_kit():
    print("\n📧 KIT")
    key=os.getenv("KIT_API_KEY",""); secret=os.getenv("KIT_API_SECRET","")
    if not key: return log("skip","Kit","Eksik — Faz 1'de gerekli")
    try:
        import requests
        r=requests.get("https://api.convertkit.com/v3/account",params={"api_secret":secret or key},timeout=10).json()
        log("ok" if "name" in r else "fail","Kit",r.get("name","Hata: "+str(r)))
    except Exception as e: log("fail","Kit",str(e))

def test_gumroad():
    print("\n🛒 GUMROAD")
    token=os.getenv("GUMROAD_ACCESS_TOKEN","")
    if not token: return log("skip","Gumroad","Eksik — Faz 1'de gerekli")
    try:
        import requests
        r=requests.get("https://api.gumroad.com/v2/user",params={"access_token":token},timeout=10).json()
        log("ok" if r.get("success") else "fail","Gumroad",r.get("user",{}).get("name","Hata"))
    except Exception as e: log("fail","Gumroad",str(e))

async def main():
    print("\n"+"="*50)
    print("  MINDFULLY BRAND — Token Testi")
    print("="*50)
    await test_telegram()
    test_sheets()
    test_github()
    test_fernet()
    test_openrouter()
    test_pexels()
    test_freesound()
    test_kit()
    test_gumroad()
    print("\n✅ Test tamamlandı\n")

asyncio.run(main())
HEREDOC
