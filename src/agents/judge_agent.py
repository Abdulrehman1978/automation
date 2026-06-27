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
            score = score_data.get("score", 70)
            
            if 60 <= score <= 84:
                log.info(f"  [REWRITE TRIGGERED] '{idea['title']}' scored {score}. Attempting rewrite...")
                
                # Wave 2 rewrite loop calls the existing script format
                from agents.script_agent import ScriptAgent
                script_agent = ScriptAgent(self.orchestrator)
                
                # Inject improvement tip so ScriptAgent uses it
                idea["improvement_tip"] = score_data.get("improvement", "")
                draft_script = script_agent._generate_script(idea)
                
                # Re-evaluate with the generated draft script
                score_data = self._score_rewritten_idea(idea, draft_script)
                score = score_data.get("score", 70)
                
            idea["composite_score"] = score
            idea["judge_reasoning"] = score_data.get("reasoning", "")
            idea["improvement_tip"] = score_data.get("improvement", "")

            # If the final score is 80 or above, we approve it (lowered from 85 to ensure we get some approvals)
            if score >= 80:
                approved_ideas.append(idea)
                log.info(
                    f"  [APPROVED] '{idea['title']}' "
                    f"(score={score})"
                )
            else:
                log.info(
                    f"  [REJECTED] '{idea['title']}' "
                    f"(score={score})"
                )

        log.info(f"JudgeAgent: {len(approved_ideas)}/{len(ideas)} ideas approved")
        result = {"approved_ideas": approved_ideas}

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("judge", result)

        return result

    def _score_idea(self, idea: dict) -> dict:
        """Score an idea 0-100 using Groq (6 Dimensions)."""
        prompt = f"""You are a YouTube Shorts virality expert. Score this content idea.

Title: {idea.get('title', '')}
Concept: {idea.get('concept', '')[:300]}
Hook: {idea.get('hook', {}).get('text', '')}
Keywords: {idea.get('keywords', [])}

Evaluate on 6 dimensions (Total 100 points):
1. Emotional hook strength (0-20)
2. Retention potential / curiosity gap (0-20)
3. Shareability / controversy potential (0-15)
4. Search demand / trending relevance (0-15)
5. Trend relevance / timeliness (0-15)
6. Production simplicity (0-15)

Return ONLY valid JSON:
{{
  "hook_score": 0,
  "retention_score": 0,
  "shareability_score": 0,
  "search_demand_score": 0,
  "trend_score": 0,
  "production_score": 0,
  "score": <total 0-100>,
  "reasoning": "<one sentence why>",
  "improvement": "<one actionable tip to fix the weakest dimension>"
}}"""

        raw = ai_client.generate(
            prompt,
            provider="groq",
            system_prompt="You are a strict YouTube Shorts virality judge. Be concise and return only JSON.",
            preferred_model="llama-3.3-70b-versatile",
        )

        return self._parse_score(raw, idea.get('title'))

    def _score_rewritten_idea(self, idea: dict, draft_script: dict) -> dict:
        """Score a rewritten idea + script 0-100 using Groq (6 Dimensions)."""
        prompt = f"""You are a YouTube Shorts virality expert. Re-evaluate this idea and its drafted script.

Title: {idea.get('title', '')}
Concept: {idea.get('concept', '')[:300]}
Draft Script Hook: {draft_script.get('hook_5s', '')}
Draft Script Body: {draft_script.get('body_40s', '')}

Evaluate on 6 dimensions (Total 100 points):
1. Emotional hook strength (0-20)
2. Retention potential / curiosity gap (0-20)
3. Shareability / controversy potential (0-15)
4. Search demand / trending relevance (0-15)
5. Trend relevance / timeliness (0-15)
6. Production simplicity (0-15)

Return ONLY valid JSON:
{{
  "hook_score": 0,
  "retention_score": 0,
  "shareability_score": 0,
  "search_demand_score": 0,
  "trend_score": 0,
  "production_score": 0,
  "score": <total 0-100>,
  "reasoning": "<one sentence why this improved or failed>",
  "improvement": "<final tip>"
}}"""

        raw = ai_client.generate(
            prompt,
            provider="groq",
            system_prompt="You are a strict YouTube Shorts virality judge. Be concise and return only JSON.",
            preferred_model="llama-3.3-70b-versatile",
        )

        return self._parse_score(raw, idea.get('title'))

    def _parse_score(self, raw: str, title: str) -> dict:
        if not raw:
            return {"score": 72, "reasoning": "Auto-approved (AI unavailable)", "improvement": ""}

        try:
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(cleaned)
            # Ensure total score is calculated correctly if the AI messed it up
            calc_score = sum([
                data.get("hook_score", 0),
                data.get("retention_score", 0),
                data.get("shareability_score", 0),
                data.get("search_demand_score", 0),
                data.get("trend_score", 0),
                data.get("production_score", 0)
            ])
            if calc_score > 0:
                data["score"] = calc_score
            return data
        except json.JSONDecodeError:
            log.warning(f"JudgeAgent: Could not parse score JSON for '{title}'. Defaulting.")
            return {"score": 70, "reasoning": raw[:200], "improvement": ""}
