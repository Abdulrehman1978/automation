# setup.py
"""
Environment validation and setup script
Run this FIRST before building anything
"""

import os
import sys
from pathlib import Path

def validate_environment():
    """Check all API keys and dependencies"""
    
    print("🔍 Validating environment...\n")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required")
        return False
    print("✅ Python version OK")
    
    # Check required API keys
    required_keys = {
        "GEMINI_API_KEY": "Google AI Studio",
        "GROQ_API_KEY": "Groq Console",
        "YOUTUBE_API_KEY": "Google Cloud Console",
    }
    
    missing = []
    for key, source in required_keys.items():
        if not os.environ.get(key):
            print(f"❌ Missing {key} (get from {source})")
            missing.append(key)
        else:
            print(f"✅ {key} found")
    
    if missing:
        print(f"\n⚠️  Missing {len(missing)} required API keys")
        return False
    
    # Test AI connectivity
    print("\n🧪 Testing AI providers...\n")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'OK' if you can hear me")
        print(f"✅ Gemini: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10,
        )
        print(f"✅ Groq: {response.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"❌ Groq failed: {e}")
        return False
    
    print("\n✅ All validations passed!")
    return True

def create_directories():
    """Create all required directories"""
    dirs = [
        "src/core", "src/agents", "src/plugins", "src/intelligence",
        "src/generation", "src/experiments", "src/upload", "src/dashboard",
        "src/dashboard/templates", "src/dashboard/static", "src/utils",
        "data", "data/embeddings", "data/checkpoints",
        "outputs/audio", "outputs/captions", "outputs/videos", "outputs/thumbnails",
        "assets/hooks", "assets/music", "assets/sfx",
        "logs", "credentials",
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    Path("src/__init__.py").touch(exist_ok=True)
    Path("src/core/__init__.py").touch(exist_ok=True)
    Path("src/agents/__init__.py").touch(exist_ok=True)
    Path("src/plugins/__init__.py").touch(exist_ok=True)
    Path("src/intelligence/__init__.py").touch(exist_ok=True)
    Path("src/generation/__init__.py").touch(exist_ok=True)
    Path("src/utils/__init__.py").touch(exist_ok=True)
    
    print("✅ Directories created")

def initialize_database():
    """Initialize SQLite database"""
    # Wait to import db until directories exist and PYTHONPATH might be set
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from core.database import db
        print("✅ Database initialized")
    except ImportError as e:
        print(f"⚠️ Could not initialize database yet (code might not be ready): {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["validate", "init", "all"])
    args = parser.parse_args()
    
    if args.action in ["validate", "all"]:
        if not validate_environment():
            sys.exit(1)
    
    if args.action in ["init", "all"]:
        create_directories()
        initialize_database()
    
    print("\n🚀 Setup complete!")
