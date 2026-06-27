import json
import uuid
from pathlib import Path

class CheckpointManager:
    def __init__(self, channel_id="main"):
        self.channel_id = channel_id
        self.checkpoint_dir = Path("data/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = None
        self.state = {}

    def start_run(self, resume_run_id=None):
        if resume_run_id:
            self.run_id = resume_run_id
            self._load()
        else:
            self.run_id = uuid.uuid4().hex
            self.state = {"completed_steps": [], "outputs": {}}
            self._save()
        return self.run_id

    def _get_path(self):
        return self.checkpoint_dir / f"{self.run_id}.json"

    def _save(self):
        with open(self._get_path(), "w") as f:
            json.dump(self.state, f, indent=2)

    def _load(self):
        path = self._get_path()
        if path.exists():
            with open(path, "r") as f:
                self.state = json.load(f)
        else:
            self.state = {"completed_steps": [], "outputs": {}}

    def mark_step_done(self, step_name, output):
        if step_name not in self.state.get("completed_steps", []):
            self.state["completed_steps"].append(step_name)
        self.state["outputs"][step_name] = output
        self._save()

    def is_step_done(self, step_name):
        return step_name in self.state.get("completed_steps", [])

    def get_step_output(self, step_name):
        return self.state.get("outputs", {}).get(step_name)
