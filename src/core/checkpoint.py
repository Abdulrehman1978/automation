import json
import uuid
from .database import Database

class CheckpointManager:
    def __init__(self, channel_id="main"):
        self.channel_id = channel_id
        self.db = Database()
        self.run_id = None
        self.state = {"completed_steps": [], "outputs": {}}

    def start_run(self, resume_run_id=None):
        if resume_run_id:
            self.run_id = resume_run_id
            self._load()
            
            # Re-activate the run
            if self.run_id:
                with self.db.conn() as c:
                    c.execute(
                        "UPDATE pipeline_runs SET status = 'running' WHERE run_id = ?",
                        (self.run_id,)
                    )
        else:
            self.run_id = uuid.uuid4().hex
            self.state = {"completed_steps": [], "outputs": {}}
            self._save()
        return self.run_id

    def _save(self):
        completed_json = json.dumps(self.state.get("completed_steps", []))
        outputs_json = json.dumps(self.state.get("outputs", {}))
        
        with self.db.conn() as c:
            existing = c.execute("SELECT id FROM pipeline_runs WHERE run_id = ?", (self.run_id,)).fetchone()
            if existing:
                c.execute("""
                    UPDATE pipeline_runs 
                    SET completed_steps = ?, step_data = ?
                    WHERE run_id = ?
                """, (completed_json, outputs_json, self.run_id))
            else:
                c.execute("""
                    INSERT INTO pipeline_runs (run_id, channel_id, status, completed_steps, step_data)
                    VALUES (?, ?, 'running', ?, ?)
                """, (self.run_id, self.channel_id, completed_json, outputs_json))

    def _load(self):
        with self.db.conn() as c:
            row = c.execute("SELECT completed_steps, step_data FROM pipeline_runs WHERE run_id = ?", (self.run_id,)).fetchone()
            if row:
                self.state = {
                    "completed_steps": json.loads(row["completed_steps"]) if row["completed_steps"] else [],
                    "outputs": json.loads(row["step_data"]) if row["step_data"] else {}
                }
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
        
    def complete_run(self):
        with self.db.conn() as c:
            c.execute(
                "UPDATE pipeline_runs SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE run_id = ?",
                (self.run_id,)
            )

