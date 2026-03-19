"""
documentary_producer.py — Phase 2 / channel_documentary
──────────────────────────────────────────────────────────
MINDFULLY BRAND — Belgesel Kanalı

Konu kategorileri:
  - Yiyecek tarihi   (pizzanın tarihi, baharatlar, kahve, ekmek...)
  - Bilim            (evren, DNA, sinir sistemi, uyku bilimi...)
  - Tarih            (uygarlıklar, keşifler, olaylar...)
  - Doğa             (hayvanlar, ekosistemler...)
  - Psikoloji        (alışkanlıklar, karar verme, sosyal davranış...)
  - Teknoloji        (internetin tarihi, yapay zeka, uzay teknolojisi...)

Pipeline:
  1. AI konu önerir → sen onaylarsın (Telegram)
  2. Script yazılır (Ollama veya Gemini)
  3. Narrasyon üretilir (Kokoro TTS)
  4. Görseller toplanır (Pexels)
  5. Video montajı (FFmpeg)
  6. Thumbnail (Pillow)
  7. YouTube draft yükleme

Video yapısı (20–40 dk):
  cold_open → context → chapter_1 → chapter_2 → chapter_3 → surprising_fact → conclusion → outro
"""
import os
import json
import requests
import subprocess
from typing import Dict, List, Optional

from config import Config
from utils.logger import get_logger
from utils.helpers import generate_job_id, safe_json_save

log = get_logger("documentary_producer")


class DocumentaryProducer:

    def __init__(self, telegram_handler=None):
        self.tg       = telegram_handler
        self.jobs_dir = Config.JOBS_DIR

    # ════════════════════════════════════════════════════════════
    # ADIM 0: KONU ÖNERİSİ (AI → Sen onaylarsın)
    # ════════════════════════════════════════════════════════════
    async def suggest_topics(self, category: str = None, count: int = 3) -> List[Dict]:
        """
        Ollama ile belgesel konu önerileri üret.
        Telegram'a gönder, onay bekle.
        """
        from ai_synthesizer import AISynthesizer
        synth = AISynthesizer(self.tg)

        categories = Config.CHANNELS["channel_documentary"]["documentary_categories"]
        if not category:
            import random
            category = random.choice(categories)

        prompt = f"""You are a documentary video strategist for YouTube.
Category: {category}
Generate {count} compelling documentary video topics for YouTube.
Each topic should be:
- Surprising or counterintuitive
- Educational but entertaining
- 20-40 minute format
- Based on verifiable facts

Respond ONLY with JSON:
{{
  "topics": [
    {{
      "title": "video title (max 70 chars, hook-based)",
      "category": "{category}",
      "hook": "opening surprising fact (1 sentence)",
      "chapters": ["chapter 1 topic", "chapter 2 topic", "chapter 3 topic"],
      "surprising_fact": "the most mind-blowing fact in this video",
      "estimated_duration_min": 25,
      "keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ]
}}"""

        result = synth._call_ollama(prompt)
        topics = result.get("topics", [])
        log.info(f"Documentary topics generated: {len(topics)}")
        return topics

    # ════════════════════════════════════════════════════════════
    # ADIM 1: SCRIPT YAZ
    # ════════════════════════════════════════════════════════════
    async def write_script(self, topic: Dict, job_id: str) -> Dict:
        """
        Belgesel script'i yaz.
        Yapı: cold_open → context → 3 chapter → surprising_fact → conclusion → outro
        """
        from ai_synthesizer import AISynthesizer
        synth = AISynthesizer(self.tg)

        duration   = topic.get("estimated_duration_min", 25)
        word_count = duration * 130  # ~130 kelime/dakika konuşma hızı

        prompt = f"""You are a documentary scriptwriter. Write a full documentary script.

Topic: {topic['title']}
Category: {topic['category']}
Opening hook: {topic['hook']}
Chapters: {', '.join(topic.get('chapters', []))}
Target duration: {duration} minutes (~{word_count} words)
Surprising fact: {topic.get('surprising_fact', '')}

Write an engaging, fact-based documentary script with this structure.
Use a warm, authoritative narrator voice. Include smooth transitions.

Respond ONLY with JSON:
{{
  "title": "{topic['title']}",
  "total_word_count": {word_count},
  "sections": {{
    "cold_open": "script text (60 seconds, most surprising fact first)",
    "context": "script text (3 minutes, background and why this matters)",
    "chapter_1": "script text (6-8 minutes, {topic.get('chapters', [''])[0]})",
    "chapter_2": "script text (6-8 minutes, {topic.get('chapters', [''])[1] if len(topic.get('chapters',[])) > 1 else 'part 2'})",
    "chapter_3": "script text (6-8 minutes, {topic.get('chapters', [''])[2] if len(topic.get('chapters',[])) > 2 else 'part 3'})",
    "surprising_fact": "script text (2 minutes, most mind-blowing revelation)",
    "conclusion": "script text (3 minutes, impact and takeaways)",
    "outro": "script text (60 seconds, subscribe CTA)"
  }},
  "visual_cues": ["visual suggestion 1", "visual suggestion 2", "visual suggestion 3"],
  "b_roll_keywords": ["search term for stock footage 1", "search term 2", "search term 3"]
}}"""

        # Uzun script için Gemini tercih et
        if self.tg:
            approved = await self.tg.send_cost_prompt(
                job_id=job_id,
                model_name="Gemini Flash",
                estimated_cost="$0.03–0.05",
                reason=f"Long documentary script ({word_count} words) — Ollama too slow"
            )
            if approved:
                return await synth._call_gemini(prompt)

        return synth._call_ollama(prompt, model="qwen2.5:3b")

    # ════════════════════════════════════════════════════════════
    # ADIM 2: NARRASYON (Kokoro TTS)
    # ════════════════════════════════════════════════════════════
    async def generate_narration(self, script: Dict, job_id: str, out_dir: str) -> Dict[str, str]:
        """
        Her bölüm için ayrı ses dosyası üret.
        Returns: {section_name: audio_file_path}
        """
        os.makedirs(out_dir, exist_ok=True)
        audio_files = {}

        sections = script.get("sections", {})
        section_order = [
            "cold_open", "context", "chapter_1", "chapter_2",
            "chapter_3", "surprising_fact", "conclusion", "outro"
        ]

        for section in section_order:
            text = sections.get(section, "")
            if not text:
                continue

            audio_path = os.path.join(out_dir, f"{section}.mp3")

            # Kokoro TTS dene
            try:
                resp = requests.post(
                    "http://localhost:8880/tts",
                    json={"text": text, "voice": "en_us_001", "speed": 0.95},
                    timeout=300
                )
                if resp.status_code == 200:
                    with open(audio_path, "wb") as f:
                        f.write(resp.content)
                    audio_files[section] = audio_path
                    log.info(f"Narration: {section} → {audio_path}")
                    continue
            except Exception as e:
                log.warning(f"Kokoro failed for {section}: {e}")

            # Edge-TTS fallback
            try:
                import asyncio
                import edge_tts
                communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
                await communicate.save(audio_path)
                audio_files[section] = audio_path
                log.info(f"Edge-TTS fallback: {section}")
            except Exception as e:
                log.error(f"TTS completely failed for {section}: {e}")

        return audio_files

    # ════════════════════════════════════════════════════════════
    # ADIM 3: GÖRSELLER (Pexels B-roll)
    # ════════════════════════════════════════════════════════════
    def fetch_broll(self, keywords: List[str], out_dir: str,
                     clips_per_keyword: int = 3) -> Dict[str, List[str]]:
        """Her anahtar kelime için B-roll videoları indir."""
        broll_dir = os.path.join(out_dir, "broll")
        os.makedirs(broll_dir, exist_ok=True)
        broll = {}

        for kw in keywords[:8]:  # max 8 arama terimi
            if not Config.PEXELS_API_KEY:
                break
            try:
                import time
                time.sleep(1)
                resp = requests.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": Config.PEXELS_API_KEY},
                    params={"query": kw, "per_page": clips_per_keyword,
                            "orientation": "landscape", "min_duration": 5},
                    timeout=20
                )
                resp.raise_for_status()
                files = []
                for video in resp.json().get("videos", []):
                    hd = next((f for f in video.get("video_files", [])
                                if f.get("quality") == "hd"), None)
                    if not hd:
                        continue
                    vpath = os.path.join(broll_dir, f"{kw[:20]}_{video['id']}.mp4")
                    if not os.path.exists(vpath):
                        vr = requests.get(hd["link"], timeout=60)
                        with open(vpath, "wb") as f:
                            f.write(vr.content)
                    files.append(vpath)
                broll[kw] = files
                log.info(f"B-roll: {kw} → {len(files)} clips")
            except Exception as e:
                log.warning(f"B-roll fetch failed ({kw}): {e}")

        return broll

    # ════════════════════════════════════════════════════════════
    # ADIM 4: VIDEO MONTAJI (FFmpeg)
    # ════════════════════════════════════════════════════════════
    def assemble_documentary(self, audio_files: Dict[str, str], broll: Dict,
                               out_dir: str, job_id: str) -> Optional[str]:
        """
        Her bölümü audio + ilgili b-roll ile birleştir.
        Sonra tüm bölümleri tek video yap.
        """
        section_order = [
            "cold_open", "context", "chapter_1", "chapter_2",
            "chapter_3", "surprising_fact", "conclusion", "outro"
        ]

        # Her bölüm için küçük video üret
        section_videos = []
        all_broll = [f for clips in broll.values() for f in clips]
        broll_idx  = 0

        for section in section_order:
            audio = audio_files.get(section)
            if not audio or not os.path.exists(audio):
                continue

            # Ses süresini al
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                audio
            ], capture_output=True, text=True)
            try:
                audio_dur = float(probe.stdout.strip())
            except Exception:
                audio_dur = 60.0

            # B-roll videoyu seç (döngüsel)
            if all_broll:
                broll_file = all_broll[broll_idx % len(all_broll)]
                broll_idx += 1
            else:
                broll_file = None

            section_video = os.path.join(out_dir, f"section_{section}.mp4")

            if broll_file and os.path.exists(broll_file):
                cmd = [
                    "ffmpeg", "-y",
                    "-stream_loop", "-1", "-i", broll_file,
                    "-i", audio,
                    "-c:v", "libx264", "-c:a", "aac",
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                    "-shortest", "-t", str(audio_dur),
                    section_video
                ]
            else:
                # B-roll yok → siyah arka plan
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "color=c=black:size=1920x1080:r=30",
                    "-i", audio,
                    "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", "-t", str(audio_dur),
                    section_video
                ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    section_videos.append(section_video)
            except Exception as e:
                log.warning(f"Section {section} assembly failed: {e}")

        if not section_videos:
            log.error("No section videos produced")
            return None

        # Tüm bölümleri birleştir
        concat_file = os.path.join(out_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for sv in section_videos:
                f.write(f"file '{sv}'\n")

        output_path = os.path.join(out_dir, f"{job_id}_documentary_draft.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart",
            output_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                log.info(f"Documentary assembled: {output_path}")
                return output_path
            log.error(f"Final assembly failed: {result.stderr[-400:]}")
            return None
        except Exception as e:
            log.error(f"Assembly error: {e}")
            return None

    # ════════════════════════════════════════════════════════════
    # ANA ÜRETIM — tüm adımları çalıştır
    # ════════════════════════════════════════════════════════════
    async def produce(self, job_id: str, topic: Dict) -> Optional[str]:
        """Full documentary production pipeline."""
        log.info(f"Documentary production: {job_id} — {topic.get('title')}")

        out_dir = os.path.join(self.jobs_dir, job_id)
        os.makedirs(out_dir, exist_ok=True)

        # Script
        script = await self.write_script(topic, job_id)
        if not script or "sections" not in script:
            log.error("Script writing failed")
            return None

        # Narrasyon
        audio_dir   = os.path.join(out_dir, "audio")
        audio_files = await self.generate_narration(script, job_id, audio_dir)
        if not audio_files:
            log.error("Narration failed")
            return None

        # B-roll
        broll_keywords = script.get("b_roll_keywords",
                                     topic.get("keywords", ["nature", "science"])[:5])
        broll = self.fetch_broll(broll_keywords, out_dir)

        # Montaj
        output = self.assemble_documentary(audio_files, broll, out_dir, job_id)

        # Thumbnail
        if output:
            self._create_thumbnail(topic, out_dir)

        # Metadata
        safe_json_save(os.path.join(out_dir, "metadata.json"), {
            "job_id":       job_id,
            "channel_id":   "channel_documentary",
            "title":        topic.get("title"),
            "category":     topic.get("category"),
            "video_type":   "documentary",
            "video":        output,
            "tags":         topic.get("keywords", []) + ["documentary", "mindfully docs"],
            "description":  f"An in-depth documentary about {topic.get('title')}.\n\n"
                            f"#documentary #education #{topic.get('category', 'science')}",
        })
        return output

    def _create_thumbnail(self, topic: Dict, out_dir: str) -> str:
        from PIL import Image, ImageDraw, ImageFont

        img  = Image.new("RGB", (1280, 720), "#1A1A2E")
        draw = ImageDraw.Draw(img)

        # Sinematik çerçeve çizgisi
        draw.rectangle([0, 0, 1280, 60],  fill="#000000")
        draw.rectangle([0, 660, 1280, 720], fill="#000000")
        draw.rectangle([0, 60, 6, 660],   fill="#E94560")

        try:
            font_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 68)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except Exception:
            font_big = font_small = ImageFont.load_default()

        title = topic.get("title", "Documentary")
        words, lines, line = title.split(), [], ""
        for w in words:
            if len(line + w) > 22:
                lines.append(line.strip())
                line = w + " "
            else:
                line += w + " "
        if line:
            lines.append(line.strip())

        y = 720 // 2 - len(lines) * 42
        for ln in lines:
            draw.text((80, y), ln, fill="white", font=font_big)
            y += 85

        draw.text((80, 680), f"MINDFULLY DOCS  ·  {topic.get('category','').replace('_',' ').upper()}",
                   fill="#E94560", font=font_small)

        thumb_path = os.path.join(out_dir, "thumbnail.jpg")
        img.save(thumb_path, "JPEG", quality=95)
        return thumb_path
