"""
strategy_engine.py — Phase 5
──────────────────────────────
AI-driven strategic content planning.
Generates a full weekly content calendar for all 3 channels.
Sends to Telegram for one-tap approval.
After approval, schedules production jobs automatically.
"""
from typing import Dict, List
from datetime import datetime, timedelta
from ai_synthesizer import AISynthesizer
from sheets_manager import SheetsManager
from config import Config
from utils.logger import get_logger

log = get_logger("strategy_engine")


class StrategyEngine:
    def __init__(self, telegram_handler=None):
        self.tg     = telegram_handler
        self.ai     = AISynthesizer(telegram_handler)
        self.sheets = SheetsManager()

    async def generate_weekly_plan(self, job_id: str) -> Dict:
        """
        Generate a full weekly content plan for all channels.
        Returns plan dict. Sends to Telegram for approval.
        """
        # Gather context
        trends   = self.sheets.read_all(Config.SHEETS_TREND_DATA)
        top10    = sorted(trends, key=lambda x: int(x.get("popularity",0)), reverse=True)[:10]
        trend_ctx = [f"{t.get('topic')} ({t.get('popularity')}/100)" for t in top10]

        sales    = self.sheets.read_all(Config.SHEETS_SALES)
        best_products = sorted(sales, key=lambda x: float(x.get("amount",0)), reverse=True)[:3]
        prod_ctx = [s.get("product","") for s in best_products]

        channels = Config.CHANNELS
        next_mon = datetime.utcnow() + timedelta(days=(7 - datetime.utcnow().weekday()))

        prompt = f"""You are a content strategy AI for MINDFULLY BRAND YouTube channels.
Today: {datetime.utcnow().strftime('%Y-%m-%d')}
Week starting: {next_mon.strftime('%Y-%m-%d')}

Top trending topics: {', '.join(trend_ctx[:5])}
Best-selling products: {', '.join(prod_ctx)}

Channels:
- Mindfully Ambiance (ambiance): 30-60 min lofi/relaxing music loops (Tue/Thu/Sat 18:00)
- Mindfully Fitness (fitness): yoga/workout/HIIT tutorials (Mon/Wed/Fri 09:00)
- Mindfully Docs (documentary): food/science/history documentaries (Sun 14:00)

Generate a complete weekly content plan. Respond ONLY with JSON:
{{
  "week_of": "{next_mon.strftime('%Y-%m-%d')}",
  "plan": [
    {{
      "channel_id": "channel_ambiance",
      "channel_name": "Mindfully Ambiance",
      "publish_day": "tuesday",
      "publish_time": "18:00",
      "title": "video title",
      "mood": "lofi|relaxing|motivational|sleep|study|focus",
      "animation": "particles|waves|starfield|aurora|gradient",
      "duration_min": 30,
      "priority": 1,
      "reason": "why this topic now"
    }}
  ],
  "weekly_email_topic": "email newsletter topic for this week",
  "featured_product": "which product to promote",
  "strategic_note": "1-sentence strategy note for the week"
}}"""

        result = self.ai._call_ollama(prompt, model="qwen2.5:3b")
        plan = result.get("plan", [])
        if not plan:
            log.error("Strategy engine returned empty plan")
            plan = self._fallback_plan(next_mon)

        full_plan = {
            "week_of":          result.get("week_of", next_mon.strftime('%Y-%m-%d')),
            "plan":             plan,
            "weekly_email":     result.get("weekly_email_topic", ""),
            "featured_product": result.get("featured_product", ""),
            "strategic_note":   result.get("strategic_note", ""),
            "approved":         False,
        }

        # Send to Telegram for approval
        if self.tg:
            msg = self._format_plan_message(full_plan)
            await self.tg.send_message(msg)
            action = await self.tg._wait_for_callback(job_id)
            full_plan["approved"] = (action == "continue")
            if full_plan["approved"]:
                await self._schedule_production(full_plan)
                await self.tg.send_message("✅ Weekly plan approved — production jobs queued.")
            else:
                await self.tg.send_message("❌ Weekly plan rejected. Generate a new plan with /report weekly")

        # Save to content_calendar
        self._save_to_calendar(full_plan)
        log.info(f"Weekly plan generated: {len(plan)} videos | approved={full_plan['approved']}")
        return full_plan

    def _fallback_plan(self, start: datetime) -> List[Dict]:
        """Default plan if AI fails."""
        return [
            {"channel_id": "channel_ambiance",    "channel_name": "Mindfully Ambiance",   "publish_day": "tuesday",   "publish_time": "18:00", "title": "Lofi Study Music 30 Minutes",       "mood": "study",    "animation": "particles", "duration_min": 30, "priority": 1, "reason": "default"},
            {"channel_id": "channel_fitness",     "channel_name": "Mindfully Fitness",    "publish_day": "monday",    "publish_time": "09:00", "title": "10 Minute Morning Yoga for Beginners","mood": "energetic","animation": "none",      "duration_min": 10, "priority": 1, "reason": "default"},
            {"channel_id": "channel_documentary", "channel_name": "Mindfully Docs",       "publish_day": "sunday",    "publish_time": "14:00", "title": "History of Coffee Documentary",      "mood": "cinematic","animation": "none",      "duration_min": 25, "priority": 1, "reason": "default"},
            {"channel_id": "channel_ambiance",    "channel_name": "Mindfully Ambiance",   "publish_day": "thursday",  "publish_time": "18:00", "title": "Relaxing Sleep Music 60 Minutes",   "mood": "sleep",    "animation": "starfield", "duration_min": 60, "priority": 2, "reason": "default"},
            {"channel_id": "channel_fitness",     "channel_name": "Mindfully Fitness",    "publish_day": "wednesday", "publish_time": "09:00", "title": "HIIT Workout No Equipment",          "mood": "energetic","animation": "none",      "duration_min": 15, "priority": 2, "reason": "default"},
        ]

    def _format_plan_message(self, plan: Dict) -> str:
        lines = [f"🗓 <b>Weekly Content Plan — {plan['week_of']}</b>\n"]
        if plan.get("strategic_note"):
            lines.append(f"<i>{plan['strategic_note']}</i>\n")

        for item in sorted(plan["plan"], key=lambda x: x.get("priority", 9)):
            day  = item.get("publish_day","").capitalize()
            time = item.get("publish_time","")
            ch   = item.get("channel_name","")
            title = item.get("title","")
            lines.append(f"📅 <b>{day} {time}</b> [{ch}]\n   {title}")

        if plan.get("weekly_email"):
            lines.append(f"\n📧 Email topic: {plan['weekly_email']}")
        if plan.get("featured_product"):
            lines.append(f"🛍️ Featured product: {plan['featured_product']}")

        lines.append("\nApprove this plan? ✅ Continue / ❌ Cancel")
        return "\n".join(lines)

    async def _schedule_production(self, plan: Dict):
        """Queue production jobs for approved plan items."""
        from workflow_manager import WorkflowManager
        wf = WorkflowManager()
        for item in plan["plan"]:
            job = wf.create_job(
                name=item["title"],
                job_type=item.get("channel_id","").replace("channel_",""),
                channel_id=item["channel_id"],
                metadata=item,
            )
            log.info(f"Production queued: {job.job_id} — {item['title']}")

    def _save_to_calendar(self, plan: Dict):
        for item in plan["plan"]:
            self.sheets.append_row(Config.SHEETS_CONTENT_CALENDAR, {
                "channel_id":   item.get("channel_id"),
                "channel_name": item.get("channel_name"),
                "date":         plan.get("week_of"),
                "time":         item.get("publish_time"),
                "topic":        item.get("title"),
                "video_type":   item.get("channel_id","").replace("channel_",""),
                "status":       "planned" if not plan.get("approved") else "approved",
                "notes":        item.get("reason",""),
            })
