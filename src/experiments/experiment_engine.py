"""
Experiment Engine
-----------------
Designs, runs, and evaluates A/B experiments on content variables
(hooks, titles, posting times, script styles).

Workflow:
  1. ExperimentAgent designs the experiment (calls Gemini for ideas).
  2. ExperimentEngine registers the experiment and picks a variant to apply.
  3. After videos are published, results are recorded in the KnowledgeBase.
  4. LearningAgent picks up winning patterns next cycle.
"""

import json
import uuid
import logging
from datetime import datetime

from intelligence.knowledge_base import knowledge_base

log = logging.getLogger(__name__)


class ExperimentEngine:
    """
    Manages the lifecycle of A/B experiments.

    Experiments compare two variants of a content variable (e.g. hook type A
    vs hook type B) across a set of videos and declare a winner based on
    view / engagement metrics once results are recorded.
    """

    def create_experiment(
        self,
        name: str,
        variable: str,
        variant_a: dict,
        variant_b: dict,
        hypothesis: str = "",
    ) -> dict:
        """
        Register a new A/B experiment.

        Args:
            name: Human-readable name, e.g. "Hook Type: Question vs Shock"
            variable: The thing being tested, e.g. "hook_type"
            variant_a: Dict describing variant A, e.g. {"hook_type": "question"}
            variant_b: Dict describing variant B, e.g. {"hook_type": "shock"}
            hypothesis: Plain-English hypothesis statement.

        Returns:
            Experiment dict with a unique ID.
        """
        experiment_id = uuid.uuid4().hex
        experiment = {
            "id": experiment_id,
            "name": name,
            "variable": variable,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "hypothesis": hypothesis,
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
            "results": {},
        }

        knowledge_base.record_experiment(
            experiment_id=experiment_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            metadata={"variable": variable, "hypothesis": hypothesis},
        )

        log.info(f"[Experiment] Created: '{name}' (id={experiment_id[:8]}...)")
        return experiment

    def pick_variant(self, experiment: dict, video_index: int = 0) -> dict:
        """
        Deterministically assign a variant to a video.
        Even-indexed → variant A, odd-indexed → variant B.
        """
        if video_index % 2 == 0:
            variant = experiment["variant_a"]
            label = "A"
        else:
            variant = experiment["variant_b"]
            label = "B"

        log.debug(
            f"[Experiment] Video #{video_index} → Variant {label}: {variant}"
        )
        return {"label": label, **variant}

    def record_result(
        self,
        experiment_id: str,
        variant_label: str,
        video_id: str,
        views: int,
        likes: int,
        watch_time_pct: float,
    ) -> None:
        """Record outcome metrics for a specific video in an experiment."""
        log.info(
            f"[Experiment] Result for {experiment_id[:8]}: "
            f"Variant {variant_label} | video={video_id} | views={views}"
        )
        # Stored at performance record level via KnowledgeBase
        knowledge_base.record_video_performance(
            video_id=video_id,
            title=f"Experiment:{experiment_id[:8]}-{variant_label}",
            topic=experiment_id,
            hook_type=variant_label,
            views=views,
            likes=likes,
            watch_time_pct=watch_time_pct,
        )

    def evaluate_experiment(
        self,
        experiment: dict,
        results_a: list[dict],
        results_b: list[dict],
        min_samples: int = 5,
    ) -> dict:
        """
        Evaluate which variant won based on average views.

        Args:
            experiment: The experiment dict from create_experiment().
            results_a: List of {views, likes, watch_time_pct} for variant A videos.
            results_b: List of {views, likes, watch_time_pct} for variant B videos.
            min_samples: Minimum videos per variant to declare a winner.

        Returns:
            Evaluation dict with winner, confidence, and recommendation.
        """
        if len(results_a) < min_samples or len(results_b) < min_samples:
            return {
                "winner": None,
                "confidence": 0.0,
                "recommendation": f"Need at least {min_samples} videos per variant.",
                "a_avg_views": 0,
                "b_avg_views": 0,
            }

        avg_a = sum(r["views"] for r in results_a) / len(results_a)
        avg_b = sum(r["views"] for r in results_b) / len(results_b)

        if avg_a == avg_b:
            winner, confidence = "tie", 0.5
        elif avg_a > avg_b:
            winner = "A"
            confidence = min((avg_a - avg_b) / max(avg_a, 1), 1.0)
        else:
            winner = "B"
            confidence = min((avg_b - avg_a) / max(avg_b, 1), 1.0)

        winning_variant = (
            experiment["variant_a"] if winner == "A"
            else experiment["variant_b"] if winner == "B"
            else {}
        )

        evaluation = {
            "winner": winner,
            "confidence": round(confidence, 3),
            "a_avg_views": round(avg_a, 0),
            "b_avg_views": round(avg_b, 0),
            "winning_variant": winning_variant,
            "recommendation": (
                f"Use variant {winner}: {json.dumps(winning_variant)} "
                f"({confidence:.0%} lift confidence)"
                if winner not in (None, "tie")
                else "No clear winner yet."
            ),
        }

        # Persist winner to Knowledge Base
        knowledge_base.record_experiment(
            experiment_id=experiment["id"],
            name=experiment["name"],
            variant_a=experiment["variant_a"],
            variant_b=experiment["variant_b"],
            winner=winner,
            confidence=confidence,
        )

        log.info(
            f"[Experiment] '{experiment['name']}' → Winner: {winner} "
            f"(A avg={avg_a:.0f} vs B avg={avg_b:.0f})"
        )
        return evaluation


# Global singleton
experiment_engine = ExperimentEngine()
