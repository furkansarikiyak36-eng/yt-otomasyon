"""
image_to_video_converter.py — Phase 2.5
─────────────────────────────────────────
Converts static images to short video clips.
Uses FFmpeg with ken-burns zoom/pan effect.
Used for: product cards, quote cards, infographic animations.
"""
import os
import subprocess
from typing import Optional, List
from config import Config
from utils.logger import get_logger

log = get_logger("image_to_video_converter")


class ImageToVideoConverter:

    def convert(
        self,
        image_path: str,
        out_dir: str,
        duration: int = 15,
        effect: str = "zoom_in",   # zoom_in | zoom_out | pan_right | pan_left | static
        output_size: str = "1080x1080",  # 1080x1080 | 1920x1080 | 1080x1920
    ) -> Optional[str]:
        """Convert a single image to a video clip."""
        os.makedirs(out_dir, exist_ok=True)
        fname    = os.path.splitext(os.path.basename(image_path))[0]
        out_path = os.path.join(out_dir, f"{fname}_{effect}.mp4")

        w, h  = output_size.split("x")
        fps   = 30
        total = duration * fps

        effects = {
            "zoom_in":    f"scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':d={total}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={output_size}",
            "zoom_out":   f"scale=8000:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={total}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={output_size}",
            "pan_right":  f"scale=-1:{h},crop={w}:{h}:'min(iw-{w},t/{duration}*(iw-{w}))':0",
            "pan_left":   f"scale=-1:{h},crop={w}:{h}:'max(0,(iw-{w})-(t/{duration}*(iw-{w})))':0",
            "static":     f"scale={output_size}:force_original_aspect_ratio=decrease,pad={output_size}:(ow-iw)/2:(oh-ih)/2",
        }

        vf = effects.get(effect, effects["zoom_in"])

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-movflags", "+faststart",
            out_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                log.info(f"Image→video: {out_path} ({effect}, {duration}s)")
                return out_path
            log.error(f"FFmpeg error: {result.stderr[-300:]}")
            return None
        except Exception as e:
            log.error(f"Conversion error: {e}")
            return None

    def batch_convert(
        self,
        image_paths: List[str],
        out_dir: str,
        duration: int = 10,
        effect: str = "zoom_in",
    ) -> List[str]:
        """Convert multiple images. Returns list of output paths."""
        outputs = []
        for img in image_paths:
            out = self.convert(img, out_dir, duration, effect)
            if out:
                outputs.append(out)
        return outputs

    def slideshow(
        self,
        image_paths: List[str],
        out_dir: str,
        seconds_per_image: int = 5,
        transition: bool = True,
        audio_path: str = None,
    ) -> Optional[str]:
        """Create a slideshow video from multiple images."""
        if not image_paths:
            return None

        # Create individual clips
        clips = self.batch_convert(image_paths, out_dir, seconds_per_image, "zoom_in")
        if not clips:
            return None

        # Concat all clips
        concat_file = os.path.join(out_dir, "slideshow_concat.txt")
        with open(concat_file, "w") as f:
            for c in clips:
                f.write(f"file '{c}'\n")

        out_path = os.path.join(out_dir, "slideshow.mp4")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file]

        if audio_path and os.path.exists(audio_path):
            cmd += ["-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest"]
        else:
            cmd += ["-c", "copy"]

        cmd.append(out_path)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                log.info(f"Slideshow: {out_path}")
                return out_path
            return None
        except Exception as e:
            log.error(f"Slideshow error: {e}")
            return None
