"""
Experiment Agent
----------------
Uses Gemini to intelligently *design* A/B experiments based on current
performance gaps identified by the Learning Agent.

Integrates with the ExperimentEngine to register and assign experiments
to the next content batch.
"""

import json
import logging
from agents.base_agent import BaseAgent
from experiments.experiment_engine import experiment_engine
from utils.ai_client import ai_client
from utils.error_handler import safe_execute

log = logging.getLogger(__name__)

# Fallback experiments if Gemini doesn't respond
_DEFAULT_EXPERIMENTS = [
    {
        "name": "Hook Type: Question vs Shock",
        "variable": "hook_type",
        "variant_a": {"hook_type": "question"},
        "variant_b": {"hook_type": "shock"},
        "hypothesis": "Question hooks get more comments; shock hooks get more views.",
    },
    {
        "name": "Title Length: Short vs Descriptive",
        "variable": "title_length",
        "variant_a": {"title_style": "short", "max_words": 6},
        "variant_b": {"title_style": "descriptive", "max_words": 12},
        "hypothesis": "Short titles perform better on mobile discovery.",
    },
]


class ExperimentAgent(BaseAgent):

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("ExperimentAgent starting...")

        learning_data = context.get("learning", {})
        recommendations = learning_data.get("recommendations", {})
        strategy_ctx = learning_data.get("strategy_context", {})

        # Design experiments using AI
        designed = self._design_experiments(recommendations, strategy_ctx, context)

        # Register each experiment in the engine
        registered = []
        for exp_spec in designed[:2]:  # Run max 2 concurrent experiments
            try:
                experiment = experiment_engine.create_experiment(
                    name=exp_spec["name"],
                    variable=exp_spec["variable"],
                    variant_a=exp_spec["variant_a"],
                    variant_b=exp_spec["variant_b"],
                    hypothesis=exp_spec.get("hypothesis", ""),
                )
                registered.append(experiment)
                log.info(f"  Registered experiment: {exp_spec['name']}")
            except Exception as e:
                log.error(f"Failed to register experiment '{exp_spec.get('name')}': {e}")

        result = {
            "active_experiments": registered,
            "experiment_count": len(registered),
        }

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("experiment", result)

        log.info(f"ExperimentAgent: {len(registered)} experiments active.")
        return result

    def _design_experiments(
        self,
        recommendations: dict,
        strategy_ctx: dict,
        pipeline_ctx: dict,
    ) -> list:
        """Ask Gemini to design targeted experiments based on current gaps."""

        next_suggestion = recommendations.get("next_experiment_suggestion", "")
        top_hooks = recommendations.get("best_hook_types", [])
        avoid_topics = recommendations.get("avoid_topics", [])

        prompt = f"""You are the A/B testing strategist for a YouTube Shorts channel.

## Current Strategy Context
- Best performing hooks: {top_hooks}
- Topics to avoid: {avoid_topics}
- AI suggested experiment: {next_suggestion}
- Channel avg views (14d): {strategy_ctx.get('avg_views_last_14d', 'unknown')}

## Task
Design 2 A/B experiments to maximise views and engagement for the next content batch.

Return a JSON array with exactly 2 experiment objects. Each object must have:
{{
  "name": "Short descriptive name",
  "variable": "what is being tested (hook_type | title_style | posting_time | script_length)",
  "variant_a": {{"key": "value"}},
  "variant_b": {{"key": "value"}},
  "hypothesis": "One sentence hypothesis"
}}

Return ONLY a valid JSON array. No markdown."""

        raw = ai_client.generate(prompt)
        if raw:
            try:
                cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                experiments = json.loads(cleaned)
                if isinstance(experiments, list) and len(experiments) > 0:
                    return experiments
            except json.JSONDecodeError:
                log.warning("ExperimentAgent: Could not parse Gemini response, using defaults.")

        return _DEFAULT_EXPERIMENTS
