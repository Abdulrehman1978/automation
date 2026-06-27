"""
AI Client — Multi-Provider with Auto-Fallback
----------------------------------------------
Provider priority (highest quota first):
  1. Groq   — llama-3.3-70b-versatile  (14,400 req/day free, very fast)
  2. Gemini — 2.0-flash-lite → 2.0-flash → 2.5-flash (20 req/day free)

Features:
  - Automatic retry with exponential back-off on 429 rate limits
  - Falls back to next provider/model on exhaustion
  - Returns empty string on total failure (never raises in callers)
"""

import re
import time
import logging

from core.config import Config

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq model chain (fast → powerful)
# ---------------------------------------------------------------------------
_GROQ_MODELS = [
    "llama-3.1-8b-instant",       # fastest, lowest cost
    "llama-3.3-70b-versatile",     # best quality on free tier
    "mixtral-8x7b-32768",          # fallback
]

# ---------------------------------------------------------------------------
# Gemini model chain (lite → capable)
# ---------------------------------------------------------------------------
_GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]


def _parse_retry_delay(error_str: str) -> int:
    """Extract retry-after seconds from a 429 error message."""
    match = re.search(
        r"retry[_\s](?:after|delay)['\"]?\s*[:=]\s*['\"]?(\d+)",
        error_str, re.IGNORECASE
    )
    return int(match.group(1)) if match else 0


class AIClient:
    def __init__(self):
        self._groq = None
        self._gemini = None
        self._init_groq()
        self._init_gemini()

    # ------------------------------------------------------------------ #
    # Initialisation                                                       #
    # ------------------------------------------------------------------ #

    def _init_groq(self):
        if not Config.GROQ_API_KEY:
            log.warning("GROQ_API_KEY not set — Groq disabled")
            return
        try:
            from groq import Groq
            self._groq = Groq(api_key=Config.GROQ_API_KEY)
            log.info("Groq client initialised (primary provider)")
        except Exception as e:
            log.error(f"Failed to init Groq: {e}")

    def _init_gemini(self):
        if not Config.GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY not set — Gemini disabled")
            return
        try:
            from google import genai as genai_sdk
            self._gemini = genai_sdk.Client(api_key=Config.GEMINI_API_KEY)
            log.info("Gemini client initialised (secondary provider)")
        except Exception as e:
            log.error(f"Failed to init Gemini: {e}")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        prompt: str,
        provider: str = "auto",
        max_retries: int = 2,
        preferred_model: str = None,
        system_prompt: str = None,
    ) -> str:
        """
        Generate text with automatic provider fallback.

        Args:
            prompt: The user prompt.
            provider: "auto" (Groq→Gemini), "groq", or "gemini".
            max_retries: Retries per model before moving to next.
            preferred_model: Override the default model for the chosen provider.
            system_prompt: Optional system/role instruction (Groq supports this natively).

        Returns:
            Generated text string, or "" on total failure.
        """
        if provider == "groq":
            return self._try_groq(prompt, system_prompt, max_retries, preferred_model) or ""
        if provider == "gemini":
            return self._try_gemini(prompt, max_retries, preferred_model) or ""

        # "auto" — try Groq first, then Gemini
        result = self._try_groq(prompt, system_prompt, max_retries, preferred_model)
        if result:
            return result
        log.warning("Groq exhausted — falling back to Gemini")
        return self._try_gemini(prompt, max_retries, preferred_model) or ""

    # ------------------------------------------------------------------ #
    # Provider implementations                                            #
    # ------------------------------------------------------------------ #

    def _try_groq(
        self,
        prompt: str,
        system_prompt: str = None,
        max_retries: int = 2,
        preferred_model: str = None,
    ) -> str:
        if not self._groq:
            return ""

        models = (
            [preferred_model] + [m for m in _GROQ_MODELS if m != preferred_model]
            if preferred_model else list(_GROQ_MODELS)
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in models:
            for attempt in range(max_retries):
                try:
                    resp = self._groq.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2048,
                    )
                    text = resp.choices[0].message.content or ""
                    log.debug(f"[Groq/{model}] Generated {len(text)} chars")
                    return text
                except Exception as e:
                    err = str(e)
                    if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
                        delay = _parse_retry_delay(err) or (2 ** attempt * 5)
                        wait = min(delay, 30)
                        log.warning(f"[Groq/{model}] Rate limit (attempt {attempt+1}). Waiting {wait}s...")
                        if attempt < max_retries - 1:
                            time.sleep(wait)
                        else:
                            log.warning(f"[Groq/{model}] Giving up, trying next model.")
                    elif "model_not_found" in err.lower() or "404" in err:
                        log.warning(f"[Groq] Model {model} not found, trying next.")
                        break
                    else:
                        log.error(f"[Groq/{model}] Error: {e}")
                        break  # Hard error on this model — move on
        return ""

    def _try_gemini(
        self,
        prompt: str,
        max_retries: int = 2,
        preferred_model: str = None,
    ) -> str:
        if not self._gemini:
            return ""

        models = (
            [preferred_model] + [m for m in _GEMINI_MODELS if m != preferred_model]
            if preferred_model else list(_GEMINI_MODELS)
        )

        for model in models:
            for attempt in range(max_retries):
                try:
                    resp = self._gemini.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    text = resp.text or ""
                    log.debug(f"[Gemini/{model}] Generated {len(text)} chars")
                    return text
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        delay = _parse_retry_delay(err) or (2 ** attempt * 10)
                        wait = min(delay, 60)
                        log.warning(f"[Gemini/{model}] Rate limit (attempt {attempt+1}). Waiting {wait}s...")
                        if attempt < max_retries - 1:
                            time.sleep(wait)
                        else:
                            log.warning(f"[Gemini/{model}] Giving up, trying next model.")
                    elif "404" in err or "NOT_FOUND" in err:
                        log.warning(f"[Gemini] Model {model} not found, trying next.")
                        break
                    else:
                        log.error(f"[Gemini/{model}] Error: {e}")
                        break
        return ""


# Global singleton
ai_client = AIClient()
