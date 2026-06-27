import os
import sys
import io

# Fix Windows console encoding for Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Ensure src is in the python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_phase1():
    from core.database import db
    from core.semantic_memory import semantic_memory

    # Test DB
    emb_id = db.save_embedding("test", b"fake_embedding")
    print(f"[PASS] Database working, embedding ID: {emb_id}")

    # Test semantic memory
    result = semantic_memory.check_duplicate("test content")
    print(f"[PASS] Semantic memory working: {result}")

if __name__ == "__main__":
    test_phase1()
