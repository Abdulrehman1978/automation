# src/core/database.py
"""
Enhanced database with semantic memory and experiments
"""

import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

log = logging.getLogger(__name__)

DB_PATH = "data/viral_os.db"

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def conn(self):
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_schema(self):
        with self.conn() as c:
            c.executescript("""
            
            -- ═══════════════════════════════════════════════════════════
            -- CONTENT MEMORY (with semantic embeddings)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS content_memory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id      TEXT DEFAULT 'main',
                
                -- Content
                title           TEXT NOT NULL,
                concept         TEXT,
                hook            TEXT,
                hook_type       TEXT,
                emotion         TEXT,
                script          TEXT,
                
                -- Semantic Search
                embedding_id    TEXT,              -- Links to embeddings table
                keywords        TEXT,              -- JSON array
                category        TEXT,
                topic_cluster   TEXT,
                
                -- Predictions vs Reality
                viral_score_predicted  INTEGER,
                viral_score_actual     INTEGER,
                retention_predicted    TEXT,       -- JSON: {3s, 10s, completion}
                retention_actual       TEXT,       -- JSON: actual metrics
                
                -- Performance
                views_24h       INTEGER DEFAULT 0,
                views_7d        INTEGER DEFAULT 0,
                views_30d       INTEGER DEFAULT 0,
                ctr             REAL DEFAULT 0,
                retention_3s    REAL DEFAULT 0,
                retention_10s   REAL DEFAULT 0,
                avg_watch_pct   REAL DEFAULT 0,
                likes           INTEGER DEFAULT 0,
                comments        INTEGER DEFAULT 0,
                shares          INTEGER DEFAULT 0,
                subs_gained     INTEGER DEFAULT 0,
                
                -- Metadata
                youtube_id      TEXT UNIQUE,
                instagram_id    TEXT,
                upload_date     TIMESTAMP,
                
                -- Experiment tracking
                experiment_id   TEXT,
                variant_id      TEXT,
                is_winner       INTEGER DEFAULT 0,
                
                -- Assets
                video_path      TEXT,
                thumbnail_path  TEXT,
                audio_path      TEXT,
                caption_path    TEXT,
                
                -- Prompts & versions
                prompt_version  TEXT,
                hook_id         TEXT,
                tool_used       TEXT,
                
                full_data       TEXT,              -- JSON blob
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_content_embedding ON content_memory(embedding_id);
            CREATE INDEX IF NOT EXISTS idx_content_channel ON content_memory(channel_id);
            CREATE INDEX IF NOT EXISTS idx_content_upload ON content_memory(upload_date);
            CREATE INDEX IF NOT EXISTS idx_content_experiment ON content_memory(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_content_youtube ON content_memory(youtube_id);

            -- ═══════════════════════════════════════════════════════════
            -- SEMANTIC EMBEDDINGS (separate table for performance)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS embeddings (
                id              TEXT PRIMARY KEY,  -- UUID
                text            TEXT,
                embedding       BLOB,              -- Numpy array as bytes
                model           TEXT DEFAULT 'all-MiniLM-L6-v2',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_embedding_text ON embeddings(text);

            -- ═══════════════════════════════════════════════════════════
            -- EXPERIMENTS (A/B/C/D testing engine)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS experiments (
                id              TEXT PRIMARY KEY,  -- UUID
                channel_id      TEXT,
                name            TEXT,
                hypothesis      TEXT,
                test_type       TEXT,              -- hook|title|thumbnail|posting_time
                
                variants        TEXT,              -- JSON array of variant specs
                
                status          TEXT DEFAULT 'running',
                                                   -- running|analyzing|completed
                
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at    TIMESTAMP,
                
                -- Results
                winner_variant  TEXT,
                confidence      REAL,              -- Statistical confidence 0-1
                improvement_pct REAL,
                
                results_summary TEXT,              -- JSON
                lesson_learned  TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_exp_channel ON experiments(channel_id);
            CREATE INDEX IF NOT EXISTS idx_exp_status ON experiments(status);

            -- ═══════════════════════════════════════════════════════════
            -- KNOWLEDGE BASE (learned rules from experience)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id      TEXT,
                
                rule_type       TEXT,              -- hook|title|thumbnail|timing|topic
                category        TEXT,
                
                rule            TEXT NOT NULL,     -- "Question hooks get 18% better CTR"
                evidence        TEXT,              -- JSON: supporting data
                confidence      REAL DEFAULT 0.5,  -- 0-1
                sample_size     INTEGER DEFAULT 0,
                
                impact_metric   TEXT,              -- ctr|retention|views
                impact_value    REAL,              -- +18.0 (percent)
                
                applies_to      TEXT,              -- JSON: conditions
                
                is_active       INTEGER DEFAULT 1,
                priority        INTEGER DEFAULT 50,
                
                learned_from    TEXT,              -- experiment_id or 'manual'
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_validated  TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_kb_channel ON knowledge_base(channel_id);
            CREATE INDEX IF NOT EXISTS idx_kb_type ON knowledge_base(rule_type);
            CREATE INDEX IF NOT EXISTS idx_kb_active ON knowledge_base(is_active);

            -- ═══════════════════════════════════════════════════════════
            -- HOOK PERFORMANCE
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS hook_performance (
                id              TEXT PRIMARY KEY,  -- UUID
                hook_template   TEXT NOT NULL,
                hook_type       TEXT,              -- curiosity|shock|question
                
                times_used      INTEGER DEFAULT 0,
                
                avg_retention_3s  REAL DEFAULT 0,
                avg_retention_10s REAL DEFAULT 0,
                avg_ctr         REAL DEFAULT 0,
                avg_views       INTEGER DEFAULT 0,
                
                best_categories TEXT,              -- JSON: categories where it works
                worst_categories TEXT,             -- JSON: where it fails
                
                last_used       TIMESTAMP,
                is_active       INTEGER DEFAULT 1,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_hook_type ON hook_performance(hook_type);
            CREATE INDEX IF NOT EXISTS idx_hook_active ON hook_performance(is_active);

            -- ═══════════════════════════════════════════════════════════
            -- PROMPT PERFORMANCE (track which prompts work)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id              TEXT PRIMARY KEY,
                version_tag     TEXT NOT NULL,     -- v1.2.3
                prompt_type     TEXT,              -- veo|meta_ai|script|title
                
                prompt_template TEXT NOT NULL,
                
                times_used      INTEGER DEFAULT 0,
                avg_views       INTEGER DEFAULT 0,
                avg_retention   REAL DEFAULT 0,
                avg_quality     REAL DEFAULT 0,
                failure_rate    REAL DEFAULT 0,
                
                is_active       INTEGER DEFAULT 1,
                is_default      INTEGER DEFAULT 0,
                
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deprecated_at   TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_prompt_type ON prompt_versions(prompt_type);
            CREATE INDEX IF NOT EXISTS idx_prompt_active ON prompt_versions(is_active);

            -- ═══════════════════════════════════════════════════════════
            -- ASSET LIBRARY (reusable components)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS asset_library (
                id              TEXT PRIMARY KEY,
                asset_type      TEXT,              -- music|sfx|transition|overlay
                name            TEXT,
                file_path       TEXT,
                
                tags            TEXT,              -- JSON array
                category        TEXT,
                mood            TEXT,
                
                times_used      INTEGER DEFAULT 0,
                avg_performance REAL DEFAULT 0,
                
                license         TEXT,
                source          TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_asset_type ON asset_library(asset_type);
            CREATE INDEX IF NOT EXISTS idx_asset_category ON asset_library(category);

            -- ═══════════════════════════════════════════════════════════
            -- TREND INTELLIGENCE
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS trend_clusters (
                id              TEXT PRIMARY KEY,
                master_topic    TEXT NOT NULL,
                keywords        TEXT,              -- JSON
                sources         TEXT,              -- JSON
                
                combined_score  INTEGER DEFAULT 0,
                priority_score  REAL DEFAULT 0,    -- Multi-factor priority
                
                status          TEXT DEFAULT 'growing',
                category        TEXT,
                
                lifecycle_stage TEXT,              -- exploding|growing|peak|declining
                days_remaining  INTEGER,
                urgency_score   INTEGER,
                
                competition_level TEXT,            -- low|medium|high|saturated
                content_gap     TEXT,
                
                discovered_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                peak_predicted  TIMESTAMP,
                used_in_video   INTEGER DEFAULT 0,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_trend_status ON trend_clusters(status);
            CREATE INDEX IF NOT EXISTS idx_trend_priority ON trend_clusters(priority_score);

            -- ═══════════════════════════════════════════════════════════
            -- COMPETITION DATA
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS competition_data (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                topic           TEXT,
                video_id        TEXT,
                title           TEXT,
                channel         TEXT,
                
                views           INTEGER,
                likes           INTEGER,
                comments        INTEGER,
                duration_sec    INTEGER,
                
                hook_text       TEXT,
                thumbnail_style TEXT,
                
                gaps_found      TEXT,              -- JSON
                fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_comp_topic ON competition_data(topic);

            -- ═══════════════════════════════════════════════════════════
            -- PIPELINE RUNS & CHECKPOINTS
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id          TEXT UNIQUE NOT NULL,
                channel_id      TEXT DEFAULT 'main',
                
                status          TEXT DEFAULT 'running',
                current_step    TEXT,
                completed_steps TEXT,              -- JSON array
                step_data       TEXT,              -- JSON blob
                
                error_log       TEXT,
                
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at    TIMESTAMP,
                stats           TEXT               -- JSON
            );

            CREATE INDEX IF NOT EXISTS idx_run_status ON pipeline_runs(status);
            CREATE INDEX IF NOT EXISTS idx_run_channel ON pipeline_runs(channel_id);

            -- ═══════════════════════════════════════════════════════════
            -- API USAGE TRACKING
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS api_usage (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                provider        TEXT NOT NULL,
                endpoint        TEXT,
                tokens_used     INTEGER DEFAULT 0,
                requests_made   INTEGER DEFAULT 0,
                cost_usd        REAL DEFAULT 0,
                date            TEXT,
                run_id          TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_usage_date ON api_usage(date);
            CREATE INDEX IF NOT EXISTS idx_usage_provider ON api_usage(provider);

            -- ═══════════════════════════════════════════════════════════
            -- APPROVAL QUEUE (human-in-the-loop)
            -- ═══════════════════════════════════════════════════════════
            CREATE TABLE IF NOT EXISTS approval_queue (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id      TEXT UNIQUE,
                channel_id      TEXT,
                
                title           TEXT,
                concept         TEXT,
                thumbnail_url   TEXT,
                
                status          TEXT DEFAULT 'pending',
                                               -- pending|approved|rejected|editing
                
                package_data    TEXT,          -- Full JSON
                
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at     TIMESTAMP,
                reviewed_by     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_queue(status);

            """)

    # ═══════════════════════════════════════════════════════════
    # CONTENT MEMORY METHODS
    # ═══════════════════════════════════════════════════════════

    def save_content(self, data: dict, channel_id: str = "main") -> int:
        """Save a new content package to the database"""
        idea = data.get("idea", {})
        metadata = data.get("metadata", {})
        
        with self.conn() as c:
            cursor = c.execute("""
                INSERT INTO content_memory (
                    channel_id, title, concept, hook, script, keywords, category, full_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                channel_id,
                idea.get("title", ""),
                idea.get("concept", ""),
                json.dumps(idea.get("hook", {})),
                data.get("script", {}).get("full_narration", ""),
                json.dumps(idea.get("keywords", [])),
                idea.get("category", ""),
                json.dumps(data)
            ))
            return cursor.lastrowid

    def update_content_embedding(self, content_id: int, embedding_id: str):
        """Link an embedding ID to a content package"""
        with self.conn() as c:
            c.execute("UPDATE content_memory SET embedding_id = ? WHERE id = ?", (embedding_id, content_id))

    # ═══════════════════════════════════════════════════════════
    # SEMANTIC MEMORY METHODS
    # ═══════════════════════════════════════════════════════════

    def save_embedding(self, text: str, embedding: bytes, model: str = "all-MiniLM-L6-v2") -> str:
        """Save an embedding vector"""
        import uuid
        emb_id = uuid.uuid4().hex
        
        with self.conn() as c:
            c.execute("""
                INSERT INTO embeddings (id, text, embedding, model)
                VALUES (?, ?, ?, ?)
            """, (emb_id, text, embedding, model))
        
        return emb_id

    def find_similar_content(self, embedding: bytes, threshold: float = 0.85, limit: int = 10) -> list:
        """Find similar content by embedding (requires semantic_memory.py)"""
        # This is called by semantic_memory.py which handles the actual comparison
        with self.conn() as c:
            rows = c.execute("""
                SELECT cm.*, e.embedding
                FROM content_memory cm
                JOIN embeddings e ON cm.embedding_id = e.id
                ORDER BY cm.created_at DESC
                LIMIT 500
            """).fetchall()
        
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # KNOWLEDGE BASE METHODS
    # ═══════════════════════════════════════════════════════════

    def add_knowledge(self, rule: dict) -> int:
        """Add a learned rule to the knowledge base"""
        with self.conn() as c:
            cursor = c.execute("""
                INSERT INTO knowledge_base (
                    channel_id, rule_type, category, rule, evidence,
                    confidence, sample_size, impact_metric, impact_value,
                    applies_to, learned_from
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.get("channel_id", "main"),
                rule.get("rule_type", ""),
                rule.get("category", ""),
                rule.get("rule", ""),
                json.dumps(rule.get("evidence", {})),
                rule.get("confidence", 0.5),
                rule.get("sample_size", 0),
                rule.get("impact_metric", ""),
                rule.get("impact_value", 0.0),
                json.dumps(rule.get("applies_to", {})),
                rule.get("learned_from", "manual"),
            ))
            return cursor.lastrowid

    def get_active_knowledge(self, channel_id: str = "main", category: str = None) -> list:
        """Get active knowledge rules"""
        with self.conn() as c:
            if category:
                rows = c.execute("""
                    SELECT * FROM knowledge_base
                    WHERE channel_id = ? AND category = ? AND is_active = 1
                    ORDER BY confidence DESC, impact_value DESC
                """, (channel_id, category)).fetchall()
            else:
                rows = c.execute("""
                    SELECT * FROM knowledge_base
                    WHERE channel_id = ? AND is_active = 1
                    ORDER BY priority DESC, confidence DESC
                """, (channel_id,)).fetchall()
        
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # EXPERIMENT METHODS
    # ═══════════════════════════════════════════════════════════

    def create_experiment(self, exp: dict) -> str:
        """Create a new A/B test experiment"""
        import uuid
        exp_id = exp.get("id", uuid.uuid4().hex)
        
        with self.conn() as c:
            c.execute("""
                INSERT INTO experiments (
                    id, channel_id, name, hypothesis, test_type,
                    variants, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'running')
            """, (
                exp_id,
                exp.get("channel_id", "main"),
                exp.get("name", ""),
                exp.get("hypothesis", ""),
                exp.get("test_type", ""),
                json.dumps(exp.get("variants", [])),
            ))
        
        return exp_id

    def get_running_experiments(self, channel_id: str = "main") -> list:
        """Get currently running experiments"""
        with self.conn() as c:
            rows = c.execute("""
                SELECT * FROM experiments
                WHERE channel_id = ? AND status = 'running'
                ORDER BY started_at DESC
            """, (channel_id,)).fetchall()
        
        return [dict(r) for r in rows]

    def complete_experiment(self, exp_id: str, results: dict):
        """Mark experiment as complete with results"""
        with self.conn() as c:
            c.execute("""
                UPDATE experiments SET
                    status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    winner_variant = ?,
                    confidence = ?,
                    improvement_pct = ?,
                    results_summary = ?,
                    lesson_learned = ?
                WHERE id = ?
            """, (
                results.get("winner", ""),
                results.get("confidence", 0.0),
                results.get("improvement_pct", 0.0),
                json.dumps(results.get("summary", {})),
                results.get("lesson", ""),
                exp_id,
            ))

    # ═══════════════════════════════════════════════════════════
    # PRIORITY SCORING
    # ═══════════════════════════════════════════════════════════

    def update_trend_priority(self, trend_id: str, priority_score: float):
        """Update multi-factor priority score for a trend"""
        with self.conn() as c:
            c.execute("""
                UPDATE trend_clusters
                SET priority_score = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (priority_score, trend_id))

    def get_top_priority_trends(self, channel_id: str = "main", limit: int = 10) -> list:
        """Get highest priority trends"""
        with self.conn() as c:
            rows = c.execute("""
                SELECT * FROM trend_clusters
                WHERE status IN ('exploding', 'growing', 'peak')
                  AND priority_score > 0
                ORDER BY priority_score DESC
                LIMIT ?
            """, (limit,)).fetchall()
        
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # APPROVAL QUEUE
    # ═══════════════════════════════════════════════════════════

    def add_to_approval_queue(self, package: dict) -> str:
        """Add package to human approval queue"""
        import uuid
        pkg_id = uuid.uuid4().hex
        
        with self.conn() as c:
            c.execute("""
                INSERT INTO approval_queue (
                    package_id, channel_id, title, concept,
                    thumbnail_url, package_data
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pkg_id,
                package.get("channel_id", "main"),
                package.get("title", ""),
                package.get("concept", ""),
                package.get("thumbnail_url", ""),
                json.dumps(package),
            ))
        
        return pkg_id

    def get_pending_approvals(self, channel_id: str = "main") -> list:
        """Get packages awaiting approval"""
        with self.conn() as c:
            rows = c.execute("""
                SELECT * FROM approval_queue
                WHERE channel_id = ? AND status = 'pending'
                ORDER BY created_at ASC
            """, (channel_id,)).fetchall()
        
        return [dict(r) for r in rows]

    def approve_package(self, package_id: str, reviewer: str = "user"):
        """Approve a package"""
        with self.conn() as c:
            c.execute("""
                UPDATE approval_queue SET
                    status = 'approved',
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?
                WHERE package_id = ?
            """, (reviewer, package_id))

    def reject_package(self, package_id: str, reviewer: str = "user"):
        """Reject a package"""
        with self.conn() as c:
            c.execute("""
                UPDATE approval_queue SET
                    status = 'rejected',
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?
                WHERE package_id = ?
            """, (reviewer, package_id))

    # ═══════════════════════════════════════════════════════════
    # PERFORMANCE TRACKING (for KnowledgeBase)
    # ═══════════════════════════════════════════════════════════

    def save_performance_record(
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
        """Upsert a video performance record into content_memory."""
        import uuid
        from datetime import datetime
        record_id = uuid.uuid4().hex
        with self.conn() as c:
            c.execute("""
                INSERT INTO content_memory (
                    channel_id, title, concept, hook, views_30d, likes,
                    comments, avg_watch_pct, created_at
                ) VALUES ('main', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, topic, hook_type, views, likes,
                comments, watch_time_pct,
                upload_date or datetime.utcnow().isoformat(),
            ))
        return record_id

    def query_top_hooks(self, min_views: int = 1000, limit: int = 10) -> list:
        """Return hook types ranked by average views from content_memory."""
        with self.conn() as c:
            rows = c.execute("""
                SELECT hook AS hook_type,
                       AVG(views_30d) AS avg_views,
                       COUNT(*) AS sample_size
                FROM content_memory
                WHERE views_30d >= ?
                  AND hook IS NOT NULL AND hook != ''
                GROUP BY hook
                ORDER BY avg_views DESC
                LIMIT ?
            """, (min_views, limit)).fetchall()
        return [dict(r) for r in rows]

    def query_topic_stats(self, topic: str) -> dict:
        """Return aggregated performance stats for a topic (concept field)."""
        with self.conn() as c:
            row = c.execute("""
                SELECT concept AS topic,
                       COUNT(*) AS video_count,
                       AVG(views_30d) AS avg_views,
                       AVG(likes) AS avg_likes,
                       AVG(avg_watch_pct) AS avg_watch_pct
                FROM content_memory
                WHERE concept LIKE ?
                GROUP BY concept
            """, (f"%{topic}%",)).fetchone()
        return dict(row) if row else {}

    def query_recent_performance(self, days: int = 30, limit: int = 50) -> list:
        """Return recent performance records ordered by date."""
        with self.conn() as c:
            rows = c.execute("""
                SELECT id, title, hook AS hook_type, views_30d AS views,
                       likes, comments, avg_watch_pct, created_at
                FROM content_memory
                WHERE created_at >= datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"-{days} days", limit)).fetchall()
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # PROMPT PERFORMANCE TRACKING (for KnowledgeBase)
    # ═══════════════════════════════════════════════════════════

    def save_prompt_result(
        self,
        template: str,
        topic: str,
        quality_score: float,
        token_count: int = 0,
    ) -> str:
        """Log prompt effectiveness into prompt_versions table."""
        import uuid
        prompt_id = uuid.uuid4().hex
        with self.conn() as c:
            # Upsert: if same template exists, update average quality
            existing = c.execute(
                "SELECT id, times_used, avg_quality FROM prompt_versions WHERE prompt_template = ?",
                (template,)
            ).fetchone()
            if existing:
                new_count = existing["times_used"] + 1
                new_avg = (existing["avg_quality"] * existing["times_used"] + quality_score) / new_count
                c.execute("""
                    UPDATE prompt_versions
                    SET times_used = ?, avg_quality = ?, deprecated_at = NULL
                    WHERE id = ?
                """, (new_count, new_avg, existing["id"]))
                return existing["id"]
            else:
                c.execute("""
                    INSERT INTO prompt_versions (
                        id, version_tag, prompt_type, prompt_template,
                        times_used, avg_quality, is_active
                    ) VALUES (?, 'auto', 'general', ?, 1, ?, 1)
                """, (prompt_id, template, quality_score))
                return prompt_id

    def query_best_prompts(self, limit: int = 5) -> list:
        """Return highest-quality prompt templates."""
        with self.conn() as c:
            rows = c.execute("""
                SELECT id, prompt_template AS template, avg_quality, times_used
                FROM prompt_versions
                WHERE is_active = 1 AND times_used > 0
                ORDER BY avg_quality DESC, times_used DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════════════════════════
    # EXPERIMENT QUERIES (for KnowledgeBase / ExperimentEngine)
    # ═══════════════════════════════════════════════════════════

    def save_experiment(
        self,
        experiment_id: str,
        name: str,
        variant_a: str,
        variant_b: str,
        winner: str = None,
        confidence: float = 0.0,
        extra: str = "{}",
    ) -> str:
        """Upsert experiment record into experiments table."""
        with self.conn() as c:
            existing = c.execute(
                "SELECT id FROM experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
            if existing:
                c.execute("""
                    UPDATE experiments SET
                        winner_variant = ?, confidence = ?,
                        status = CASE WHEN ? IS NOT NULL THEN 'completed' ELSE status END,
                        completed_at = CASE WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP ELSE completed_at END,
                        results_summary = ?
                    WHERE id = ?
                """, (winner, confidence, winner, winner, extra, experiment_id))
            else:
                c.execute("""
                    INSERT INTO experiments (
                        id, channel_id, name, hypothesis, test_type,
                        variants, winner_variant, confidence, status
                    ) VALUES (?, 'main', ?, '', 'ab', ?, ?, ?, ?)
                """, (
                    experiment_id, name,
                    json.dumps([variant_a, variant_b]),
                    winner, confidence,
                    "completed" if winner else "running",
                ))
        return experiment_id

    def query_experiments(self, limit: int = 20) -> list:
        """Return experiments ordered by most recent."""
        with self.conn() as c:
            rows = c.execute("""
                SELECT id, name, winner_variant AS winner, confidence,
                       status, started_at, completed_at
                FROM experiments
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]


# Global singleton
db = Database()
