# Viral Content Operating System — Complete Walkthrough

**Status: All 7 Phases Complete ✅**  
Last updated: 2026-06-27

---

## 🏗️ Architecture Overview

```
Research → Idea → Judge → Script → SEO → [Learning → Experiment]
                                     ↓
                              Outputs (JSON) → YouTube Upload
```

### AI Providers
| Provider | Role | Quota |
|---|---|---|
| **Groq** (`llama-3.1-8b-instant`, `llama-3.3-70b`) | Primary — all agents | ~14,400 req/day free |
| **Gemini** (`gemini-2.5-flash` etc.) | Fallback when Groq is rate-limited | 20 req/day free |

---

## 📁 Project Structure

```
c:\crm-final\viral-os\
├── src/
│   ├── agents/
│   │   ├── research_agent.py     # Fetches Reddit trends
│   │   ├── idea_agent.py         # Generates video concepts (Groq)
│   │   ├── judge_agent.py        # Scores & filters ideas (Groq)
│   │   ├── script_agent.py       # Full 60s scripts (Groq)
│   │   ├── seo_agent.py          # YouTube metadata (Groq)
│   │   ├── learning_agent.py     # Analyses past performance (Phase 5)
│   │   └── experiment_agent.py   # Designs A/B tests (Phase 5)
│   ├── core/
│   │   ├── database.py           # SQLite with full schema
│   │   ├── orchestrator.py       # Workflow runner + checkpointing
│   │   ├── checkpoint.py         # Run state persistence
│   │   ├── semantic_memory.py    # Duplicate detection (embeddings)
│   │   └── config.py             # Env var loader
│   ├── intelligence/
│   │   ├── knowledge_base.py     # Performance data layer
│   │   ├── trend_deduplicator.py
│   │   ├── trend_lifetime.py
│   │   └── priority_scorer.py
│   ├── experiments/
│   │   └── experiment_engine.py  # A/B test lifecycle
│   ├── generation/
│   │   └── hook_selector.py      # Hook templates
│   ├── plugins/
│   │   ├── reddit_plugin.py      # PRAW (real) + mock fallback
│   │   └── base_plugin.py
│   ├── upload/
│   │   └── youtube_uploader.py   # OAuth2 upload + save-only mode
│   ├── dashboard/
│   │   ├── app.py                # Flask backend (full API)
│   │   └── templates/index.html  # Dark-mode premium UI
│   ├── utils/
│   │   ├── ai_client.py          # Multi-provider client (Groq→Gemini)
│   │   └── error_handler.py
│   └── main.py                   # CLI pipeline runner
├── outputs/                      # Generated JSON packages land here
├── data/viral_os.db              # SQLite database
├── .env                          # Your API keys
├── requirements.txt
└── test_phase*.py                # Phase-by-phase test scripts
```

---

## 🚀 How to Run

### Activate environment
```powershell
cd c:\crm-final\viral-os
venv\Scripts\activate
```

### Single pipeline run
```powershell
python src\main.py
```

### With Learning + Experiment agents
```powershell
python src\main.py --with-learning
```

### Scheduled runs (every 6 hours)
```powershell
python src\main.py --schedule 6h
```

### Daily at 9 AM
```powershell
python src\main.py --schedule 09:00
```

### Start the dashboard
```powershell
python src\main.py --dashboard
# Open http://localhost:5000
```

---

## 📊 Sample Pipeline Output

A real run produced 5 AI-generated packages including:

| Title | Score | Tags |
|---|---|---|
| AI Jobs: Will Software Engineers Be Replaced? | 80 | #AIJobs #SoftwareEngineering |
| LLMs Outshine GPT-4: Open Source Models Dominate | 80 | #LLMs #GPT4 |
| Python 4.0 Speed Boost: Top 5 Features! | 80 | #python40 |
| Quantum Computing Breakthrough! | 85 | #QuantumComputing |
| Tesla Autopilot Hacked! | 85 | #TeslaHacks |

Each package includes: title, title variants, description, 8 tags, hashtags, thumbnail prompt, best posting time, and pinned comment.

---

## 🔑 Keys Needed for Full Functionality

| Feature | Key Needed | Where to get it |
|---|---|---|
| Live Reddit trends | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps |
| YouTube live uploads | OAuth credentials JSON | Google Cloud Console |

---

## ✅ Phase Completion Status

| Phase | Description | Status |
|---|---|---|
| 0 | Setup & Validation | ✅ Done |
| 1 | Database & Semantic Memory | ✅ Done |
| 2 | Orchestrator & Research Agent | ✅ Done |
| 3 | Idea + Judge Agents | ✅ Done |
| 4 | Script + SEO Agents | ✅ Done |
| 5 | Learning Agent + Experiment Engine | ✅ Done |
| 6 | Full Dashboard (dark UI, live logs) | ✅ Done |
| 7 | YouTube Uploader + Scheduler + CLI | ✅ Done |
