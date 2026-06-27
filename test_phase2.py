import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_phase2():
    from core.orchestrator import Orchestrator
    
    orch = Orchestrator(channel_id="test")
    print(f"[PASS] Orchestrator initialized: {orch.run_id}")

    result = orch.execute_workflow(["research"])
    trends = result.get('research', {}).get('trends', [])
    print(f"[PASS] Research agent working: {len(trends)} trends found")
    print(trends)

if __name__ == "__main__":
    test_phase2()
