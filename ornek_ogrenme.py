"""
ornek_ogrenme.py — Phase 2.5+
───────────────────────────────
Phase 2.5: Tracks which title/heading styles you kept vs. edited.
           Builds a simple JSON style profile.
Phase 3+:  Adds Ollama-based diff analysis for deeper preference learning.

DO NOT build complex ML here — keep Phase 2.5 simple and working.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from utils.logger import get_logger

log = get_logger("ornek_ogrenme")

PROFILE_PATH = "/app/backups/style_profile.json"


class OrnekOgrenme:

    # ── Phase 2.5: Simple title style tracking ───────────────────
    def record_edit(
        self,
        job_id: str,
        original_title: str,
        edited_title: str,
        original_outline: List[str],
        edited_outline: List[str],
    ):
        """Record that you edited a title/outline. Updates style profile."""
        profile = self._load_profile()

        # Track whether you shortened, lengthened, or kept the title
        orig_len = len(original_title)
        edit_len = len(edited_title)
        if edit_len < orig_len * 0.8:
            action = "shortened"
        elif edit_len > orig_len * 1.2:
            action = "lengthened"
        else:
            action = "kept"

        profile["title_edits"].append({
            "job_id":   job_id,
            "action":   action,
            "orig_len": orig_len,
            "edit_len": edit_len,
            "date":     datetime.utcnow().isoformat(),
        })

        # Track outline point count preference
        orig_count = len(original_outline)
        edit_count = len(edited_outline)
        profile["outline_preferences"].append({
            "job_id":     job_id,
            "orig_points": orig_count,
            "kept_points": edit_count,
        })

        # Derive simple preferences
        if len(profile["title_edits"]) >= 5:
            actions = [e["action"] for e in profile["title_edits"][-10:]]
            profile["preferred_title_length"] = max(set(actions), key=actions.count)

        if len(profile["outline_preferences"]) >= 5:
            kept_counts = [p["kept_points"] for p in profile["outline_preferences"][-10:]]
            profile["preferred_outline_points"] = round(sum(kept_counts) / len(kept_counts))

        profile["last_updated"] = datetime.utcnow().isoformat()
        self._save_profile(profile)
        log.info(f"Style edit recorded for job {job_id}: title action={action}")

    def get_style_hints(self, influence: float = 0.35) -> Dict:
        """
        Return current style preferences for AI prompts.

        influence: referansın ne kadar ağırlık taşıyacağı (varsayılan %35)
        Döndürülen hint'ler bu ağırlıkla prompt'a eklenir.
        """
        profile = self._load_profile()
        hints   = {}

        if pref := profile.get("preferred_title_length"):
            hints["title_length"] = pref
        if pref := profile.get("preferred_outline_points"):
            hints["outline_points"] = pref

        # Etki katsayısını hint'e göm — ai_synthesizer bunu okur
        hints["_influence"]        = influence
        hints["_influence_label"]  = f"{int(influence*100)}% user preference weight"
        hints["_system_weight"]    = f"{int((1-influence)*100)}% system autonomous decision"

        return hints

    def get_style_prompt_fragment(self, influence: float = 0.35) -> str:
        """
        Stil tercihlerini doğrudan prompt'a eklenecek metin olarak döndür.
        %35 etkiyle — sistem kararını bozmadan hafif yönlendirir.
        """
        hints = self.get_style_hints(influence)
        if not hints.get("title_length") and not hints.get("outline_points"):
            return ""

        parts = []
        if tl := hints.get("title_length"):
            parts.append(f"title tends to be {tl}")
        if op := hints.get("outline_points"):
            parts.append(f"outline typically has {op} points")

        if not parts:
            return ""

        return (
            f"\n\n--- USER STYLE PREFERENCE ({int(influence*100)}% influence) ---\n"
            f"Based on past edits: {', '.join(parts)}.\n"
            f"Apply softly — system's own judgment ({int((1-influence)*100)}%) takes precedence.\n"
            f"--- END PREFERENCE ---"
        )

    # ── Phase 3+: Ollama diff analysis (placeholder) ─────────────
    def analyze_with_ollama(self, job_id: str, original: str, edited: str) -> Optional[Dict]:
        """
        Phase 3+: Use Ollama to understand WHY you made an edit.
        Returns inferred preferences as dict.
        Stub — implement when Phase 3 is active.
        """
        log.info(f"Ollama diff analysis requested for {job_id} — not yet implemented (Phase 3+)")
        return None


    # ── Referans görsel/video stil profili ───────────────────────
    def get_reference_style(self) -> dict:
        """
        Telegram'dan yüklenen referans görsel/video stil profilini döndürür.
        ai_synthesizer.py bu profili prompt'lara ekler.
        """
        REF_PATH = "/app/backups/reference_style_profile.json"
        import os
        if os.path.exists(REF_PATH):
            with open(REF_PATH) as f:
                return json.load(f)
        return {}

    def clear_reference_style(self):
        """Referans stil profilini temizle."""
        import os
        REF_PATH = "/app/backups/reference_style_profile.json"
        if os.path.exists(REF_PATH):
            os.remove(REF_PATH)

    # ── Profile I/O ──────────────────────────────────────────────
    def _load_profile(self) -> Dict:
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH) as f:
                return json.load(f)
        return {
            "title_edits":              [],
            "outline_preferences":      [],
            "preferred_title_length":   None,
            "preferred_outline_points": None,
            "last_updated":             None,
        }

    def _save_profile(self, profile: Dict):
        os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
        with open(PROFILE_PATH, "w") as f:
            json.dump(profile, f, indent=2)
