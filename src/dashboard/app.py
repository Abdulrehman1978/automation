"""
Viral OS Dashboard — Flask Backend
-----------------------------------
Full dashboard with:
  - Pipeline trigger (runs in background thread)
  - Real-time status via SSE / polling
  - Approval queue with approve/reject
  - A/B experiment viewer
  - Learning agent recommendations display
  - Output package download
"""
import json
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file
from flask_socketio import SocketIO, emit

# Add src to path when running directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.database import db

log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# ── In-memory pipeline state ───────────────────────────────────────────────
_pipeline_lock = threading.Lock()
_pipeline_state = {
    "status": "idle",          # idle | running | done | error
    "current_step": None,
    "steps_done": [],
    "started_at": None,
    "finished_at": None,
    "last_result": None,
    "log_lines": [],
}


def _update_state(**kwargs):
    with _pipeline_lock:
        _pipeline_state.update(kwargs)


def _log(msg: str):
    with _pipeline_lock:
        line = f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}"
        _pipeline_state["log_lines"].append(line)
        if len(_pipeline_state["log_lines"]) > 200:
            _pipeline_state["log_lines"] = _pipeline_state["log_lines"][-200:]
    socketio.emit("log", {"line": line})
    socketio.emit("status", dict(_pipeline_state))


def _run_pipeline_thread(channel_id: str, workflow: list, save_output: bool):
    """Background thread that runs the full Orchestrator workflow."""
    try:
        from core.orchestrator import Orchestrator

        _update_state(status="running", started_at=datetime.utcnow().isoformat(),
                      steps_done=[], log_lines=[], current_step=None)
        _log("Pipeline started...")

        orch = Orchestrator(channel_id=channel_id)
        results = {}

        for step in workflow:
            _update_state(current_step=step)
            _log(f"Running step: {step}...")

            step_result = orch.execute_workflow([step])
            results[step] = step_result.get(step, {})

            if "error" in step_result.get(step, {}):
                _log(f"ERROR in {step}: {step_result[step]['error']}")
                _update_state(status="error", current_step=None, last_result=results)
                return

            _pipeline_state["steps_done"].append(step)
            _log(f"Step '{step}' complete.")

        # Save output packages to disk
        if save_output:
            _save_output_packages(results, channel_id)

        # Queue SEO packages for approval
        seo_packages = results.get("seo", {}).get("seo_packages", [])
        for pkg in seo_packages:
            try:
                db.add_to_approval_queue({
                    "channel_id": channel_id,
                    "title": pkg.get("final_title", "Unknown"),
                    "concept": pkg.get("description", ""),
                    "thumbnail_url": "",
                    **pkg,
                })
                _log(f"Queued for approval: {pkg.get('final_title')}")
            except Exception as e:
                _log(f"Could not queue package: {e}")

        _update_state(status="done", current_step=None, finished_at=datetime.utcnow().isoformat(),
                      last_result=results)
        _log(f"Pipeline complete! {len(seo_packages)} packages ready.")

    except Exception as e:
        _log(f"FATAL ERROR: {e}")
        _update_state(status="error", current_step=None)


def _save_output_packages(results: dict, channel_id: str):
    """Save pipeline output to outputs/ directory as JSON."""
    out_dir = Path(__file__).parent.parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"pipeline_{channel_id}_{timestamp}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    _log(f"Output saved to {out_file.name}")
    return str(out_file)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    pending = db.get_pending_approvals()
    trends = db.get_top_priority_trends()
    experiments = db.get_running_experiments()
    knowledge = db.get_active_knowledge()
    state = dict(_pipeline_state)
    state["log_lines"] = state["log_lines"][-50:]  # last 50 for template
    return render_template(
        "index.html",
        pending=pending,
        trends=trends,
        experiments=experiments,
        knowledge=knowledge,
        state=state,
    )


@app.route("/api/status")
def api_status():
    with _pipeline_lock:
        return jsonify(dict(_pipeline_state))


@app.route("/api/pipeline/run", methods=["POST"])
def api_run_pipeline():
    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            return jsonify({"error": "Pipeline is already running"}), 409

    data = request.get_json(silent=True) or {}
    channel_id = data.get("channel_id", "main")
    workflow = data.get("workflow", ["research", "idea", "judge", "script", "seo"])
    save_output = data.get("save_output", True)

    t = threading.Thread(
        target=_run_pipeline_thread,
        args=(channel_id, workflow, save_output),
        daemon=True,
    )
    t.start()
    return jsonify({"status": "started", "workflow": workflow})


@app.route("/api/pipeline/stop", methods=["POST"])
def api_stop_pipeline():
    _update_state(status="idle", current_step=None)
    _log("Pipeline manually stopped.")
    return jsonify({"status": "stopped"})


@app.route("/api/pipeline/logs")
def api_logs():
    with _pipeline_lock:
        return jsonify({"logs": _pipeline_state["log_lines"]})


@app.route("/api/trends")
def api_trends():
    return jsonify(db.get_top_priority_trends())


@app.route("/api/approvals")
def api_approvals():
    return jsonify(db.get_pending_approvals())


@app.route("/api/approve/<package_id>", methods=["POST"])
def api_approve(package_id):
    db.approve_package(package_id)
    return jsonify({"status": "approved", "id": package_id})


@app.route("/api/reject/<package_id>", methods=["POST"])
def api_reject(package_id):
    db.reject_package(package_id)
    return jsonify({"status": "rejected", "id": package_id})


@app.route("/api/experiments")
def api_experiments():
    return jsonify(db.get_running_experiments())


@app.route("/api/knowledge")
def api_knowledge():
    return jsonify(db.get_active_knowledge())


@app.route("/api/last-output")
def api_last_output():
    """Return the last pipeline result JSON."""
    with _pipeline_lock:
        return jsonify(_pipeline_state.get("last_result") or {})


@app.route("/api/outputs")
def api_outputs():
    """List available saved output files."""
    out_dir = Path(__file__).parent.parent.parent / "outputs"
    if not out_dir.exists():
        return jsonify([])
    files = sorted(out_dir.glob("pipeline_*.json"), reverse=True)
    return jsonify([
        {"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1),
         "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
        for f in files[:20]
    ])


@app.route("/api/outputs/<filename>")
def api_download_output(filename):
    """Download a saved output file."""
    out_dir = Path(__file__).parent.parent.parent / "outputs"
    file_path = out_dir / filename
    if not file_path.exists() or not file_path.name.startswith("pipeline_"):
        return jsonify({"error": "Not found"}), 404
    return send_file(str(file_path), as_attachment=True)


# ── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    print("\n  Viral OS Dashboard → http://localhost:5000\n")
    socketio.run(app, debug=False, port=5000)
