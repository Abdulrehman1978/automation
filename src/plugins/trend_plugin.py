import logging
import requests
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
from .base_plugin import BasePlugin

log = logging.getLogger(__name__)

class TrendPlugin(BasePlugin):
    """
    Scrapes Inshorts and uses Google Trends IN to find high-velocity trends.
    Calculates a combined velocity and engagement score.
    """
    def __init__(self):
        self.mock_fallback = [
            {
                "topic": "AI Video Generation",
                "source": "mock",
                "velocity_score": 95,
                "engagement_score": 85,
                "total_score": 90,
                "url": ""
            },
            {
                "topic": "SpaceX Mars Mission",
                "source": "mock",
                "velocity_score": 80,
                "engagement_score": 70,
                "total_score": 75,
                "url": ""
            }
        ]

    def fetch_data(self) -> list:
        trends = []
        try:
            # 1. Scrape Inshorts
            inshorts_data = self._scrape_inshorts()
            trends.extend(inshorts_data)
            
            # 2. Fetch Google Trends IN
            gtrends_data = self._fetch_google_trends()
            trends.extend(gtrends_data)
            
            if not trends:
                raise Exception("No trends fetched")
                
            # Sort by total_score descending
            trends.sort(key=lambda x: x.get("total_score", 0), reverse=True)
            return trends
            
        except Exception as e:
            log.warning(f"TrendPlugin failed due to network/parsing error: {e}. Falling back to mock data.")
            return self.mock_fallback

    def _scrape_inshorts(self) -> list:
        results = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get('https://inshorts.com/en/read', headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.find_all('div', class_='news-card', limit=5)
        
        for card in cards:
            title_elem = card.find('span', itemprop='headline')
            if title_elem:
                title = title_elem.text.strip()
                # Dummy scores for now, simulating velocity calculation based on time/shares if available
                velocity = 80
                engagement = 75
                results.append({
                    "topic": title,
                    "source": "inshorts",
                    "velocity_score": velocity,
                    "engagement_score": engagement,
                    "total_score": (velocity * 0.6) + (engagement * 0.4),
                    "url": ""
                })
        return results

    def _fetch_google_trends(self) -> list:
        results = []
        pytrend = TrendReq(hl='en-IN', tz=330, timeout=(10,25))
        df = pytrend.trending_searches(pn='india')
        
        if not df.empty:
            for idx, row in df.head(5).iterrows():
                topic = row[0]
                velocity = 90 - (idx * 5) # Rank 1 gets higher velocity
                engagement = 80
                results.append({
                    "topic": topic,
                    "source": "google_trends_in",
                    "velocity_score": velocity,
                    "engagement_score": engagement,
                    "total_score": (velocity * 0.6) + (engagement * 0.4),
                    "url": ""
                })
        return results
