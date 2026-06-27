# Viral OS v2

An autonomous content growth engine designed to prioritize content quality, minimize risk, and operate resiliently.

Viral OS is a multi-agent system that completely automates the process of researching, ideating, writing, and packaging content for YouTube Shorts and Instagram Reels. 

## 🚀 Features

- **Autonomous Research**: Scrapes trending topics from Google Trends and InShorts, calculating growth velocity to prioritize high-potential topics.
- **Semantic Memory**: Uses ChromaDB to map ideas to embeddings, ensuring the system never generates repetitive content.
- **Judge & Critic Loop**: Ideas are evaluated on 6 dimensions (Clickability, Retention, Clarity, Emotion, Feasibility, Novelty). Sub-par ideas are sent back to the Script Agent for iterative rewriting.
- **Retention-Optimized Scripts**: Generates highly-structured video scripts focusing on pattern interrupts and curiosity gaps.
- **Platform-Specific SEO**: Generates tags, titles, and descriptions tailored for YouTube Shorts and Instagram Reels, validated via Pytrends.
- **Graceful Degradation**: Built to never crash. If APIs fail or rate limits are hit, the system automatically falls back to secondary models (Groq) or degrades gracefully to ensure the pipeline keeps running.
- **Real-Time Dashboard**: Includes a Flask-SocketIO dashboard to monitor live pipeline execution, manage approval queues, and view active trends.

## 🧠 Multi-Agent Architecture

The pipeline is orchestrated through several specialized agents:
1. **Research Agent**: Discovers trends and calculates velocity scores.
2. **Idea Agent**: Generates fresh concepts while avoiding duplicates.
3. **Judge Agent**: Evaluates ideas and triggers rewrite loops.
4. **Script Agent**: Structures the final narration.
5. **SEO Agent**: Appends platform-specific metadata.
6. **Learning Agent**: Ingests analytics from published videos and extracts actionable rules (e.g., "Question hooks get 18% better CTR") to improve future content.

## 🛠 Usage & Command Line Interface

We've unified all execution into a single entry point: `viral_os.py`.

### Start the Dashboard
```bash
python viral_os.py start-dashboard
```
Starts the dashboard on `http://localhost:5000`. You can monitor real-time pipeline execution, approve/reject generated packages, view trends, and download output JSONs.

### Run the Pipeline
```bash
python viral_os.py run-pipeline
```
Executes the main Orchestrator pipeline. If a run crashes, it will resume exactly where it left off.

### Publish a Video
```bash
python src/publish.py link <database_package_id> <path_to_mp4>
```
Links a rendered MP4 to an approved package and uploads it to YouTube as a Private video, updating the database status.

### Start the Scheduler
```bash
python viral_os.py start-scheduler
```
Starts `APScheduler` to automatically trigger the pipeline twice a day.

### Health Check
```bash
python viral_os.py health-check
```
Checks if the system has stalled, verifying that a pipeline run has completed within the last 24 hours.

## 📦 Installation

1. Clone the repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   # OR install core components directly:
   pip install google-api-python-client google-auth-oauthlib pytrends requests beautifulsoup4 sentence-transformers chromadb apscheduler flask-socketio eventlet
   ```
3. Copy `.env.example` to `.env` and fill in your API keys (Gemini, Groq, YouTube OAuth, etc.).
4. Run `python viral_os.py start-dashboard` to begin!

## 🧪 Resiliency

A core design principle of Viral OS v2 is that **the pipeline must never crash.**

- **Dependency Chaos**: If `chromadb` is missing, Semantic Memory falls back to a TF-IDF approach.
- **API Chaos**: If Google blocks `pytrends`, the SEO Agent falls back to standard generation without search volume validation.
- **Data Chaos**: If the Learning Agent encounters an empty database, it gracefully exits with `insufficient_data` instead of failing.
