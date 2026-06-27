"""
Phase 5 Test — Intelligence & Learning
Tests: KnowledgeBase, LearningAgent, ExperimentAgent, ExperimentEngine
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


def test_phase5():
    from intelligence.knowledge_base import knowledge_base
    from experiments.experiment_engine import experiment_engine
    from core.orchestrator import Orchestrator

    print("=" * 60)
    print("PHASE 5: Intelligence & Learning")
    print("=" * 60)

    # --- 1. Knowledge Base: record some mock performance data ---
    print("\n[1] Recording mock video performance...")
    rid = knowledge_base.record_video_performance(
        video_id="test_vid_001",
        title="AI Will Replace You in 2025",
        topic="AI jobs",
        hook_type="shock",
        views=15000,
        likes=800,
        comments=120,
        watch_time_pct=0.72,
    )
    print(f"  Recorded performance, record_id={rid}")

    rid2 = knowledge_base.record_video_performance(
        video_id="test_vid_002",
        title="Will AI Take Your Job? The Truth",
        topic="AI jobs",
        hook_type="question",
        views=9500,
        likes=410,
        comments=95,
        watch_time_pct=0.65,
    )
    print(f"  Recorded performance, record_id={rid2}")

    # --- 2. Strategy context build ---
    print("\n[2] Building strategy context...")
    ctx = knowledge_base.build_strategy_context()
    print(f"  Videos tracked: {ctx['total_videos_tracked']}")
    print(f"  Avg views (14d): {ctx['avg_views_last_14d']}")
    print(f"  Top hook types: {ctx['top_hook_types']}")

    # --- 3. Experiment Engine: create & evaluate ---
    print("\n[3] Creating A/B experiment...")
    exp = experiment_engine.create_experiment(
        name="Hook: Shock vs Question (Test)",
        variable="hook_type",
        variant_a={"hook_type": "shock"},
        variant_b={"hook_type": "question"},
        hypothesis="Shock hooks get 30% more views than question hooks.",
    )
    print(f"  Experiment ID: {exp['id'][:12]}...")

    # Pick variants for 4 videos
    for i in range(4):
        v = experiment_engine.pick_variant(exp, video_index=i)
        print(f"  Video #{i} → Variant {v['label']}: {v['hook_type']}")

    # Evaluate with mock results
    results_a = [{"views": 14000}, {"views": 16000}]
    results_b = [{"views": 9000}, {"views": 11000}]
    evaluation = experiment_engine.evaluate_experiment(exp, results_a, results_b, min_samples=2)
    print(f"\n  Experiment Winner: {evaluation['winner']} "
          f"(A avg={evaluation['a_avg_views']:.0f} vs B avg={evaluation['b_avg_views']:.0f})")
    print(f"  Recommendation: {evaluation['recommendation']}")

    # --- 4. Full pipeline with Learning + Experiment agents (via Orchestrator) ---
    print("\n[4] Running Learning + Experiment workflow via Orchestrator...")
    orch = Orchestrator(channel_id="test")
    result = orch.execute_workflow(["learning", "experiment"])

    learning_out = result.get("learning", {})
    experiment_out = result.get("experiment", {})

    print(f"\n  Learning summary: {learning_out.get('analysis_summary', 'N/A')[:120]}...")
    print(f"  Active experiments: {experiment_out.get('experiment_count', 0)}")
    for exp_item in experiment_out.get("active_experiments", []):
        print(f"    - {exp_item['name']}")

    print("\n[PASS] Phase 5 complete!")


if __name__ == "__main__":
    test_phase5()
