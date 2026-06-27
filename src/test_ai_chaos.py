import os
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from core.config import Config
from utils.ai_client import ai_client

def test_ai_chaos():
    print("Testing AI Client Chaos (Invalid Gemini Key)...")
    
    # Intentionally corrupt Gemini key
    Config.GEMINI_API_KEY = "invalid_key_for_chaos_test"
    ai_client._gemini = None
    ai_client._init_gemini()
    
    res = ai_client.generate("Say 'hello test'", provider="auto")
    
    assert res != "", "Fallback to Groq failed, returned empty string"
    print(f"Test passed! AI Client fell back to Groq. Output: {res}")

if __name__ == "__main__":
    test_ai_chaos()
