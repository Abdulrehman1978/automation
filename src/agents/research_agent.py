import logging
from .base_agent import BaseAgent
from utils.error_handler import safe_execute
from plugins.reddit_plugin import RedditPlugin

log = logging.getLogger(__name__)

class ResearchAgent(BaseAgent):
    def __init__(self, orchestrator=None):
        super().__init__(orchestrator)
        self.plugins = [RedditPlugin()]

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("ResearchAgent starting...")
        trends = []
        for plugin in self.plugins:
            trends.extend(plugin.fetch_data())
        
        log.info(f"ResearchAgent found {len(trends)} trends")
        
        result = {"trends": trends}
        
        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("research", result)
            
        return result
