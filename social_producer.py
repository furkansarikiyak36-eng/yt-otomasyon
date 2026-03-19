"""
social_producer.py — Phase 2
──────────────────────────────
MINDFULLY BRAND — 2 Social Media Pipeline

Pipeline 1 — Organic:
  YouTube içeriklerini Instagram Reels, TikTok, Pinterest'e uygun
  kısa kliplere dönüştürür. Her gün 12:00 çalışır.

Pipeline 2 — Shopify:
  Shopify'da yeni ürün eklenince veya stok yenilenince tetiklenir (n8n).
  Ürün tanıtım içeriği üretir, onaylanınca yayınlanır.
"""
import os
import subprocess
from typing import Dict, List, Optional

from config import Config
from utils.logger import get_logger

log = get_logger("social_producer")


class SocialProducer:

    # ════════════════════════════════════════════════════════════
    # PİPELİNE 1: ORGANIC — YouTube klipten kısa format
    # ════════════════════════════════════════════════════════════

    async def produce_daily_clips(self, pipeline: Dict = None) -> List[str]:
        """
        En son YouTube videosundan platform-specific klipler üretir.
        Instagram: 30 sn | TikTok: 60 sn | Pinterest: 15 sn
        Returns: list of output file paths
        """
        pipeline = pipeline or Config.SOCIAL_PIPELINES["social_organic"]
        log.info(f"Daily clip production: {pipeline['name']}")

        # Son yüklenen video dosyasını bul
        source_video = self._get_latest_video()
        if not source_video:
            log.warning("No source video found for clip production")
            return []

        outputs = []
        for platform in pipeline["platforms"]:
            duration = pipeline["clip_length"].get(platform, 30)
            out_path  = self._cut_clip(source_video, platform, duration)
            if out_path:
                outputs.append(out_path)
                log.info(f"Clip ready for {platform}: {out_path}")

        return outputs

    def _get_latest_video(self) -> Optional[str]:
        """En son üretilen video dosyasını bul."""
        jobs_dir = Config.JOBS_DIR
        if not os.path.exists(jobs_dir):
            return None
        videos = []
        for d in os.listdir(jobs_dir):
            job_dir = os.path.join(jobs_dir, d)
            if os.path.isdir(job_dir):
                for f in os.listdir(job_dir):
                    if f.endswith("_draft.mp4"):
                        videos.append(os.path.join(job_dir, f))
        if not videos:
            return None
        return max(videos, key=os.path.getmtime)

    def _cut_clip(self, source: str, platform: str, duration: int) -> Optional[str]:
        """
        Platform için optimize edilmiş kısa klip üretir.
        Instagram/TikTok: 9:16 dikey format
        Pinterest: 4:5 format
        """
        out_dir = os.path.join(Config.JOBS_DIR, "social_clips")
        os.makedirs(out_dir, exist_ok=True)

        filename = os.path.basename(source).replace("_draft.mp4", "")
        out_path  = os.path.join(out_dir, f"{filename}_{platform}.mp4")

        # Platform formatları
        if platform in ("instagram", "tiktok"):
            scale   = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            bitrate = "2M"
        elif platform == "pinterest":
            scale   = "scale=1080:1350:force_original_aspect_ratio=increase,crop=1080:1350"
            bitrate = "1M"
        else:
            scale   = "scale=1280:720"
            bitrate = "2M"

        cmd = [
            "ffmpeg", "-y",
            "-i", source,
            "-t", str(duration),         # clip duration
            "-vf", scale,
            "-b:v", bitrate,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",   # web streaming optimization
            out_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return out_path
            log.error(f"FFmpeg clip error ({platform}): {result.stderr[-300:]}")
            return None
        except Exception as e:
            log.error(f"Clip production failed ({platform}): {e}")
            return None

    # ════════════════════════════════════════════════════════════
    # PİPELİNE 2: SHOPİFY — Ürün tanıtım içeriği
    # ════════════════════════════════════════════════════════════

    async def produce_shopify_content(
        self,
        product: Dict,
        job_id: str,
        telegram_handler=None,
    ) -> Optional[str]:
        """
        Shopify'dan gelen ürün verisiyle sosyal medya içeriği üretir.
        n8n'den /webhook/shopify üzerinden tetiklenir.

        Adımlar:
        1. Ürün görselini al (Shopify'dan veya Pexels'tan)
        2. Görsel üzerine ürün bilgisi yaz (Pillow)
        3. 15 sn kısa video üret (FFmpeg)
        4. Telegram'a onay için gönder
        5. Onay sonrası Instagram + Pinterest'e yayınla (auto_post: False)
        """
        pipeline  = Config.SOCIAL_PIPELINES["social_shopify"]
        log.info(f"Shopify content production: {product.get('title')}")

        out_dir  = os.path.join(Config.JOBS_DIR, job_id)
        os.makedirs(out_dir, exist_ok=True)

        # 1. Ürün kartı görseli oluştur
        card_path = self._create_product_card(product, out_dir)

        # 2. Kısa video üret
        video_path = self._image_to_video(card_path, out_dir, job_id, duration=15)

        # 3. Telegram onayına gönder
        if telegram_handler and video_path:
            await telegram_handler.send_message(
                f"🛍️ <b>Shopify Ürün İçeriği Hazır</b>\n\n"
                f"Ürün: <b>{product.get('title')}</b>\n"
                f"Fiyat: ${product.get('price', 'N/A')}\n"
                f"Platformlar: Instagram · Pinterest\n\n"
                f"Onaylar mısınız? (✅ Yayınla / ❌ İptal)"
            )

        return video_path

    def _create_product_card(self, product: Dict, out_dir: str) -> str:
        """Ürün bilgilerini içeren görsel kart oluştur (Pillow)."""
        from PIL import Image, ImageDraw, ImageFont

        img  = Image.new("RGB", (1080, 1080), "#1A1A2E")
        draw = ImageDraw.Draw(img)

        # Accent bar
        draw.rectangle([0, 0, 8, 1080], fill="#E94560")

        # Ürün adı
        title = product.get("title", "Product")[:50]
        price = f"${product.get('price', '')}"

        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
        except Exception:
            font_large = font_small = ImageFont.load_default()

        draw.text((80, 380), title, fill="white",   font=font_large)
        draw.text((80, 480), price, fill="#E94560", font=font_large)
        draw.text((80, 960), "MINDFULLY BRAND",    fill="#666666", font=font_small)

        out_path = os.path.join(out_dir, "product_card.jpg")
        img.save(out_path, "JPEG", quality=95)
        return out_path

    def _image_to_video(self, image_path: str, out_dir: str,
                        job_id: str, duration: int = 15) -> Optional[str]:
        """Görselden kısa video üret (ken-burns efekti ile)."""
        out_path = os.path.join(out_dir, f"{job_id}_shopify_social.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", f"scale=1080:1080,zoompan=z='min(zoom+0.0015,1.5)':d={duration*25}:s=1080x1080",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            out_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                log.info(f"Shopify social video: {out_path}")
                return out_path
            log.error(f"Shopify video error: {result.stderr[-300:]}")
            return None
        except Exception as e:
            log.error(f"Shopify video failed: {e}")
            return None


# ════════════════════════════════════════════════════════════════
# SOCIAL PUBLISHER — Platform'lara yayın
# ════════════════════════════════════════════════════════════════

class SocialPublisher:
    """
    Platform API'larına içerik yayınlar.
    Sadece organik paylaşım — reklam API'si yok.
    """

    async def publish(self, video_path: str, caption: str,
                      platforms: List[str]) -> Dict[str, bool]:
        results = {}
        for platform in platforms:
            if platform == "instagram":
                results["instagram"] = await self._post_instagram(video_path, caption)
            elif platform == "tiktok":
                results["tiktok"] = await self._post_tiktok(video_path, caption)
            elif platform == "pinterest":
                results["pinterest"] = await self._post_pinterest(video_path, caption)
        return results

    async def _post_instagram(self, video_path: str, caption: str) -> bool:
        if not Config.INSTAGRAM_ACCESS_TOKEN:
            log.warning("Instagram token not configured")
            return False
        try:
            import requests
            # Instagram Graph API — video upload (2-step)
            # Step 1: Create container
            resp = requests.post(
                f"https://graph.facebook.com/v18.0/{Config.INSTAGRAM_BUSINESS_ID}/media",
                params={
                    "access_token": Config.INSTAGRAM_ACCESS_TOKEN,
                    "media_type":   "REELS",
                    "caption":      caption[:2200],
                }
            )
            container_id = resp.json().get("id")
            if not container_id:
                return False
            # Step 2: Publish
            pub = requests.post(
                f"https://graph.facebook.com/v18.0/{Config.INSTAGRAM_BUSINESS_ID}/media_publish",
                params={"access_token": Config.INSTAGRAM_ACCESS_TOKEN,
                        "creation_id": container_id}
            )
            success = "id" in pub.json()
            log.info(f"Instagram post: {'✅' if success else '❌'}")
            return success
        except Exception as e:
            log.error(f"Instagram post failed: {e}")
            return False

    async def _post_tiktok(self, video_path: str, caption: str) -> bool:
        if not Config.TIKTOK_ACCESS_TOKEN:
            log.warning("TikTok token not configured")
            return False
        log.info("TikTok post: API integration placeholder — implement when Phase 2+ active")
        return False

    async def _post_pinterest(self, video_path: str, caption: str) -> bool:
        if not Config.PINTEREST_ACCESS_TOKEN:
            log.warning("Pinterest token not configured")
            return False
        try:
            import requests
            resp = requests.post(
                "https://api.pinterest.com/v5/pins",
                headers={"Authorization": f"Bearer {Config.PINTEREST_ACCESS_TOKEN}"},
                json={
                    "board_id":   Config.PINTEREST_BOARD_ID,
                    "title":      caption[:100],
                    "description": caption[:500],
                    "media_source": {"source_type": "video_id"},
                }
            )
            success = resp.status_code in (200, 201)
            log.info(f"Pinterest post: {'✅' if success else '❌'}")
            return success
        except Exception as e:
            log.error(f"Pinterest post failed: {e}")
            return False
