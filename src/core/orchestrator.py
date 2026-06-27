import logging
from typing import Dict, List
from .checkpoint import CheckpointManager
from .cost_tracker import CostTracker

log = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, channel_id: str = "main", resume_run_id: str = None):
        self.channel_id = channel_id
        self.checkpoint = CheckpointManager(channel_id)
        self.cost_tracker = CostTracker()
        
        self.run_id = self.checkpoint.start_run(resume_run_id)
        
        self.agents = {}
        self._register_agents()
        
    def _register_agents(self):
        from agents.research_agent import ResearchAgent
        from agents.idea_agent import IdeaAgent
        from agents.judge_agent import JudgeAgent
        from agents.script_agent import ScriptAgent
        from agents.seo_agent import SEOAgent
        from agents.learning_agent import LearningAgent
        from agents.experiment_agent import ExperimentAgent
        self.agents = {
            "research": ResearchAgent(self),
            "idea": IdeaAgent(self),
            "judge": JudgeAgent(self),
            "script": ScriptAgent(self),
            "seo": SEOAgent(self),
            "learning": LearningAgent(self),
            "experiment": ExperimentAgent(self),
        }

    def execute_workflow(self, workflow: List[str]) -> Dict:
        log.info(f"🎬 Starting workflow: {' -> '.join(workflow)}")
        results = {}
        
        context = {"channel_id": self.channel_id, "run_id": self.run_id}
        
        for step in workflow:
            if self.checkpoint.is_step_done(step):
                log.info(f"  ⏩ Skipping {step} (checkpoint)")
                results[step] = self.checkpoint.get_step_output(step)
                # merge into context so next agents have access
                context[step] = results[step]
                continue
                
            agent = self.agents.get(step)
            if not agent:
                log.error(f"Agent {step} not found!")
                continue
                
            log.info(f"  ▶️ Executing {step}...")
            step_result = agent.execute(context)
            
            if "error" in step_result:
                log.error(f"Workflow halted at {step} due to error: {step_result['error']}")
                break
                
            results[step] = step_result
            context[step] = step_result
            
        # If we successfully finished all steps in the requested workflow
        if not any("error" in results.get(s, {}) for s in workflow):
            self.checkpoint.complete_run()
            
        return results
