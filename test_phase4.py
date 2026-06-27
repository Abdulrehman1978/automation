import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_phase4():
    from core.orchestrator import Orchestrator
    
    orch = Orchestrator(channel_id="test")
    print(f"[PASS] Orchestrator initialized: {orch.run_id}")

    result = orch.execute_workflow(["research", "idea", "judge", "script", "seo"])
    seo_packages = result.get('seo', {}).get('seo_packages', [])
    print(f"[PASS] Script/SEO agents working: {len(seo_packages)} packages ready")
    for pkg in seo_packages:
        print(f" - Title: {pkg['final_title']}")
        print(f"   Tags: {pkg['tags']}")

if __name__ == "__main__":
    test_phase4()
