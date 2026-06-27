import logging

log = logging.getLogger(__name__)

class CostTracker:
    def __init__(self):
        pass

    def log_usage(self, provider: str, tokens: int):
        log.info(f"[{provider}] Tokens used: {tokens}")
