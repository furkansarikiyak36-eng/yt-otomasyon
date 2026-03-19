"""
video_producer.py — Phase 1/2
───────────────────────────────
Produces short (3–5 min) and complex (10–20 min) videos.
Channel-aware: adapts style per channel theme.
Pipeline: script → TTS (Kokoro) → visuals (Pexels) → FFmpeg assembly
"""
import os
import subprocess
import requests
import tempfile
from typing import Dict, List, Optional

from config import Config
from utils.logger import get_logger
from utils.helpers import safe_json_save

log = get_logger("video_producer")

PEXELS_API = "https://api.pexels.com/videos/search"


class VideoProducer:
    def __init__(self):
        self.jobs_dir = Config.JOBS_DIR

    # ── Main entry ───────────────────────────────────────────────
    async def produce(
        self,
        job_id: str,
        script: Dict,
        channel_id: str,
        channel_theme: str = "wellness",
        video_type: str = "short",  # "short" | "complex" | "ambient" | "documentary"
    ) -> Optional[str]:
        """
        Produce a video. Returns path to output file or None on failure.
        """
        log.info(f"Starting video production: {job_id} ({video_type})")

        out_dir = os.path.join(self.jobs_dir, job_id)
        os.makedirs(out_dir, exist_ok=True)

        # 1. Generate audio via Kokoro TTS
        audio_path = await self._generate_audio(job_id, script, out_dir)
        if not audio_path:
            log.error(f"Audio generation failed for {job_id}")
            return None

        # 2. Fetch visuals from Pexels
        visual_paths = self._fetch_visuals(
            query=script.get("title", channel_theme),
            count=5 if video_type == "short" else 15,
            out_dir=out_dir
        )

        # 3. Generate thumbnail via Pillow
        thumbnail_path = self._create_thumbnail(
            title=script.get("title", ""),
            out_dir=out_dir,
            theme=channel_theme
        )

        # 4. Assemble video via FFmpeg
        output_path = os.path.join(out_dir, f"{job_id}_draft.mp4")
        success = self._assemble_video(
            audio_path=audio_path,
            visual_paths=visual_paths,
            output_path=output_path,
            video_type=video_type,
        )

        if success:
            log.info(f"Video produced: {output_path}")
            # Save metadata
            safe_json_save(os.path.join(out_dir, "metadata.json"), {
                "job_id": job_id,
                "channel_id": channel_id,
                "title": script.get("title"),
                "tags": script.get("tags", []),
                "thumbnail": thumbnail_path,
                "video": output_path,
                "video_type": video_type,
            })
            return output_path
        return None

    # ── Kokoro TTS ───────────────────────────────────────────────
    async def _generate_audio(self, job_id: str, script: Dict, out_dir: str) -> Optional[str]:
        """
        Generate narration audio using Kokoro v1 (local).
        Falls back to edge-tts if Kokoro unavailable.
        """
        audio_path = os.path.join(out_dir, f"{job_id}_audio.mp3")
        full_script = self._build_narration(script)

        # Try Kokoro v1 first
        try:
            # Kokoro v1 runs as local service on port 8880
            resp = requests.post(
                "http://localhost:8880/tts",
                json={"text": full_script, "voice": "af_sky", "speed": 1.0},
                timeout=120
            )
            if resp.status_code == 200:
                with open(audio_path, "wb") as f:
                    f.write(resp.content)
                log.info(f"Kokoro TTS complete: {audio_path}")
                return audio_path
        except Exception as e:
            log.warning(f"Kokoro unavailable: {e} — trying edge-tts")

        # Fallback: edge-tts
        try:
            import asyncio
            import edge_tts
            communicate = edge_tts.Communicate(full_script, "en-US-JennyNeural")
            await communicate.save(audio_path)
            log.info(f"Edge-TTS fallback complete: {audio_path}")
            return audio_path
        except Exception as e:
            log.error(f"TTS completely failed: {e}")
            return None

    def _build_narration(self, script: Dict) -> str:
        parts = []
        if script.get("hook"):
            parts.append(script["hook"])
        for point in script.get("script_outline", []):
            parts.append(point)
        if script.get("cta"):
            parts.append(script["cta"])
        return " ".join(parts)

    # ── Pexels visuals ───────────────────────────────────────────
    def _fetch_visuals(self, query: str, count: int, out_dir: str) -> List[str]:
        if not Config.PEXELS_API_KEY:
            log.warning("PEXELS_API_KEY not set — using placeholder visuals")
            return []
        paths = []
        try:
            resp = requests.get(
                PEXELS_API,
                headers={"Authorization": Config.PEXELS_API_KEY},
                params={"query": query, "per_page": count, "min_duration": 5},
                timeout=30
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            for i, video in enumerate(videos[:count]):
                files = video.get("video_files", [])
                # Pick HD quality
                hd = next((f for f in files if f.get("quality") == "hd"), files[0] if files else None)
                if not hd:
                    continue
                vpath = os.path.join(out_dir, f"visual_{i}.mp4")
                vresp = requests.get(hd["link"], timeout=60)
                with open(vpath, "wb") as f:
                    f.write(vresp.content)
                paths.append(vpath)
            log.info(f"Fetched {len(paths)} visuals from Pexels")
        except Exception as e:
            log.warning(f"Pexels fetch failed: {e}")
        return paths

    # ── Pillow thumbnail ──────────────────────────────────────────
    def _create_thumbnail(self, title: str, out_dir: str, theme: str = "wellness") -> str:
        from PIL import Image, ImageDraw, ImageFont

        # Theme colors — matches MINDFULLY BRAND channel palettes
        from config import Config
        # Try to get from channel config first
        ch = Config.get_channel_by_theme(theme)
        if ch and ch.get("color_palette"):
            bg_color = ch["color_palette"][1]  # dark color as bg
            accent   = ch["color_palette"][0]  # accent color
        else:
            fallback = {
                "fitness":     ("#1C1C1C", "#FF6B35"),
                "ambiance":    ("#0D0D0D", "#7EB8B3"),
                "documentary": ("#1A1A2E", "#E94560"),
                "wellness":    ("#1A1A2E", "#E94560"),
            }
            bg_color, accent = fallback.get(theme, ("#1A1A2E", "#E94560"))

        img = Image.new("RGB", (1280, 720), bg_color)
        draw = ImageDraw.Draw(img)

        # Accent bar
        draw.rectangle([0, 0, 8, 720], fill=accent)

        # Title text (wrap at 30 chars per line)
        words = title.split()
        lines = []
        line = ""
        for w in words:
            if len(line + w) > 28:
                lines.append(line.strip())
                line = w + " "
            else:
                line += w + " "
        if line:
            lines.append(line.strip())

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        except Exception:
            font = ImageFont.load_default()

        y = 720 // 2 - (len(lines) * 80) // 2
        for line_text in lines:
            draw.text((80, y), line_text, fill="white", font=font)
            y += 90

        # Accent dot
        draw.ellipse([1200, 650, 1260, 710], fill=accent)

        thumb_path = os.path.join(out_dir, "thumbnail.jpg")
        img.save(thumb_path, "JPEG", quality=95)
        log.info(f"Thumbnail created: {thumb_path}")
        return thumb_path

    # ── FFmpeg assembly ──────────────────────────────────────────
    def _assemble_video(
        self,
        audio_path: str,
        visual_paths: List[str],
        output_path: str,
        video_type: str = "short",
    ) -> bool:
        if not visual_paths:
            log.warning("No visuals available — creating audio-only video")
            # Create a simple black background video
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=30",
                "-i", audio_path,
                "-c:v", "libx264", "-c:a", "aac",
                "-shortest", output_path
            ]
        else:
            # Create concat file
            concat_file = output_path.replace(".mp4", "_concat.txt")
            with open(concat_file, "w") as f:
                for vp in visual_paths:
                    f.write(f"file '{vp}'\n")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-i", audio_path,
                "-c:v", "libx264", "-c:a", "aac",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-shortest", output_path
            ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                log.info(f"FFmpeg assembly complete: {output_path}")
                return True
            else:
                log.error(f"FFmpeg failed: {result.stderr[-500:]}")
                return False
        except subprocess.TimeoutExpired:
            log.error("FFmpeg timed out (>600s)")
            return False
        except Exception as e:
            log.error(f"FFmpeg error: {e}")
            return False
