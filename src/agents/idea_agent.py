"""
Idea Agent
----------
Takes researched trends, deduplicates them, predicts lifetimes, then uses
Groq (fast) to generate rich content ideas with hook angles.
Also injects Learning Agent recommendations if available.
"""
import json
import logging
from .base_agent import BaseAgent
from utils.error_handler import safe_execute
from intelligence.trend_deduplicator import TrendDeduplicator
from intelligence.trend_lifetime import predict_lifetimes
from generation.hook_selector import HookSelector
from utils.ai_client import ai_client

log = logging.getLogger(__name__)


class IdeaAgent(BaseAgent):
    def __init__(self, orchestrator=None):
        super().__init__(orchestrator)
        self.deduplicator = TrendDeduplicator()
        self.hook_selector = HookSelector()

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("IdeaAgent starting...")
        raw_trends = context.get("research", {}).get("trends", [])
        learning_recs = context.get("learning", {}).get("recommendations", {})

        clusters = self.deduplicator.cluster(raw_trends)
        actionable = predict_lifetimes(clusters)

        # Pull strategy hints from Learning Agent if available
        best_hooks = learning_recs.get("best_hook_types", [])
        avoid_topics = learning_recs.get("avoid_topics", [])
        style_tips = learning_recs.get("script_style_tips", [])

        ideas = []
        for trend in actionable:
            topic = trend["master_topic"]

            # Skip topics the Learning Agent flagged as poor performers
            if any(avoid in topic.lower() for avoid in [t.lower() for t in avoid_topics]):
                log.info(f"  Skipping '{topic}' (Learning Agent flagged as low performer)")
                continue

            idea = self._generate_idea(topic, best_hooks, style_tips)
            ideas.append(idea)

        log.info(f"IdeaAgent generated {len(ideas)} ideas")
        result = {"ideas": ideas}

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("idea", result)

        return result

    def _generate_idea(self, topic: str, best_hooks: list, style_tips: list) -> dict:
        """Use Groq to generate a rich content idea for a topic."""
        hook_hint = f"Prefer these hook styles: {best_hooks}" if best_hooks else ""
        style_hint = f"Style tips: {'; '.join(style_tips)}" if style_tips else ""

        prompt = f"""You are a YouTube Shorts content strategist.

Create a viral content idea for this trending topic: "{topic}"
{hook_hint}
{style_hint}

Return ONLY valid JSON:
{{
  "title": "<catchy title under 60 chars>",
  "concept": "<2-3 sentence video concept>",
  "hook_line": "<opening hook sentence that stops the scroll>",
  "angle": "<unique angle or perspective>",
  "keywords": ["kw1", "kw2", "kw3"],
  "category": "<niche category>"
}}"""

        raw = ai_client.generate(
            prompt,
            provider="groq",
            system_prompt="You are a viral content expert. Return only JSON, no markdown.",
            preferred_model="llama-3.1-8b-instant",
        )

        if raw:
            try:
                cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(cleaned)
                hook_obj = self.hook_selector.get_random_hook(topic)
                data["hook"] = hook_obj
                data["topic_source"] = topic
                return data
            except json.JSONDecodeError:
                log.warning(f"IdeaAgent: JSON parse failed for '{topic}', using template.")

        # Fallback template
        hook_obj = self.hook_selector.get_random_hook(topic)
        return {
            "title": f"The Truth About {topic}",
            "concept": f"An eye-opening look at {topic} that most people don't know.",
            "hook_line": f"Did you know {topic} could change everything?",
            "angle": "Surprising facts",
            "keywords": [topic, "viral", "shorts"],
            "category": "Tech",
            "hook": hook_obj,
            "topic_source": topic,
        }
