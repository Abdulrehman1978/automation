"""
Knowledge Base
--------------
Persists historical performance data (video metrics, A/B test results,
prompt effectiveness scores) so the Learning Agent can adapt strategy
over time.  Uses the existing SQLite database via core.database.
"""

import json
import logging
from datetime import datetime
from core.database import db

log = logging.getLogger(__name__)


class KnowledgeBase:
    # ------------------------------------------------------------------ #
    # Performance records                                                  #
    # ------------------------------------------------------------------ #

    def record_video_performance(
        self,
        video_id: str,
        title: str,
        topic: str,
        hook_type: str,
        views: int = 0,
        likes: int = 0,
        comments: int = 0,
        watch_time_pct: float = 0.0,
        upload_date: str = None,
    ) -> str:
        """Save a video's performance snapshot."""
        record_id = db.save_performance_record(
            video_id=video_id,
            title=title,
            topic=topic,
            hook_type=hook_type,
            views=views,
            likes=likes,
            comments=comments,
            watch_time_pct=watch_time_pct,
            upload_date=upload_date or datetime.utcnow().isoformat(),
        )
        log.info(f"[KB] Recorded performance for video {video_id}: {views} views")
        return record_id

    def get_top_performing_hooks(self, min_views: int = 1000, limit: int = 10) -> list:
        """Return hook types ranked by average views."""
        return db.query_top_hooks(min_views=min_views, limit=limit)

    def get_topic_performance(self, topic: str) -> dict:
        """Return aggregated stats for a given topic."""
        return db.query_topic_stats(topic)

    def get_recent_performance(self, days: int = 30, limit: int = 50) -> list:
        """Return the most recent performance records."""
        return db.query_recent_performance(days=days, limit=limit)

    # ------------------------------------------------------------------ #
    # Prompt & strategy effectiveness                                      #
    # ------------------------------------------------------------------ #

    def record_prompt_result(
        self,
        prompt_template: str,
        topic: str,
        output_quality_score: float,
        token_count: int = 0,
    ) -> str:
        """Log how well a prompt template performed."""
        return db.save_prompt_result(
            template=prompt_template,
            topic=topic,
            quality_score=output_quality_score,
            token_count=token_count,
        )

    def get_best_prompt_templates(self, limit: int = 5) -> list:
        """Return the highest-scoring prompt templates."""
        return db.query_best_prompts(limit=limit)

    # ------------------------------------------------------------------ #
    # Experiment results                                                   #
    # ------------------------------------------------------------------ #

    def record_experiment(
        self,
        experiment_id: str,
        name: str,
        variant_a: dict,
        variant_b: dict,
        winner: str = None,
        confidence: float = 0.0,
        metadata: dict = None,
    ) -> str:
        """Persist an A/B experiment result."""
        return db.save_experiment(
            experiment_id=experiment_id,
            name=name,
            variant_a=json.dumps(variant_a),
            variant_b=json.dumps(variant_b),
            winner=winner,
            confidence=confidence,
            extra=json.dumps(metadata or {}),
        )

    def get_experiment_history(self, limit: int = 20) -> list:
        """Return past experiments ordered by date."""
        return db.query_experiments(limit=limit)

    # ------------------------------------------------------------------ #
    # Strategy recommendations summary                                     #
    # ------------------------------------------------------------------ #

    def build_strategy_context(self) -> dict:
        """
        Synthesise available data into a compact strategy context dict
        that can be injected into AI prompts.
        """
        top_hooks = self.get_top_performing_hooks(limit=5)
        recent = self.get_recent_performance(days=14, limit=10)
        best_prompts = self.get_best_prompt_templates(limit=3)

        hook_names = [h.get("hook_type", "unknown") for h in top_hooks] if top_hooks else []
        avg_views = (
            sum(r.get("views", 0) for r in recent) / len(recent)
            if recent else 0
        )

        with db.conn() as c:
            row = c.execute("SELECT COUNT(*) as cnt FROM content_memory WHERE views_30d > 0").fetchone()
            total_valid = row["cnt"] if row else 0

        return {
            "top_hook_types": hook_names,
            "avg_views_last_14d": round(avg_views, 0),
            "best_prompt_templates": [p.get("template", "") for p in best_prompts],
            "total_videos_tracked": len(recent),
            "total_valid_videos": total_valid,
        }


# Global singleton
knowledge_base = KnowledgeBase()
