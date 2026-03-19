"""
blog_post_producer.py — Phase 2.5
───────────────────────────────────
Generates SEO-optimised blog posts via Ollama.
Output: HTML or Markdown file ready for WordPress/Ghost/static site.
"""
import os
from typing import Optional
from ai_synthesizer import AISynthesizer
from config import Config
from utils.logger import get_logger
from utils.helpers import safe_json_save

log = get_logger("blog_post_producer")


class BlogPostProducer:
    def __init__(self):
        self.ai = AISynthesizer()

    async def produce(
        self,
        topic: str,
        channel_id: str,
        job_id: str,
        word_count: int = 800,
        format: str = "html",   # "html" or "markdown"
    ) -> Optional[str]:
        """Generate blog post. Returns file path."""

        prompt = f"""Write a high-quality, SEO-optimized blog post.
Topic: {topic}
Word count: ~{word_count} words
Tone: informative, engaging, friendly
Include: introduction, 3-4 sections with H2 headings, conclusion, call-to-action

Respond ONLY with JSON:
{{
  "title": "SEO blog post title",
  "meta_description": "155-char meta description",
  "slug": "url-friendly-slug",
  "content_html": "full HTML content with <h2>, <p>, <ul> tags",
  "content_markdown": "full Markdown content",
  "tags": ["tag1", "tag2", "tag3"],
  "word_count": {word_count}
}}"""

        result = self.ai._call_ollama(prompt, model="qwen2.5:3b")
        if not result or "content_html" not in result:
            log.error(f"Blog post generation failed for: {topic}")
            return None

        out_dir = os.path.join(Config.JOBS_DIR, job_id)
        os.makedirs(out_dir, exist_ok=True)

        slug    = result.get("slug", "post")
        ext     = "html" if format == "html" else "md"
        content = result.get("content_html") if format == "html" else result.get("content_markdown", "")
        path    = os.path.join(out_dir, f"{slug}.{ext}")

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Save metadata
        safe_json_save(os.path.join(out_dir, "blog_metadata.json"), {
            "job_id":           job_id,
            "channel_id":       channel_id,
            "title":            result.get("title"),
            "meta_description": result.get("meta_description"),
            "slug":             slug,
            "tags":             result.get("tags", []),
            "word_count":       result.get("word_count", word_count),
            "file":             path,
        })
        log.info(f"Blog post: {path}")
        return path
