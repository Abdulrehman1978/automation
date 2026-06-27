import os
import sys
from pathlib import Path

# Setup path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from core.orchestrator import Orchestrator
from agents.judge_agent import JudgeAgent

def test_judge_chaos():
    print("Testing Judge Agent Chaos (Terrible Idea)...")
    
    orch = Orchestrator(channel_id="test_chaos")
    
    terrible_idea = {
        "title": "Watching Paint Dry For 10 Hours",
        "concept": "Literally just a static camera staring at a blank wall while white paint dries. No talking, no music.",
        "hook": {"text": "Look at this wall."},
        "keywords": ["paint", "drying", "wall"]
    }
    
    context = {
        "idea": {
            "ideas": [terrible_idea]
        }
    }
    
    judge = JudgeAgent(orch)
    result = judge.execute(context)
    
    approved = result.get("approved_ideas", [])
    if len(approved) == 0:
        print("Test passed! Terrible idea was rejected (either initially or after rewrite).")
    else:
        print(f"Test failed! Terrible idea was approved with score: {approved[0].get('composite_score')}")

if __name__ == "__main__":
    test_judge_chaos()
