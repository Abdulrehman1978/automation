# src/core/semantic_memory.py
"""
Semantic Memory Engine
Uses sentence embeddings for true similarity detection
"""

import numpy as np
import logging
from sentence_transformers import SentenceTransformer

from core.database import db

log = logging.getLogger(__name__)


class SemanticMemory:
    """
    Handles all embedding-based similarity searches.
    Prevents duplicate content better than keyword matching.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        log.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        return self.model.encode(text, convert_to_numpy=True)

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

    def save_content_embedding(self, text: str) -> str:
        """Embed text and save to database"""
        embedding = self.embed(text)
        embedding_bytes = embedding.tobytes()
        
        emb_id = db.save_embedding(text, embedding_bytes, self.model_name)
        return emb_id

    def check_duplicate(self, text: str, threshold: float = 0.85) -> dict:
        """
        Check if text is too similar to existing content.
        
        Returns:
            {
                "is_duplicate": bool,
                "similarity": float,
                "matching_content": dict or None
            }
        """
        new_embedding = self.embed(text)
        
        # Get recent content with embeddings
        past_content = db.find_similar_content(new_embedding.tobytes())
        
        if not past_content:
            return {"is_duplicate": False, "similarity": 0.0, "matching_content": None}

        best_match = None
        best_similarity = 0.0

        for content in past_content:
            stored_embedding_bytes = content.get("embedding")
            if not stored_embedding_bytes:
                continue

            # Convert bytes back to numpy array
            stored_embedding = np.frombuffer(stored_embedding_bytes, dtype=np.float32)
            
            similarity = self.cosine_similarity(new_embedding, stored_embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = content

        return {
            "is_duplicate": best_similarity >= threshold,
            "similarity": round(best_similarity, 3),
            "matching_content": best_match if best_similarity >= threshold else None,
        }

    def find_similar(self, text: str, top_k: int = 5, min_similarity: float = 0.5) -> list:
        """Find top K most similar pieces of content"""
        query_embedding = self.embed(text)
        past_content = db.find_similar_content(query_embedding.tobytes())

        results = []
        for content in past_content:
            stored_embedding_bytes = content.get("embedding")
            if not stored_embedding_bytes:
                continue

            stored_embedding = np.frombuffer(stored_embedding_bytes, dtype=np.float32)
            similarity = self.cosine_similarity(query_embedding, stored_embedding)

            if similarity >= min_similarity:
                results.append({
                    "content": content,
                    "similarity": round(similarity, 3),
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]


# Global singleton
semantic_memory = SemanticMemory()
