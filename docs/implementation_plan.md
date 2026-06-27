# Viral Content Operating System - Final Implementation Plan

## Goal Description
Build the MVP for the Viral Content Operating System in `c:\crm-final\viral-os\`, focusing on the core pipeline to produce upload-ready packages using a robust, multi-provider AI strategy (Gemini + Groq + OpenRouter) and local sentence transformers for embeddings.

## Revised Architecture & Strategy
- **Workspace:** Isolated in `c:\crm-final\viral-os\`
- **MVP Focus:** Research -> Idea -> Judge -> Script -> SEO -> Upload Package. Advanced features (Voice, Captions, Learning, Experiments) will follow the MVP.
- **AI Providers:** 
  - Primary: Google Gemini 1.5 Flash
  - Secondary (Judge): Groq (Mixtral/Llama3)
  - Tertiary: OpenRouter
  - Embeddings: HuggingFace Inference (local)
- **Plugin Scope:** Start with Reddit, YouTube, and Google Trends.

## Phased Execution Plan

### Phase 0: Setup & Validation (MVP)
- Create `viral-os` directory structure.
- Create `.env.example` and `requirements.txt`.
- Create `setup.py` for environment validation and initialization.

### Phase 1: Core Foundation (MVP)
- Implement `src/core/database.py` and `src/core/semantic_memory.py`.
- Verify database and embeddings function locally.

### Phase 2: Agent Foundation & Research (MVP)
- Implement `src/core/orchestrator.py`, `checkpoint.py`, `config.py`, `cost_tracker.py`.
- Implement `src/agents/base_agent.py` and `src/utils/ai_client.py`.
- Implement `src/plugins/base_plugin.py`, `reddit_plugin.py`, and `src/agents/research_agent.py`.

### Phase 3: Idea Pipeline (MVP)
- Implement `trend_deduplicator.py`, `trend_lifetime.py`, `priority_scorer.py`.
- Implement `hook_selector.py` + hook JSONs.
- Implement `idea_agent.py` and `judge_agent.py`.

### Phase 4: Content Generation (MVP)
- Implement `script_agent.py` and `seo_agent.py`.

### Phase 5: Intelligence & Learning (Post-MVP)
- Implement `knowledge_base.py`, `learning_agent.py`, `experiment_agent.py`, `experiment_engine.py`.

### Phase 6: Dashboard & Interface (MVP subset)
- Minimal Flask dashboard for pipeline status, active trends, and approval queue.

### Phase 7: Integration & Deployment (MVP subset)
- Uploaders (`youtube_uploader.py`), `main.py` orchestrator, GitHub actions.

## Verification Plan
- Use isolated `test_phaseX.py` scripts for each phase to ensure the foundation is solid before moving to the next.
- Include `setup.py validate` to check all API keys and dependencies early.
