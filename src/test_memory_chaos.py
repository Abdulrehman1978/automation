import os
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from core.semantic_memory import SemanticMemory

def test_memory_chaos():
    print("Testing Semantic Memory Chaos (Missing ChromaDB)...")
    
    # We will instantiate SemanticMemory but force an ImportError
    import builtins
    real_import = builtins.__import__
    
    def mocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'chromadb':
            raise ImportError("Mocked missing chromadb")
        return real_import(name, globals, locals, fromlist, level)
        
    builtins.__import__ = mocked_import
    
    try:
        mem = SemanticMemory()
        
        assert mem.chroma_client is None, "ChromaDB client should be None"
        gap = mem.find_content_gaps("Testing topic")
        assert gap in ["fresh", "partial_coverage"], "Fallback didn't return correct gap status"
        print("Test passed! Semantic Memory fell back to TF-IDF mock gracefully.")
    finally:
        builtins.__import__ = real_import

if __name__ == "__main__":
    test_memory_chaos()
