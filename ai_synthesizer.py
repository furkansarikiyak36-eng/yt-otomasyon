"""
ai_synthesizer.py — Phase 1/2
───────────────────────────────
Synthesizes trend data into video topics, product ideas, and edits.

NEW in v2:
  - synthesize_variations()   : 3 farklı varyasyon üretir
  - apply_edit_instruction()  : "şunu değiştir" komutunu uygular
  - analyze_reference_image() : resim/video referansından stil çıkarır
"""
import json
import base64
import requests
from typing import Optional, Dict, List

from config import Config
from utils.logger import get_logger

log = get_logger("ai_synthesizer")

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_CHAT  = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:3b"


class AISynthesizer:
    def __init__(self, telegram_handler=None):
        self.tg = telegram_handler

    # ════════════════════════════════════════════════════════════
    # 3 VARİASYON ÜRETİMİ
    # ════════════════════════════════════════════════════════════
    async def synthesize_variations(
        self,
        trend: Dict,
        channel_theme: str,
        job_id: str,
        count: int = 3,
    ) -> List[Dict]:
        """
        Aynı trend için 3 farklı varyasyon üretir.
        Her biri farklı ton/açı/format ile.
        Telegram'a 3 seçenek sunar, sen birini seçersin.
        """
        tones = [
            ("educational",  "Bilgilendirici ve detaylı — izleyiciyi öğretir"),
            ("motivational", "İlham verici ve enerjik — izleyiciyi harekete geçirir"),
            ("storytelling", "Hikaye anlatımı — kişisel deneyim ve duygusal bağ"),
        ]

        variations = []
        for tone_name, tone_desc in tones[:count]:
            prompt = self._variation_prompt(trend, channel_theme, tone_name, tone_desc)
            result = self._call_ollama(prompt)
            result["variation_tone"] = tone_name
            result["variation_desc"] = tone_desc
            variations.append(result)
            log.info(f"Variation generated: {tone_name} — {result.get('title','')[:40]}")

        # Telegram'a 3 seçenek gönder
        if self.tg and variations:
            await self._send_variation_choice(variations, job_id)

        return variations

    async def _send_variation_choice(self, variations: List[Dict], job_id: str):
        """3 varyasyonu Telegram'a gönder, kullanıcı seçim yapsın."""
        lines = [f"🎯 <b>3 Varyasyon Hazır — Job #{job_id}</b>\n"]
        keyboard_rows = []

        for i, v in enumerate(variations, 1):
            tone  = v.get("variation_tone", f"V{i}")
            title = v.get("title", "")
            hook  = v.get("hook", "")[:80]
            lines.append(
                f"<b>Varyasyon {i} — {tone.upper()}</b>\n"
                f"📌 {title}\n"
                f"💬 {hook}...\n"
            )
            keyboard_rows.append([
                __import__('telegram').InlineKeyboardButton(
                    f"✅ Varyasyon {i} seç",
                    callback_data=f"{job_id}:var_{i-1}"
                )
            ])

        from telegram import InlineKeyboardMarkup
        keyboard_rows.append([
            __import__('telegram').InlineKeyboardButton("✏️ Hepsini değiştir", callback_data=f"{job_id}:var_redo"),
            __import__('telegram').InlineKeyboardButton("❌ İptal", callback_data=f"{job_id}:cancel"),
        ])

        await self.tg.app.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text="\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )

    # ════════════════════════════════════════════════════════════
    # DOĞAL DİL DÜZENLEMESİ
    # ════════════════════════════════════════════════════════════
    def apply_edit_instruction(
        self,
        original_content: Dict,
        instruction: str,
        content_type: str = "script",  # "script" | "title" | "outline" | "product"
    ) -> Dict:
        """
        "Giriş bölümünü kısalt", "ton daha enerjik olsun", "3. maddeyi çıkar"
        gibi doğal dil talimatlarını uygular ve güncellenmiş içeriği döndürür.
        """
        log.info(f"Applying edit: '{instruction[:60]}...' to {content_type}")

        prompt = f"""You are an editor. Apply the following instruction to the content below.
Return ONLY the updated content in the same JSON format. Do not explain.

INSTRUCTION: {instruction}

ORIGINAL {content_type.upper()}:
{json.dumps(original_content, ensure_ascii=False, indent=2)}

Return the updated version with the same JSON structure, applying the instruction precisely."""

        result = self._call_ollama(prompt, model="qwen2.5:3b")

        # Eğer result boşsa original'i döndür
        if not result or "error" in result:
            log.warning("Edit instruction failed — returning original")
            return original_content

        # Değişen alanları logla
        changed = []
        for key in original_content:
            if key in result and result[key] != original_content[key]:
                changed.append(key)
        log.info(f"Edit applied. Changed fields: {changed}")

        result["_edit_applied"] = instruction
        result["_changed_fields"] = changed
        return result

    async def apply_edit_interactive(
        self,
        original_content: Dict,
        job_id: str,
        content_type: str = "script",
    ) -> Dict:
        """
        Telegram'dan düzenleme talimatı bekler.
        Kullanıcı mesaj yazınca uygular, onaya sunar.
        """
        if not self.tg:
            return original_content

        await self.tg.send_message(
            f"✏️ <b>Düzenleme Modu — Job #{job_id}</b>\n\n"
            f"Ne değiştirilmesini istiyorsun? Mesaj olarak yaz:\n\n"
            f"Örnekler:\n"
            f"• <i>Giriş bölümünü daha kısa yap</i>\n"
            f"• <i>Ton daha enerjik olsun</i>\n"
            f"• <i>3. maddeyi çıkar, yerine nefes egzersizi ekle</i>\n"
            f"• <i>Başlık daha merak uyandırıcı olsun</i>"
        )

        # Kullanıcı mesajını bekle
        instruction = await self._wait_for_text_message(job_id, timeout=300)
        if not instruction:
            return original_content

        # Uygula
        updated = self.apply_edit_instruction(original_content, instruction, content_type)

        # Önizle ve onay al
        await self.tg.send_message(
            f"🔄 <b>Düzenleme Uygulandı</b>\n\n"
            f"<b>Talimat:</b> {instruction}\n"
            f"<b>Değişen alanlar:</b> {', '.join(updated.get('_changed_fields', []))}\n\n"
            f"<b>Yeni başlık:</b> {updated.get('title', '')}\n\n"
            f"Onaylıyor musun?"
        )

        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Onayla",          callback_data=f"{job_id}:edit_ok"),
            InlineKeyboardButton("🔄 Tekrar düzenle",  callback_data=f"{job_id}:edit_again"),
            InlineKeyboardButton("↩️ Orijinale dön",   callback_data=f"{job_id}:edit_revert"),
        ]])
        await self.tg.app.bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text="👆 Seçimini yap:",
            reply_markup=keyboard
        )

        action = await self.tg._wait_for_callback(f"{job_id}_edit")
        if action == "edit_ok":
            return updated
        elif action == "edit_again":
            return await self.apply_edit_interactive(updated, job_id, content_type)
        else:
            return original_content

    async def _wait_for_text_message(self, job_id: str, timeout: int = 300) -> Optional[str]:
        """Kullanıcıdan düz metin mesajı bekle."""
        import asyncio
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        key = f"text_{job_id}"
        self.tg._pending_callbacks[key] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            log.warning(f"Text message timeout for {job_id}")
            return None

    # ════════════════════════════════════════════════════════════
    # GÖRSEL / VİDEO REFERANS ANALİZİ
    # ════════════════════════════════════════════════════════════
    def analyze_reference_image(
        self,
        image_path: str,
        context: str = "video thumbnail",
    ) -> Dict:
        """
        Bir resim veya video frame'ini analiz eder.
        Renk paleti, kompozisyon, stil, ton çıkarır.
        Bu stil profili sonraki üretimlerde referans alınır.

        Desteklenen: .jpg, .png, .webp
        Video için: önce frame çıkarılır (FFmpeg), sonra analiz edilir.
        """
        # Video ise frame çıkar
        if image_path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
            image_path = self._extract_video_frame(image_path)
            if not image_path:
                return {}

        # Görüntüyü base64'e çevir
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            log.error(f"Image read failed: {e}")
            return {}

        # Ollama vision modeli varsa kullan (llava), yoksa text tabanlı analiz
        style_profile = self._analyze_with_vision(img_b64, context)
        if not style_profile:
            style_profile = self._analyze_filename_fallback(image_path, context)

        log.info(f"Reference image analyzed: {style_profile.get('style_name','unknown')}")
        return style_profile

    def _analyze_with_vision(self, img_b64: str, context: str) -> Optional[Dict]:
        """Ollama llava modeli ile görsel analiz."""
        try:
            resp = requests.post(OLLAMA_CHAT, json={
                "model": "llava",
                "messages": [{
                    "role": "user",
                    "content": f"Analyze this {context} image. Extract style information.",
                    "images": [img_b64]
                }],
                "format": "json",
                "stream": False,
            }, timeout=60)

            if resp.status_code == 200:
                raw = resp.json().get("message", {}).get("content", "{}")
                return json.loads(raw) if raw.startswith("{") else self._parse_vision_text(raw)
        except Exception as e:
            log.warning(f"Vision model failed: {e}")

        # Gemini vision fallback
        return self._analyze_with_gemini_vision(img_b64, context)

    def _analyze_with_gemini_vision(self, img_b64: str, context: str) -> Optional[Dict]:
        """Gemini vision ile görsel analiz (Ollama llava yoksa)."""
        if not Config.GEMINI_API_KEY:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash-latest")

            import PIL.Image
            import io
            img_bytes = base64.b64decode(img_b64)
            img = PIL.Image.open(io.BytesIO(img_bytes))

            response = model.generate_content([
                f"""Analyze this {context} and extract its visual style.
Respond ONLY with JSON:
{{
  "style_name": "brief style name (e.g. dark minimal, bright energetic)",
  "dominant_colors": ["#hex1", "#hex2", "#hex3"],
  "background_color": "#hex",
  "accent_color": "#hex",
  "mood": "calm|energetic|dark|bright|minimal|busy",
  "composition": "centered|rule_of_thirds|full_bleed|split",
  "text_style": "bold_white|dark_minimal|colorful|none",
  "font_weight": "light|regular|bold|extra_bold",
  "recommended_for": ["fitness", "ambiance", "documentary"],
  "style_keywords": ["keyword1", "keyword2", "keyword3"],
  "thumbnail_guidance": "specific advice for replicating this style"
}}""",
                img
            ])
            result = json.loads(response.text.strip())
            log.info("Gemini vision analysis complete")
            return result
        except Exception as e:
            log.warning(f"Gemini vision failed: {e}")
            return None

    def _parse_vision_text(self, text: str) -> Dict:
        """Vision modeli JSON yerine düz metin döndürdüyse parse et."""
        return {
            "style_name":    "analyzed",
            "mood":          "neutral",
            "raw_analysis":  text[:500],
            "style_keywords": [],
        }

    def _analyze_filename_fallback(self, path: str, context: str) -> Dict:
        """Görsel analiz tamamen başarısız olursa temel profil döndür."""
        import os
        fname = os.path.basename(path).lower()
        mood = "energetic" if any(w in fname for w in ["fit","gym","work","hiit"]) else \
               "calm"      if any(w in fname for w in ["sleep","relax","calm","med"]) else \
               "neutral"
        return {
            "style_name":    "auto-detected",
            "mood":          mood,
            "style_keywords": [mood],
            "thumbnail_guidance": f"Use {mood} visual style based on filename"
        }

    def _extract_video_frame(self, video_path: str) -> Optional[str]:
        """Video'dan ilk kareyi PNG olarak çıkar."""
        import subprocess, os
        frame_path = video_path.replace(".mp4","_frame.jpg").replace(".mov","_frame.jpg")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vframes", "1", "-q:v", "2",
            frame_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return frame_path if result.returncode == 0 else None
        except Exception as e:
            log.error(f"Frame extraction failed: {e}")
            return None

    def apply_style_to_prompt(
        self,
        base_prompt: str,
        style_profile: Dict,
        influence: float = 0.35,
    ) -> str:
        """
        Stil profilini mevcut bir prompt'a ekle.

        influence parametresi referansın ne kadar etkili olacağını belirler:
          0.0  = referans tamamen görmezden gelinir
          0.35 = hafif dokunuş — sistem kendi kararının %65'ini korur (varsayılan)
          0.65 = belirgin etki
          1.0  = referansı tam uygula

        %35 için prompt dili: "gözlemle ama kendi yaratıcılığını koru"
        %65 için prompt dili: "bu stili belirgin şekilde yansıt"
        %100 için prompt dili: "bu stili tamamen uygula"
        """
        if not style_profile or influence <= 0:
            return base_prompt

        # Etki seviyesine göre talimat dili
        if influence <= 0.25:
            directive = (
                "VERY SUBTLE REFERENCE ONLY — barely noticeable influence. "
                "Your own creative judgment dominates 90%+. "
                "Only note the color family if it fits naturally."
            )
        elif influence <= 0.45:
            directive = (
                "LIGHT REFERENCE INFLUENCE (~35%) — use this as a soft background hint. "
                "Your own creative decisions lead (65%). "
                "Adopt the general mood only if it fits the content. "
                "Do NOT copy colors, layout, or specific visual elements directly. "
                "Let the reference inform tone, not dictate form."
            )
        elif influence <= 0.70:
            directive = (
                "MODERATE REFERENCE INFLUENCE (~50%) — balance reference style with content needs. "
                "Consider colors and mood while keeping content-appropriate choices."
            )
        else:
            directive = (
                "STRONG REFERENCE INFLUENCE (~80%) — closely follow this visual style. "
                "Adopt colors, mood, and composition where applicable."
            )

        style_context = f"""

--- VISUAL STYLE REFERENCE (influence: {int(influence*100)}%) ---
{directive}

Reference details (treat as soft inspiration, not hard rules):
- Style name: {style_profile.get('style_name', '')}
- Mood: {style_profile.get('mood', '')}
- Color family: {style_profile.get('dominant_colors', ['unknown'])[0] if style_profile.get('dominant_colors') else 'unspecified'}
- Style keywords: {', '.join(style_profile.get('style_keywords', [])[:2])}

Remember: your content judgment is primary ({int((1-influence)*100)}%). Reference is secondary ({int(influence*100)}%).
--- END REFERENCE ---
"""
        return base_prompt + style_context

    # ════════════════════════════════════════════════════════════
    # MEVCUT METODLAR (değişmedi)
    # ════════════════════════════════════════════════════════════
    async def synthesize_video_topic(
        self,
        trend: Dict,
        channel_theme: str,
        job_id: str,
        use_paid: bool = False,
        style_profile: Dict = None,
    ) -> Dict:
        prompt = self._video_prompt(trend, channel_theme)
        if style_profile:
            prompt = self.apply_style_to_prompt(prompt, style_profile)

        if use_paid and self.tg:
            approved = await self.tg.send_cost_prompt(
                job_id=job_id,
                model_name="Gemini Flash",
                estimated_cost="$0.01–0.03",
                reason="Complex video synthesis"
            )
            if approved:
                return await self._call_gemini(prompt)

        return self._call_ollama(prompt)

    async def synthesize_product_idea(
        self,
        trend: Dict,
        product_type: str = "PDF guide",
        job_id: str = "",
        style_profile: Dict = None,
    ) -> Dict:
        prompt = self._product_prompt(trend, product_type)
        if style_profile:
            prompt = self.apply_style_to_prompt(prompt, style_profile)
        return self._call_ollama(prompt)

    def _call_ollama(self, prompt: str, model: str = None) -> Dict:
        model = model or OLLAMA_MODEL
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model":  model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }, timeout=120)
            resp.raise_for_status()
            raw    = resp.json().get("response", "{}")
            result = json.loads(raw)
            log.info(f"Ollama complete ({model})")
            return result
        except Exception as e:
            log.error(f"Ollama failed: {e}")
            return self._fallback_response()

    async def _call_gemini(self, prompt: str) -> Dict:
        if not Config.GEMINI_API_KEY:
            return self._call_ollama(prompt)
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model    = genai.GenerativeModel("gemini-1.5-flash-latest")
            response = model.generate_content(prompt + "\n\nRespond ONLY with valid JSON.")
            result   = json.loads(response.text)
            log.info("Gemini Flash complete")
            return result
        except Exception as e:
            log.error(f"Gemini failed: {e}")
            return self._call_ollama(prompt)

    async def _call_claude(self, prompt: str) -> Dict:
      async def _call_openrouter(self, prompt: str, model: str = None) -> Dict:
    """
    OpenRouter API — 100+ model tek endpoint üzerinden.
    Ücretsiz modeller: meta-llama/llama-3.1-8b-instruct:free
                       mistralai/mistral-7b-instruct:free
                       google/gemma-2-9b-it:free
    Ücretli modeller:  openai/gpt-4o, anthropic/claude-3.5-sonnet vs.
    """
    if not Config.OPENROUTER_API_KEY:
        log.warning("OpenRouter API key not set — falling back to Ollama")
        return self._call_ollama(prompt)
    try:
        import requests
        model = model or Config.OPENROUTER_MODEL
        resp  = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://mindfully.brand",  # isteğe bağlı
                "X-Title":       "Mindfully Brand Automation",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt + "\n\nRespond ONLY with valid JSON."}
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=120
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        result  = json.loads(content)
        log.info(f"OpenRouter complete ({model})")
        return result
    except Exception as e:
        log.error(f"OpenRouter failed: {e} — falling back to Ollama")
        return self._call_ollama(prompt)
        if not Config.CLAUDE_API_KEY:
            return self._call_ollama(prompt)
        try:
            import anthropic
            client  = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt + "\n\nRespond ONLY with valid JSON."}]
            )
            result = json.loads(message.content[0].text)
            log.info("Claude Haiku complete")
            return result
        except Exception as e:
            log.error(f"Claude failed: {e}")
            return self._call_ollama(prompt)

    def _video_prompt(self, trend: Dict, channel_theme: str) -> str:
        return f"""You are a YouTube content strategist for a {channel_theme} channel.
Trend: {trend.get('topic')} (popularity: {trend.get('popularity')}/100)
Related: {trend.get('related')}

Create a compelling YouTube video concept. Respond with JSON:
{{
  "title": "engaging title (max 60 chars)",
  "hook": "first 15 seconds hook script",
  "script_outline": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "estimated_duration_min": 5,
  "thumbnail_concept": "brief thumbnail description",
  "cta": "call to action"
}}"""

    def _variation_prompt(self, trend: Dict, channel_theme: str, tone: str, tone_desc: str) -> str:
        return f"""You are a YouTube content strategist for a {channel_theme} channel.
Trend: {trend.get('topic')} (popularity: {trend.get('popularity')}/100)
Tone: {tone} — {tone_desc}

Create a video concept with this specific tone. Respond with JSON:
{{
  "title": "title matching the {tone} tone (max 60 chars)",
  "hook": "opening hook in {tone} style (15 seconds)",
  "script_outline": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "tags": ["tag1", "tag2", "tag3"],
  "estimated_duration_min": 5,
  "thumbnail_concept": "thumbnail idea for {tone} style",
  "why_this_tone": "1 sentence: why {tone} works for this topic"
}}"""

    def _product_prompt(self, trend: Dict, product_type: str) -> str:
        return f"""You are a digital product creator for wellness content.
Trend: {trend.get('topic')} (popularity: {trend.get('popularity')}/100)
Product type: {product_type}

Create a digital product concept. Respond with JSON:
{{
  "title": "product title",
  "subtitle": "one-line description",
  "description": "2-3 sentence sales description",
  "chapters": ["chapter 1", "chapter 2", "chapter 3", "chapter 4"],
  "price_suggestion": 19,
  "target_audience": "specific audience",
  "lead_magnet_version": "free version title"
}}"""

    def _fallback_response(self) -> Dict:
        return {"title": "Synthesis failed — please retry", "error": "AI unavailable"}
