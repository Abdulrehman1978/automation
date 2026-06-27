import functools
import logging

log = logging.getLogger(__name__)

def safe_execute(func):
    """Decorator to catch and log agent errors"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error(f"{func.__name__} failed: {e}", exc_info=True)
            return {"error": str(e)}
    return wrapper
