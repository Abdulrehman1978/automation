"""
Trend Plugin — Multi-Source (No API Keys Required)
----------------------------------------------------
Fetches trending topics from free, open sources:
  1. Google Trends Daily RSS (no key needed)
  2. Hacker News Top Stories API (no key needed)
  3. Tech/Science RSS feeds (no key needed)
  4. Reddit PRAW (optional — add REDDIT_* keys to .env)

Falls back through sources gracefully if any fail.
"""
import logging
import os
import time
from urllib.request import urlopen, Request
from urllib.error import URLError
import json
import re

from .base_plugin import BasePlugin

log = logging.getLogger(__name__)

# ── RSS / API sources (all free, no keys) ────────────────────
GOOGLE_TRENDS_RSS = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
HN_TOP_API       = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_API      = "https://hacker-news.firebaseio.com/v0/item/{}.json"

RSS_FEEDS = [
    ("TechCrunch",  "https://techcrunch.com/feed/"),
    ("The Verge",   "https://www.theverge.com/rss/index.xml"),
    ("Wired",       "https://www.wired.com/feed/rss"),
    ("Ars Technica","https://feeds.arstechnica.com/arstechnica/index"),
]

# Fallback rich mock data — diverse topics across niches
MOCK_TRENDS = [
    {"source": "mock", "topic": "AI agents replacing software engineers in 2025", "score": 9800},
    {"source": "mock", "topic": "Open source LLMs beating GPT-4o on benchmarks",  "score": 8700},
    {"source": "mock", "topic": "Python 4.0 features that will change everything", "score": 7200},
    {"source": "mock", "topic": "Quantum computing just solved 10,000 year problem","score": 6500},
    {"source": "mock", "topic": "Tesla FSD finally works: real world test results",  "score": 5900},
    {"source": "mock", "topic": "Google Gemini 3 destroys GPT-5 in every test",     "score": 5400},
    {"source": "mock", "topic": "Apple Vision Pro 2 leaked specs are insane",        "score": 4800},
    {"source": "mock", "topic": "This AI makes $10k/month — no coding needed",       "score": 4300},
    {"source": "mock", "topic": "India overtakes US in AI researchers by 2026",      "score": 3900},
    {"source": "mock", "topic": "New battery charges phone 100% in 3 minutes",       "score": 3500},
]


def _fetch_url(url: str, timeout: int = 8) -> bytes | None:
    """Simple URL fetch with a user-agent header."""
    try:
        req = Request(url, headers={"User-Agent": "ViralOS/1.0 (trend research bot)"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, Exception) as e:
        log.debug(f"Fetch failed for {url}: {e}")
        return None


class TrendPlugin(BasePlugin):
    """Multi-source trend fetcher — works with zero API keys."""

    def fetch_data(self) -> list:
        trends = []

        # 1. Google Trends RSS
        gt = self._fetch_google_trends()
        trends.extend(gt)
        log.info(f"Google Trends: {len(gt)} topics")

        # 2. Hacker News Top Stories
        hn = self._fetch_hacker_news(limit=15)
        trends.extend(hn)
        log.info(f"Hacker News: {len(hn)} topics")

        # 3. Tech RSS feeds
        rss = self._fetch_rss_feeds()
        trends.extend(rss)
        log.info(f"RSS feeds: {len(rss)} topics")

        # 4. Real Reddit (optional)
        reddit = self._fetch_reddit_optional()
        trends.extend(reddit)

        if not trends:
            log.warning("All live sources failed — using rich mock data")
            return MOCK_TRENDS

        # Deduplicate similar topics and sort by score
        trends = self._deduplicate(trends)
        trends.sort(key=lambda x: x.get("score", 0), reverse=True)
        log.info(f"TrendPlugin: {len(trends)} total unique trends fetched")
        return trends[:25]

    # ────────────────────────────────────────────────────────────
    # Source implementations
    # ────────────────────────────────────────────────────────────

    def _fetch_google_trends(self) -> list:
        """Parse Google Trends daily RSS — no API key needed."""
        try:
            import feedparser
            raw = _fetch_url(GOOGLE_TRENDS_RSS)
            if not raw:
                return []
            feed = feedparser.parse(raw)
            results = []
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                # Get approx traffic from ht:approx_traffic tag if present
                traffic = 1000
                for tag in entry.get("tags", []):
                    val = tag.get("term", "")
                    if val.replace(",", "").replace("+", "").isdigit():
                        traffic = int(val.replace(",", "").replace("+", ""))
                        break
                if title:
                    results.append({"source": "google_trends", "topic": title, "score": traffic})
            return results
        except Exception as e:
            log.debug(f"Google Trends fetch error: {e}")
            return []

    def _fetch_hacker_news(self, limit: int = 15) -> list:
        """Fetch top HN stories — public API, no key."""
        try:
            raw = _fetch_url(HN_TOP_API)
            if not raw:
                return []
            ids = json.loads(raw)[:limit]
            results = []
            for story_id in ids:
                item_raw = _fetch_url(HN_ITEM_API.format(story_id))
                if not item_raw:
                    continue
                item = json.loads(item_raw)
                title = item.get("title", "").strip()
                score = item.get("score", 0)
                if title and score > 50:
                    results.append({
                        "source": "hacker_news",
                        "topic": title,
                        "score": score * 10,  # scale to match reddit scores
                        "url": item.get("url", ""),
                    })
                time.sleep(0.05)  # light rate-limiting
            return results
        except Exception as e:
            log.debug(f"HN fetch error: {e}")
            return []

    def _fetch_rss_feeds(self) -> list:
        """Parse tech RSS feeds for trending articles."""
        try:
            import feedparser
        except ImportError:
            return []

        results = []
        for source_name, url in RSS_FEEDS:
            try:
                raw = _fetch_url(url, timeout=6)
                if not raw:
                    continue
                feed = feedparser.parse(raw)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "").strip()
                    # Remove publication name suffixes
                    title = re.sub(r'\s*[\|–—]\s*\w[\w\s]*$', '', title).strip()
                    if title and len(title) > 10:
                        results.append({
                            "source": source_name.lower().replace(" ", "_"),
                            "topic": title,
                            "score": 500,
                        })
            except Exception as e:
                log.debug(f"RSS error for {source_name}: {e}")
        return results

    def _fetch_reddit_optional(self) -> list:
        """Use PRAW if credentials are available."""
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        if not client_id or not client_secret:
            return []
        try:
            import praw
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=os.getenv("REDDIT_USER_AGENT", "ViralOS/1.0"),
                check_for_async=False,
            )
            subreddits = os.getenv(
                "REDDIT_SUBREDDITS",
                "technology,artificial,MachineLearning,worldnews"
            ).split(",")
            results = []
            for sub in subreddits[:4]:
                for post in reddit.subreddit(sub.strip()).hot(limit=8):
                    if post.score >= 100:
                        results.append({
                            "source": f"reddit/r/{sub.strip()}",
                            "topic": post.title[:120],
                            "score": post.score,
                        })
            return results
        except Exception as e:
            log.debug(f"Reddit optional fetch: {e}")
            return []

    def _deduplicate(self, trends: list) -> list:
        """Remove near-duplicate topics using simple word-overlap."""
        seen_words: list[set] = []
        unique = []
        for t in trends:
            words = set(t["topic"].lower().split())
            # Skip if >60% overlap with an already-seen topic
            is_dup = any(
                len(words & seen) / max(len(words | seen), 1) > 0.6
                for seen in seen_words
            )
            if not is_dup:
                seen_words.append(words)
                unique.append(t)
        return unique


# Keep backwards-compatible alias so research_agent still imports RedditPlugin
RedditPlugin = TrendPlugin
