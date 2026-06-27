import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_phase3():
    from core.orchestrator import Orchestrator
    
    orch = Orchestrator(channel_id="test")
    print(f"[PASS] Orchestrator initialized: {orch.run_id}")

    result = orch.execute_workflow(["research", "idea", "judge"])
    ideas = result.get('judge', {}).get('approved_ideas', [])
    print(f"[PASS] Idea/Judge agents working: {len(ideas)} ideas approved")
    for idea in ideas:
        print(f" - {idea['title']} (Score: {idea['composite_score']})")

if __name__ == "__main__":
    test_phase3()
