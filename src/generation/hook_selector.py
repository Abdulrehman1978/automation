import json
from pathlib import Path

class HookSelector:
    def __init__(self):
        self.hooks_dir = Path("assets/hooks")
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_hooks()

    def _ensure_default_hooks(self):
        curiosity_file = self.hooks_dir / "curiosity.json"
        if not curiosity_file.exists():
            with open(curiosity_file, "w") as f:
                json.dump([
                    {"text": "The reason why {topic} is blowing up.", "type": "curiosity"},
                    {"text": "I tried {topic} so you don't have to.", "type": "curiosity"}
                ], f, indent=2)
                
    def get_random_hook(self, topic: str) -> dict:
        # MVP: just return a curiosity hook
        return {"text": f"The secret behind {topic} revealed.", "type": "curiosity", "strength": 85}

    def get_hook_by_type(self, topic: str, hook_type: str) -> dict:
        for file in self.hooks_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    hooks = json.load(f)
                    for h in hooks:
                        if h.get("type") == hook_type:
                            text = h.get("text", "").replace("{topic}", topic)
                            return {"text": text, "type": hook_type, "strength": 85}
            except Exception:
                pass
        
        # Fallback if not found
        return {"text": f"The secret behind {topic} revealed.", "type": hook_type, "strength": 85}
