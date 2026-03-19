"""
ambiance_video_producer.py — Phase 2 / channel_ambiance
──────────────────────────────────────────────────────────
MINDFULLY BRAND — Ambiance Kanalı

Görev:
  Telifsiz müzikleri birleştir + arka plan animasyonu ekle
  → 30–60 dk loop video üret → YouTube draft olarak yükle

Pipeline:
  1. Müzik seç (Freesound API veya Pixabay Music)
  2. Müzikleri birleştir (FFmpeg crossfade)
  3. Arka plan animasyonu üret (FFmpeg lavfi)
  4. Müzik + animasyon birleştir
  5. Thumbnail oluştur (Pillow)
  6. YouTube draft yükle

Animasyon türleri:
  - particles : yüzen partiküller (genel amaçlı)
  - waves     : dalgalanan çizgiler (lo-fi, sakinleştirici)
  - starfield : yıldız alanı (uyku, meditasyon)
  - aurora    : kuzey ışıkları efekti (ambiyans)
  - rain      : yağmur damlaları (odaklanma)
  - gradient  : yavaş renk geçişi (minimal, profesyonel)
"""
import os
import subprocess
import requests
import random
import time
from typing import Dict, List, Optional, Tuple

from config import Config
from utils.logger import get_logger

log = get_logger("ambiance_video_producer")

# Telifsiz müzik API'leri
FREESOUND_SEARCH  = "https://freesound.org/apiv2/search/text/"
PIXABAY_MUSIC     = "https://pixabay.com/api/"


class AmbianceVideoProducer:

    def __init__(self):
        self.jobs_dir = Config.JOBS_DIR

    # ════════════════════════════════════════════════════════════
    # ANA GİRİŞ
    # ════════════════════════════════════════════════════════════
    async def produce(
        self,
        job_id: str,
        mood: str = "lofi",          # lofi | motivational | relaxing | sleep | study | focus
        animation_type: str = "particles",
        duration_minutes: int = 30,
        title: str = None,
    ) -> Optional[str]:
        """
        Ambiance video üret. Returns: output video path or None.

        mood: müzik ruh hali
        animation_type: arka plan animasyon türü
        duration_minutes: video süresi (30–60)
        """
        log.info(f"Ambiance production start: {job_id} | mood={mood} | anim={animation_type} | {duration_minutes}min")

        out_dir = os.path.join(self.jobs_dir, job_id)
        os.makedirs(out_dir, exist_ok=True)

        # 1. Müzik dosyalarını indir
        music_files = await self._fetch_music(mood, out_dir, duration_minutes)
        if not music_files:
            log.error(f"No music files fetched for mood: {mood}")
            return None

        # 2. Müzikleri birleştir (crossfade ile)
        combined_audio = self._combine_music(music_files, out_dir, job_id, duration_minutes)
        if not combined_audio:
            log.error("Music combination failed")
            return None

        # 3. Arka plan animasyonu üret
        animation = self._generate_animation(animation_type, out_dir, job_id, duration_minutes, mood)
        if not animation:
            log.error(f"Animation generation failed: {animation_type}")
            return None

        # 4. Animasyon + ses birleştir
        output_path = os.path.join(out_dir, f"{job_id}_ambiance_draft.mp4")
        success = self._merge_audio_video(animation, combined_audio, output_path)
        if not success:
            return None

        # 5. Thumbnail oluştur
        thumb_path = self._create_thumbnail(mood, animation_type, title or mood.upper(), out_dir)

        # 6. Metadata kaydet
        self._save_metadata(job_id, mood, animation_type, duration_minutes, title, thumb_path, output_path)

        log.info(f"Ambiance video ready: {output_path}")
        return output_path

    # ════════════════════════════════════════════════════════════
    # 1. TELİFSİZ MÜZİK İNDİR
    # ════════════════════════════════════════════════════════════
    async def _fetch_music(self, mood: str, out_dir: str, target_minutes: int) -> List[str]:
        """
        Freesound veya Pixabay'dan telifsiz müzik indir.
        Hedef süreyi dolduracak kadar parça topla.
        """
        music_dir = os.path.join(out_dir, "music")
        os.makedirs(music_dir, exist_ok=True)

        # Mood → arama terimi eşleştirme
        mood_queries = {
            "lofi":         ["lofi hip hop", "chillhop", "lofi beats"],
            "motivational": ["motivational background music", "uplifting instrumental", "epic background"],
            "relaxing":     ["relaxing ambient music", "peaceful background", "calm instrumental"],
            "sleep":        ["sleep music", "delta waves", "sleeping ambient"],
            "study":        ["study music", "concentration music", "focus instrumental"],
            "focus":        ["deep focus music", "concentration beats", "work music"],
            "meditation":   ["meditation music", "healing frequencies", "zen ambient"],
        }
        queries = mood_queries.get(mood, ["ambient music"])

        files = []
        total_seconds = 0
        target_seconds = target_minutes * 60

        # Freesound API dene
        if Config.FREESOUND_API_KEY:
            files, total_seconds = self._fetch_from_freesound(
                queries, music_dir, target_seconds
            )

        # Yeterli değilse Pixabay dene
        if total_seconds < target_seconds * 0.7:
            extra, extra_secs = self._fetch_from_pixabay(
                queries[0], music_dir, target_seconds - total_seconds
            )
            files += extra
            total_seconds += extra_secs

        if not files:
            log.warning("No music from APIs — using silence placeholder")
            # Sessiz ses dosyası oluştur (test/fallback)
            silence_path = os.path.join(music_dir, "silence.mp3")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(target_seconds),
                silence_path
            ], capture_output=True)
            files = [silence_path]

        log.info(f"Music fetched: {len(files)} files, ~{total_seconds//60} min total")
        return files

    def _fetch_from_freesound(self, queries: List[str], out_dir: str,
                               target_secs: int) -> Tuple[List[str], int]:
        files, total = [], 0
        for query in queries:
            if total >= target_secs:
                break
            try:
                time.sleep(1)
                resp = requests.get(FREESOUND_SEARCH, params={
                    "query":    query,
                    "filter":   "duration:[120 TO 600] license:\"Creative Commons 0\"",
                    "fields":   "id,name,duration,previews",
                    "token":    Config.FREESOUND_API_KEY,
                    "page_size": 10,
                }, timeout=20)
                resp.raise_for_status()
                results = resp.json().get("results", [])
                for item in results:
                    preview_url = item.get("previews", {}).get("preview-hq-mp3")
                    if not preview_url:
                        continue
                    fname = os.path.join(out_dir, f"fs_{item['id']}.mp3")
                    if not os.path.exists(fname):
                        r = requests.get(preview_url, timeout=30)
                        with open(fname, "wb") as f:
                            f.write(r.content)
                    files.append(fname)
                    total += int(item.get("duration", 0))
                    if total >= target_secs:
                        break
            except Exception as e:
                log.warning(f"Freesound fetch error ({query}): {e}")
        return files, total

    def _fetch_from_pixabay(self, query: str, out_dir: str,
                             target_secs: int) -> Tuple[List[str], int]:
        files, total = [], 0
        if not Config.PEXELS_API_KEY:  # Pixabay API key (aynı .env'de tutabiliriz)
            return files, total
        try:
            resp = requests.get(PIXABAY_MUSIC, params={
                "key":      Config.PEXELS_API_KEY,
                "q":        query,
                "media_type": "music",
                "per_page": 10,
            }, timeout=20)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                url = hit.get("audio", {}).get("mp3")
                if not url:
                    continue
                fname = os.path.join(out_dir, f"px_{hit['id']}.mp3")
                if not os.path.exists(fname):
                    r = requests.get(url, timeout=30)
                    with open(fname, "wb") as f:
                        f.write(r.content)
                files.append(fname)
                total += hit.get("duration", 180)
                if total >= target_secs:
                    break
        except Exception as e:
            log.warning(f"Pixabay music fetch error: {e}")
        return files, total

    # ════════════════════════════════════════════════════════════
    # 2. MÜZİKLERİ BİRLEŞTİR (crossfade)
    # ════════════════════════════════════════════════════════════
    def _combine_music(self, music_files: List[str], out_dir: str,
                        job_id: str, duration_minutes: int) -> Optional[str]:
        """
        Müzik dosyalarını crossfade ile birleştir.
        Hedef süreye ulaşmak için döngüye al.
        """
        combined_path = os.path.join(out_dir, f"{job_id}_combined_audio.mp3")
        target_secs   = duration_minutes * 60
        crossfade_secs = 3

        if len(music_files) == 1:
            # Tek dosya — loop et
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", music_files[0],
                "-t", str(target_secs),
                "-c:a", "libmp3lame", "-q:a", "2",
                combined_path
            ]
        else:
            # Çok dosya — crossfade ile birleştir
            # FFmpeg complex filter: acrossfade
            inputs = []
            for f in music_files:
                inputs += ["-i", f]

            # Basit concat (crossfade kompleks filtreyle)
            filter_parts = []
            for i in range(len(music_files) - 1):
                if i == 0:
                    filter_parts.append(
                        f"[0:a][1:a]acrossfade=d={crossfade_secs}[a01]"
                    )
                else:
                    filter_parts.append(
                        f"[a{str(i-1).zfill(2)}][{i+1}:a]acrossfade=d={crossfade_secs}[a{str(i).zfill(2)}]"
                    )
            final_label = f"[a{str(len(music_files)-2).zfill(2)}]" if len(music_files) > 2 else "[a01]"

            cmd = (
                ["ffmpeg", "-y"] +
                inputs +
                ["-filter_complex", ";".join(filter_parts),
                 "-map", final_label,
                 "-t", str(target_secs),
                 "-c:a", "libmp3lame", "-q:a", "2",
                 combined_path]
            )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                log.info(f"Music combined: {combined_path}")
                return combined_path
            # Fallback: basit concat
            return self._simple_concat(music_files, combined_path, target_secs)
        except Exception as e:
            log.error(f"Music combine error: {e}")
            return self._simple_concat(music_files, combined_path, target_secs)

    def _simple_concat(self, files: List[str], out_path: str, target_secs: int) -> Optional[str]:
        """Basit FFmpeg concat — crossfade olmadan."""
        concat_file = out_path.replace(".mp3", "_concat.txt")
        with open(concat_file, "w") as f:
            # Yeterli süreye ulaşmak için dosyaları tekrarla
            i = 0
            while True:
                f.write(f"file '{files[i % len(files)]}'\n")
                i += 1
                if i * 180 > target_secs:  # yaklaşık tahmin
                    break
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-t", str(target_secs),
            "-c:a", "libmp3lame", "-q:a", "2",
            out_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return out_path if result.returncode == 0 else None
        except Exception as e:
            log.error(f"Simple concat failed: {e}")
            return None

    # ════════════════════════════════════════════════════════════
    # 3. ARKA PLAN ANİMASYONU ÜRET (FFmpeg lavfi)
    # ════════════════════════════════════════════════════════════
    def _generate_animation(self, anim_type: str, out_dir: str, job_id: str,
                             duration_minutes: int, mood: str) -> Optional[str]:
        """
        FFmpeg lavfi filtrelerle arka plan animasyonu üret.
        Tüm animasyonlar 1920x1080, 30fps.
        """
        anim_path = os.path.join(out_dir, f"{job_id}_animation.mp4")
        duration  = duration_minutes * 60

        # Mood'a göre renk paleti
        mood_colors = {
            "lofi":         ("0x1a1a2e", "0x7eb8b3"),  # koyu lacivert + teal
            "motivational": ("0x1c1c1c", "0xff6b35"),  # siyah + turuncu
            "relaxing":     ("0x0d0d0d", "0x7eb8b3"),  # siyah + açık yeşil
            "sleep":        ("0x05051a", "0x2a2a6e"),  # çok koyu mavi
            "study":        ("0x0d1b2a", "0x1b4f72"),  # koyu mavi tonları
            "focus":        ("0x1a1a1a", "0x4a4a6a"),  # nötr koyu
            "meditation":   ("0x0d0d1a", "0x6b5b95"),  # koyu mor
        }
        bg_color, accent = mood_colors.get(mood, ("0x0d0d0d", "0x4a4a8a"))

        # Animasyon türlerine göre FFmpeg filtreleri
        filters = {
            "particles": (
                f"color=c={bg_color}:size=1920x1080:r=30,"
                f"noise=alls=3:allf=t,"
                f"eq=brightness=0.05"
            ),
            "waves": (
                f"color=c={bg_color}:size=1920x1080:r=30,"
                f"geq=lum='127+127*sin(2*PI*(X/W+T/10))'"
            ),
            "starfield": (
                f"color=c=0x000008:size=1920x1080:r=30,"
                f"noise=alls=15:allf=t+u,"
                f"curves=all='0/0 0.1/0.1 0.3/0.4 1/1'"
            ),
            "gradient": (
                f"color=c={bg_color}:size=1920x1080:r=30,"
                f"geq=r='clip(128+60*sin(2*PI*T/20),0,255)':"
                f"g='clip(80+40*sin(2*PI*T/25+PI/3),0,255)':"
                f"b='clip(180+60*sin(2*PI*T/30+PI/2),0,255)'"
            ),
            "aurora": (
                f"color=c=0x020818:size=1920x1080:r=30,"
                f"geq=r='clip(20+40*sin(2*PI*(X/W*3+T/15)),0,255)':"
                f"g='clip(80+100*sin(2*PI*(X/W*2+T/12)+PI/4),0,255)':"
                f"b='clip(120+80*sin(2*PI*(X/W*4+T/18)+PI/2),0,255)'"
            ),
            "rain": (
                f"color=c=0x0a1628:size=1920x1080:r=30,"
                f"noise=alls=5:allf=t,"
                f"geq=lum='clip(lum(X,Y)+30*sin(2*PI*(Y/H*8+T*2)),0,255)'"
            ),
        }

        vf_filter = filters.get(anim_type, filters["gradient"])

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"{vf_filter},format=yuv420p",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "28",          # boyut dengesi
            "-pix_fmt", "yuv420p",
            anim_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                log.info(f"Animation generated: {anim_type} → {anim_path}")
                return anim_path
            log.error(f"Animation failed ({anim_type}): {result.stderr[-400:]}")
            # Fallback: sade gradient
            return self._fallback_animation(bg_color, duration, anim_path)
        except subprocess.TimeoutExpired:
            log.error("Animation timed out")
            return self._fallback_animation(bg_color, duration, anim_path)

    def _fallback_animation(self, bg_color: str, duration: int, out_path: str) -> Optional[str]:
        """Basit sabit renkli arka plan — animasyon üretimi başarısız olursa."""
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={bg_color}:size=1920x1080:r=1",
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "35",
            out_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return out_path if result.returncode == 0 else None
        except Exception as e:
            log.error(f"Fallback animation failed: {e}")
            return None

    # ════════════════════════════════════════════════════════════
    # 4. ANİMASYON + SES BİRLEŞTİR
    # ════════════════════════════════════════════════════════════
    def _merge_audio_video(self, video_path: str, audio_path: str,
                            output_path: str) -> bool:
        """Video + ses birleştir. Video kanal süresi baz alınır."""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                log.info(f"Merge complete: {output_path}")
                return True
            log.error(f"Merge failed: {result.stderr[-300:]}")
            return False
        except Exception as e:
            log.error(f"Merge error: {e}")
            return False

    # ════════════════════════════════════════════════════════════
    # 5. THUMBNAIL
    # ════════════════════════════════════════════════════════════
    def _create_thumbnail(self, mood: str, anim_type: str,
                           title: str, out_dir: str) -> str:
        from PIL import Image, ImageDraw, ImageFont

        # Renk şeması
        palettes = {
            "lofi":         ("#1a1a2e", "#7eb8b3", "#ffffff"),
            "motivational": ("#1c1c1c", "#ff6b35", "#ffffff"),
            "relaxing":     ("#0d0d0d", "#7eb8b3", "#e0f0ee"),
            "sleep":        ("#05051a", "#4a4a9e", "#c0c0ff"),
            "study":        ("#0d1b2a", "#3498db", "#ffffff"),
            "focus":        ("#1a1a1a", "#9b59b6", "#ffffff"),
            "meditation":   ("#0d0d1a", "#8e44ad", "#dcc0ff"),
        }
        bg, accent, text_c = palettes.get(mood, ("#0d0d0d", "#7eb8b3", "#ffffff"))

        img  = Image.new("RGB", (1280, 720), bg)
        draw = ImageDraw.Draw(img)

        # Arka plan efekti — daireler
        for i in range(8):
            x = random.randint(0, 1280)
            y = random.randint(0, 720)
            r = random.randint(40, 200)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=accent + "20" if len(accent) == 7 else accent, outline=None)

        # Sol accent çizgi
        draw.rectangle([0, 0, 6, 720], fill=accent)

        # Başlık
        try:
            font_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except Exception:
            font_big = font_small = ImageFont.load_default()

        # Başlığı kır (max 22 karakter/satır)
        words = title.split()
        lines, line = [], ""
        for w in words:
            if len(line + w) > 20:
                lines.append(line.strip())
                line = w + " "
            else:
                line += w + " "
        if line:
            lines.append(line.strip())

        y_start = 720 // 2 - len(lines) * 45
        for ln in lines:
            draw.text((80, y_start), ln, fill=text_c, font=font_big)
            y_start += 90

        # Alt bilgi
        draw.text((80, 660), f"MINDFULLY AMBIANCE  ·  {mood.upper()}", fill=accent, font=font_small)

        thumb_path = os.path.join(out_dir, "thumbnail.jpg")
        img.save(thumb_path, "JPEG", quality=95)
        log.info(f"Thumbnail: {thumb_path}")
        return thumb_path

    # ════════════════════════════════════════════════════════════
    # 6. METADATA
    # ════════════════════════════════════════════════════════════
    def _save_metadata(self, job_id, mood, anim_type, duration_min,
                        title, thumb_path, video_path):
        from utils.helpers import safe_json_save
        import os
        safe_json_save(
            os.path.join(self.jobs_dir, job_id, "metadata.json"),
            {
                "job_id":          job_id,
                "channel_id":      "channel_ambiance",
                "title":           title or f"{mood.title()} Music Loop - {duration_min} Minutes",
                "mood":            mood,
                "animation_type":  anim_type,
                "duration_minutes": duration_min,
                "video_type":      "ambient",
                "thumbnail":       thumb_path,
                "video":           video_path,
                "tags": [
                    mood, "ambient music", "background music",
                    f"{mood} music", "no copyright music", "royalty free music",
                    f"{duration_min} minutes", "loop", "mindfully ambiance"
                ],
                "description": (
                    f"{duration_min} minutes of {mood} background music for "
                    f"studying, relaxing, working, or sleeping. "
                    f"All music is royalty-free. No copyright. Free to use.\n\n"
                    f"#ambient #backgroundmusic #{mood} #noCopyrightMusic"
                ),
            }
        )
