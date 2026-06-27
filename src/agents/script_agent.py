"""
Script Agent
------------
Expands approved ideas into full 60-second YouTube Shorts scripts using Groq.
Outputs: narration, visual cues, b-roll suggestions, and CTA.
"""
import json
import logging
from .base_agent import BaseAgent
from utils.error_handler import safe_execute
from utils.ai_client import ai_client

log = logging.getLogger(__name__)


class ScriptAgent(BaseAgent):

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("ScriptAgent starting...")
        ideas = context.get("judge", {}).get("approved_ideas", [])

        scripts = []
        for idea in ideas:
            script = self._generate_script(idea)
            scripts.append(script)

        log.info(f"ScriptAgent generated {len(scripts)} scripts")
        result = {"scripts": scripts}

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("script", result)

        return result

    def _generate_script(self, idea: dict) -> dict:
        title = idea.get("title", "Unknown")
        concept = idea.get("concept", "")
        
        hook_obj = idea.get("hook", {})
        hook_type = hook_obj.get("type", "curiosity")
        
        from generation.hook_selector import HookSelector
        hook_selector = HookSelector()
        best_hook = hook_selector.get_hook_by_type(title, hook_type)
        
        hook_line = idea.get("hook_line", best_hook.get("text", ""))
        angle = idea.get("angle", "")

        prompt = f"""Write a punchy 60-second YouTube Shorts script with strict 60-second pacings.

Title: {title}
Concept: {concept}
Opening hook: {hook_line}
Hook Type: {hook_type}
Angle: {angle}
Judge feedback: {idea.get('improvement_tip', '')}

Return ONLY valid JSON:
{{
  "hook_0_to_5s": "<first 5 seconds — must hook instantly using the {hook_type} hook>",
  "setup_5_to_15s": "<context and setup>",
  "body_15_to_45s": "<main content in 3-4 punchy sentences>",
  "climax_45_to_55s": "<the big reveal or payoff>",
  "cta_55_to_60s": "<call to action — subscribe/comment prompt>",
  "full_narration": "<complete script stitched together>",
  "visual_cues": ["<scene 1 description>", "<scene 2>", "<scene 3>"],
  "broll_suggestions": ["<b-roll clip idea 1>", "<b-roll clip idea 2>"],
  "estimated_duration_sec": 60
}}"""

        raw = ai_client.generate(
            prompt,
            provider="groq",
            system_prompt="You are an expert YouTube Shorts scriptwriter. Return only JSON.",
            preferred_model="llama-3.3-70b-versatile",
        )

        if raw:
            try:
                cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(cleaned)
                data["idea_ref"] = title
                return data
            except json.JSONDecodeError:
                log.warning(f"ScriptAgent: JSON parse failed for '{title}'")

        # Fallback template
        return {
            "idea_ref": title,
            "hook_0_to_5s": hook_line or f"Did you know about {title}?",
            "setup_5_to_15s": f"Here is the context for {title}.",
            "body_15_to_45s": concept or f"Here is everything you need to know about {title}.",
            "climax_45_to_55s": "And that is why it is so important.",
            "cta_55_to_60s": "Drop a comment below and subscribe for more!",
            "full_narration": f"{hook_line}\n\n{concept}\n\nLike and subscribe for more!",
            "visual_cues": ["Show text overlay", "Fast cut to relevant footage", "End card"],
            "broll_suggestions": [f"{title} stock footage", "Reaction clip"],
            "estimated_duration_sec": 60,
        }
