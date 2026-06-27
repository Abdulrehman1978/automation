# Viral OS: Complete System Architecture & Documentation

**Version:** 1.0 (MVP)  
**Objective:** An autonomous, AI-driven content operating system that discovers trends, generates YouTube Shorts scripts, optimizes metadata, learns from performance, and handles uploads.

---

## 1. System Overview

Viral OS is designed as a multi-agent pipeline. It operates by breaking down the content creation process into distinct steps (agents) that pass structured JSON data (context) down a pipeline. 

The entire system is glued together by an **Orchestrator** which manages state, checkpointing, and agent execution.

### Key Features
- **Keyless Trend Discovery**: Scrapes Hacker News, Google Trends, and RSS feeds without needing API keys.
- **Multi-Provider AI Fallback**: Uses Groq (fast, high quota) as primary, falling back to Gemini (slower, stricter limits) if rate-limited.
- **Autonomous Scheduling**: Runs completely hands-free via a chron/sleep loop.
- **A/B Testing & Learning Engine**: Uses historical performance data to intelligently pick hooks, titles, and topics.
- **Flask Dashboard**: A premium UI for monitoring trends, approving scripts, and tracking experiments.

---

## 2. The Multi-Agent Pipeline

The core logic resides in `src/agents/`. Each agent inherits from `BaseAgent` and implements an `execute(context: dict) -> dict` method.

### Agent 1: Research Agent (`research_agent.py`)
- **Role**: Discovers what is currently going viral on the internet.
- **Mechanics**: Calls `TrendPlugin` to aggregate topics from Google Trends RSS, Hacker News, and tech news feeds. 
- **Output**: A raw list of trending topics and their engagement scores.

### Agent 2: Idea Agent (`idea_agent.py`)
- **Role**: Transforms raw trends into video concepts.
- **Mechanics**: 
  1. Uses `TrendDeduplicator` (TF-IDF semantic memory) to filter out topics we've recently covered.
  2. Uses `predict_lifetimes()` to ensure the trend isn't dying.
  3. Uses Groq to generate a hook, title, and angle.
- **Output**: A list of structured `idea` objects.

### Agent 3: Judge Agent (`judge_agent.py`)
- **Role**: Quality control.
- **Mechanics**: Prompts the AI to act as a strict virality judge. Evaluates ideas on emotional hook strength, shareability, and production simplicity. Ideas scoring below `65/100` are discarded.
- **Output**: A filtered list of `approved_ideas`.

### Agent 4: Script Agent (`script_agent.py`)
- **Role**: Writes the actual video content.
- **Mechanics**: Expands the approved idea into a 60-second script structured as JSON: `hook_5s`, `body_40s`, `cta_15s`, `visual_cues`, and `broll_suggestions`.
- **Output**: A list of fully written `scripts`.

### Agent 5: SEO Agent (`seo_agent.py`)
- **Role**: YouTube optimization.
- **Mechanics**: Generates click-optimized titles, descriptions, hashtags, an AI image generation prompt for the thumbnail, and optimal posting times.
- **Output**: The final `seo_packages`.

---

## 3. Intelligence & Learning (Phase 5)

Viral OS doesn't just generate content; it learns what works.

### Knowledge Base (`knowledge_base.py`)
- Interfaces with the SQLite database to track video performance (views, likes, retention).
- Computes aggregate metrics (e.g., "Do 'Shock' hooks perform better than 'Question' hooks?").

### Learning Agent (`learning_agent.py`)
- Runs *before* the Idea Agent.
- Analyzes the Knowledge Base and provides explicit recommendations (e.g., `avoid_topics: ["Crypto"]`, `best_hook_types: ["Statistic"]`).
- Feeds these rules directly into the Idea Agent's prompt.

### Experiment Engine & Agent (`experiment_engine.py`, `experiment_agent.py`)
- Automatically designs A/B tests (e.g., testing short vs. long titles).
- Tracks variants in the database and evaluates statistical confidence to declare a winner.

---

## 4. YouTube Uploader (`youtube_uploader.py`)

- **Live Mode**: If `credentials/youtube_oauth.json` and a valid token exist, it connects via the Google API Python client to upload video files directly to YouTube.
- **Save Mode**: If a video file isn't provided (since the AI doesn't generate the physical video yet), the system saves the rich JSON package to the `outputs/` folder.
- **Publisher Script**: A standalone `src/publish.py` allows a human editor to easily link a rendered `.mp4` file with an output JSON to instantly trigger the YouTube upload.

---

## 5. Web Dashboard (`app.py`)

A local Flask web app that provides a control center.
- **Real-time Pipeline Logs**: View the agents thinking and executing live.
- **Approval Queue**: Review generated scripts and manually approve/reject them.
- **Trends & Experiments**: Monitor active trends and A/B test results in a UI.

---

## 6. How to Improve It (Suggestions to ask for)

If you are sharing this architecture with developers, creators, or AI engineers to get feedback, here are the best questions to ask them:

### A. Fully Autonomous Video Generation (Phase 8)
*Current state: We generate the script, a human edits the video.*
- "How should we integrate ElevenLabs for TTS and Runway/Luma for video generation?"
- "What's the best way to auto-edit B-roll and captions using FFmpeg or MoviePy in Python?"

### B. Better Semantic Memory & Deduplication
*Current state: We use basic TF-IDF to prevent generating the same video twice.*
- "Should we replace TF-IDF with ChromaDB or Pinecone and OpenAI embeddings for better semantic deduplication?"
- "How can we use RAG to recall past scripts to ensure the AI doesn't repeat the exact same jokes?"

### C. Advanced Agent Routing (LangGraph / AutoGen)
*Current state: Agents run in a linear, rigid pipeline via our custom Orchestrator.*
- "Would moving the pipeline to LangChain/LangGraph or Microsoft AutoGen make the agents more collaborative?"
- "Should the Judge Agent be able to send a script *back* to the Script Agent for a rewrite instead of just discarding it?"

### D. Multi-Platform Distribution
*Current state: YouTube only.*
- "What's the most stable API approach to simultaneously distribute these packages to TikTok and Instagram Reels?"
- "How can we adapt the SEO Agent to generate platform-specific metadata (e.g., TikTok hashtags vs YouTube tags)?"

### E. Real-Time Analytics Ingestion
*Current state: The Knowledge Base exists, but performance data is manually mocked for tests.*
- "How do we best set up a CRON job to pull live YouTube Analytics API data back into our Knowledge Base so the Learning Agent can train on real-world view counts?"
