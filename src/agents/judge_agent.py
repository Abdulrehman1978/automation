"""
Judge Agent
-----------
Uses Groq (fast LLM) to score ideas on virality potential and filter out weak ones.
Applies a composite score threshold before passing ideas downstream.
"""
import json
import logging
from .base_agent import BaseAgent
from utils.error_handler import safe_execute
from utils.ai_client import ai_client

log = logging.getLogger(__name__)

APPROVE_THRESHOLD = 65  # Minimum score to pass to script generation


class JudgeAgent(BaseAgent):

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("JudgeAgent starting...")
        ideas = context.get("idea", {}).get("ideas", [])
        approved_ideas = []

        for idea in ideas:
            score_data = self._score_idea(idea)
            idea["composite_score"] = score_data.get("score", 70)
            idea["judge_reasoning"] = score_data.get("reasoning", "")
            idea["improvement_tip"] = score_data.get("improvement", "")

            if idea["composite_score"] >= APPROVE_THRESHOLD:
                approved_ideas.append(idea)
                log.info(
                    f"  [APPROVED] '{idea['title']}' "
                    f"(score={idea['composite_score']})"
                )
            else:
                log.info(
                    f"  [REJECTED] '{idea['title']}' "
                    f"(score={idea['composite_score']} < {APPROVE_THRESHOLD})"
                )

        log.info(f"JudgeAgent: {len(approved_ideas)}/{len(ideas)} ideas approved")
        result = {"approved_ideas": approved_ideas}

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("judge", result)

        return result

    def _score_idea(self, idea: dict) -> dict:
        """Score an idea 0-100 using Groq."""
        prompt = f"""You are a YouTube Shorts virality expert. Score this content idea.

Title: {idea.get('title', '')}
Concept: {idea.get('concept', '')[:300]}
Hook: {idea.get('hook', {}).get('text', '')}
Keywords: {idea.get('keywords', [])}

Evaluate on:
- Emotional hook strength (0-25)
- Shareability / controversy potential (0-25)
- Search demand / trending relevance (0-25)
- Production simplicity (0-25)

Return ONLY valid JSON:
{{
  "score": <total 0-100>,
  "reasoning": "<one sentence why>",
  "improvement": "<one actionable tip>"
}}"""

        raw = ai_client.generate(
            prompt,
            provider="groq",
            system_prompt="You are a strict YouTube Shorts virality judge. Be concise and return only JSON.",
            preferred_model="llama-3.3-70b-versatile",
        )

        if not raw:
            # Fallback: auto-approve with default score
            return {"score": 72, "reasoning": "Auto-approved (AI unavailable)", "improvement": ""}

        try:
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            log.warning(f"JudgeAgent: Could not parse score JSON for '{idea.get('title')}'. Defaulting.")
            return {"score": 70, "reasoning": raw[:200], "improvement": ""}
