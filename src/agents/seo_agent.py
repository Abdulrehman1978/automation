"""
SEO Agent
---------
Generates optimised YouTube metadata packages for each script using Groq.
Outputs: title variants, description, tags, hashtags, thumbnail prompt,
posting time recommendation, and pinned comment.
"""
import json
import logging
from .base_agent import BaseAgent
from utils.error_handler import safe_execute
from utils.ai_client import ai_client

log = logging.getLogger(__name__)


class SEOAgent(BaseAgent):

    @safe_execute
    def execute(self, context: dict) -> dict:
        log.info("SEOAgent starting...")
        scripts = context.get("script", {}).get("scripts", [])
        learning_recs = context.get("learning", {}).get("recommendations", {})

        post_freq = learning_recs.get("recommended_posting_frequency", "2x per day")

        seo_packages = []
        for script in scripts:
            pkg = self._generate_seo(script, post_freq)
            seo_packages.append(pkg)

        log.info(f"SEOAgent generated {len(seo_packages)} SEO packages")
        result = {"seo_packages": seo_packages}

        if self.orchestrator:
            self.orchestrator.checkpoint.mark_step_done("seo", result)

        return result

    def _generate_seo(self, script: dict, post_freq: str) -> dict:
        title = script.get("idea_ref", "Unknown")
        narration = script.get("full_narration", "")[:500]

        prompt = f"""You are a YouTube SEO expert optimising a Shorts video.

Video title: {title}
Script excerpt: {narration}
Channel posting frequency: {post_freq}

Generate YouTube metadata. Return ONLY valid JSON:
{{
  "final_title": "<optimised title with power word, under 70 chars>",
  "title_variants": ["<alt title 1>", "<alt title 2>"],
  "description": "<150-200 char description with keywords and CTA>",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
  "thumbnail_prompt": "<DALL-E/MJ prompt for a high-CTR thumbnail>",
  "best_posting_time": "<e.g. 6PM IST weekdays>",
  "pinned_comment": "<engaging first comment to pin>"
}}"""

        raw = ai_client.generate(
            prompt,
            provider="groq",
            system_prompt="You are a YouTube SEO expert. Return only valid JSON.",
            preferred_model="llama-3.1-8b-instant",
        )

        if raw:
            try:
                cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                data = json.loads(cleaned)
                data["script_ref"] = title
                
                # Validate with pytrends
                main_tag = data.get("tags", [title])[0]
                self._validate_with_pytrends(main_tag)
                
                return data
            except json.JSONDecodeError:
                log.warning(f"SEOAgent: JSON parse failed for '{title}'")

        # Fallback
        return {
            "script_ref": title,
            "final_title": f"{title} | Mind Blown",
            "title_variants": [title, f"The Truth About {title}"],
            "description": f"Learn about {title}. Subscribe for more viral content!",
            "tags": ["shorts", "viral", "tech", "trending", "facts", "mindblown"],
            "hashtags": ["#shorts", "#viral", "#trending"],
            "thumbnail_prompt": f"High contrast split face shocked expression, text '{title}'",
            "best_posting_time": "6PM IST weekdays",
            "pinned_comment": "What do you think? Drop your take below 👇",
        }

    def _validate_with_pytrends(self, keyword: str) -> bool:
        try:
            from pytrends.request import TrendReq
            pytrend = TrendReq(hl='en-US', tz=360, timeout=(5,10))
            suggestions = pytrend.suggestions(keyword)
            if suggestions:
                log.info(f"pytrends validation passed for keyword: '{keyword}'")
                return True
            else:
                log.info(f"pytrends validation: '{keyword}' might have low volume.")
                return False
        except ImportError:
            log.warning("pytrends is not installed. Falling back to unvalidated metadata.")
            return True
        except Exception as e:
            log.warning(f"pytrends validation failed or rate-limited: {e}. Falling back to unvalidated metadata.")
            return True
