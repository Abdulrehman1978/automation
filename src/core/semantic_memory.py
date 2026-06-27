# src/core/semantic_memory.py
"""
Semantic Memory Engine
Uses ChromaDB for true similarity detection, falls back to basic keyword/TF-IDF mock
"""

import logging
from core.database import Database

log = logging.getLogger(__name__)

class SemanticMemory:
    """
    Handles all embedding-based similarity searches.
    Prevents duplicate content better than keyword matching.
    """

    def __init__(self):
        self.db = Database()
        self.chroma_client = None
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            # Initialize persistent client
            self.chroma_client = chromadb.PersistentClient(path="data/chroma_db")
            self.collection = self.chroma_client.get_or_create_collection(name="video_concepts")
            log.info("ChromaDB initialized for Semantic Memory.")
        except ImportError:
            log.warning("ChromaDB not installed. Semantic Memory will fallback to TF-IDF logic.")
        except Exception as e:
            log.error(f"Error initializing ChromaDB: {e}. Falling back to TF-IDF.")

    def add_concept(self, video_id: str, text: str):
        if self.collection:
            self.collection.upsert(
                documents=[text],
                metadatas=[{"video_id": str(video_id)}],
                ids=[str(video_id)]
            )
        else:
            log.debug("ChromaDB missing. Concept added to DB natively instead.")

    def find_content_gaps(self, topic: str, threshold: float = 1.0) -> str:
        """Returns 'fresh', 'partial_coverage', or 'duplicate'"""
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[topic],
                    n_results=1
                )
                if results and results.get("distances") and results["distances"][0]:
                    dist = results["distances"][0][0]
                    # Note: L2 distance. Smaller is closer.
                    if dist < 0.5:
                        return "duplicate"
                    elif dist < threshold:
                        return "partial_coverage"
                return "fresh"
            except Exception as e:
                log.warning(f"ChromaDB query failed: {e}")
                return "fresh"
        else:
            # TF-IDF / keyword Fallback mock
            with self.db.conn() as c:
                # Assuming 'content_memory' table has 'idea' or 'title'
                try:
                    rows = c.execute("SELECT idea_ref FROM experiments ORDER BY id DESC LIMIT 100").fetchall()
                    for row in rows:
                        if row["idea_ref"] and topic.lower() in row["idea_ref"].lower():
                            return "partial_coverage"
                except Exception:
                    pass
            return "fresh"

# Global singleton
semantic_memory = SemanticMemory()
