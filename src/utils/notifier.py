import logging
import requests
from core.config import Config

log = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = getattr(Config, "TELEGRAM_BOT_TOKEN", None)
        self.chat_id = getattr(Config, "TELEGRAM_CHAT_ID", None)

    def send_message(self, message: str):
        if not self.bot_token or not self.chat_id:
            log.info(f"Telegram not configured. Console fallback:\n{message}")
            return
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            log.warning(f"Failed to send Telegram message: {e}. Fallback console:\n{message}")

notifier = TelegramNotifier()
