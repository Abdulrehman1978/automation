"""
Learning Agent
--------------
Analyses historical performance data from the Knowledge Base and uses
Gemini to produce actionable strategy recommendations that get injected
into subsequent pipeline runs (idea scoring, hook selection, scripting).

This is a *post-run* agent — it runs after a batch of videos has been
published and their analytics are available.
"""

import json
import logging
from agents.base_agent import BaseAgent
from intelligence.knowledge_base import knowledge_base
from utils.ai_client import ai_client
from utils.error_handler import safe_execute

log = logging.getLogger(__name__)


class LearningAgent(BaseAgent):

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("LearningAgent starting analysis...")

        # ------------------------------------------------------------------ #
        # 1. Gather performance context from the Knowledge Base               #
        # ------------------------------------------------------------------ #
        strategy_ctx = knowledge_base.build_strategy_context()
        
        # Check minimum data thresholds (min 5 videos with views > 0)
        total_valid = strategy_ctx.get('total_valid_videos', 0)
        if total_valid < 5:
            log.info(f"LearningAgent skipped: Insufficient data ({total_valid}/5 videos required).")
            result = {"status": "insufficient_data", "reason": f"Only {total_valid} valid videos tracked"}
            if self.orchestrator:
                self.orchestrator.checkpoint.mark_step_done("learning", result)
            return result
            
        recent_records = knowledge_base.get_recent_performance(days=30, limit=20)
        top_hooks = knowledge_base.get_top_performing_hooks(limit=5)
        experiments = knowledge_base.get_experiment_history(limit=10)

        log.info(
            f"  Context: {strategy_ctx['total_videos_tracked']} videos tracked, "
            f"avg views={strategy_ctx['avg_views_last_14d']}"
        )

        # ------------------------------------------------------------------ #
        # 2. Ask Gemini for recommendations                                   #
        # ------------------------------------------------------------------ #
        prompt = self._build_analysis_prompt(
            strategy_ctx, recent_records, top_hooks, experiments, context
        )
        raw_response = ai_client.generate(prompt)

        recommendations = self._parse_recommendations(raw_response)
        
        confidence = recommendations.get("confidence", 0.0)
        if confidence < 0.60:
            log.warning(f"LearningAgent recommendations rejected: confidence too low ({confidence}).")
            result = {"status": "insufficient_data", "reason": f"Confidence {confidence} below threshold 0.60"}
            if self.orchestrator:
                self.orchestrator.checkpoint.mark_step_done("learning", result)
            return result

        # ------------------------------------------------------------------ #
        # 3. Persist recommended strategy updates back to KB                  #
        # ------------------------------------------------------------------ #
        if recommendations.get("best_hook_types"):
            log.info(f"  Recommended hooks: {recommendations['best_hook_types']}")
        if recommendations.get("avoid_topics"):
            log.info(f"  Topics to avoid: {recommendations['avoid_topics']}")

        result = {
            "recommendations": recommendations,
            "strategy_context": strategy_ctx,
            "analysis_summary": recommendations.get("summary", "No summary available."),
        }

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("learning", result)

        log.info("LearningAgent complete.")
        return result

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _build_analysis_prompt(
        self,
        strategy_ctx: dict,
        recent_records: list,
        top_hooks: list,
        experiments: list,
        pipeline_context: dict,
    ) -> str:
        channel_id = pipeline_context.get("channel_id", "unknown")

        top_hook_str = (
            ", ".join(h.get("hook_type", "N/A") for h in top_hooks)
            if top_hooks else "No data yet"
        )
        recent_str = (
            "\n".join(
                f"  - '{r.get('title', 'N/A')}' | views={r.get('views', 0)} "
                f"| hook={r.get('hook_type', 'N/A')}"
                for r in recent_records[:10]
            )
            if recent_records else "  No recent videos."
        )
        experiment_str = (
            "\n".join(
                f"  - {e.get('name', 'N/A')}: winner={e.get('winner', 'TBD')} "
                f"(confidence={e.get('confidence', 0):.0%})"
                for e in experiments[:5]
            )
            if experiments else "  No experiments run yet."
        )

        return f"""You are the strategy intelligence layer of a YouTube Shorts content system for channel "{channel_id}".

## Performance Data (last 30 days)
- Videos tracked: {strategy_ctx['total_videos_tracked']}
- Average views: {strategy_ctx['avg_views_last_14d']:,.0f}
- Top performing hook types: {top_hook_str}

## Recent Video Performance
{recent_str}

## A/B Experiment History
{experiment_str}

## Task
Based on the data above, produce a JSON strategy recommendation with exactly these keys:
{{
  "summary": "2-3 sentence plain-English summary of what's working",
  "confidence": 0.85,
  "best_hook_types": ["list", "of", "hook", "types", "to", "prioritise"],
  "avoid_topics": ["topics", "performing", "poorly"],
  "recommended_posting_frequency": "e.g. 2x per day",
  "script_style_tips": ["tip1", "tip2"],
  "next_experiment_suggestion": "one sentence A/B test idea"
}}

Return ONLY valid JSON. No markdown fences."""

    def _parse_recommendations(self, raw: str) -> dict:
        """Safely parse the JSON response from Gemini."""
        if not raw:
            return {"summary": "Insufficient data for analysis."}
        try:
            # Strip any accidental markdown fences
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            log.warning("Could not parse LearningAgent JSON response — returning raw.")
            return {"summary": raw[:500]}
