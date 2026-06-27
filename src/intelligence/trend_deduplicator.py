class TrendDeduplicator:
    def cluster(self, trends: list) -> list:
        # MVP: Just return the trends as clusters for now
        clusters = []
        for t in trends:
            # Handle both reddit_plugin's 'score' and trend_plugin's 'total_score'
            score = t.get("total_score", t.get("score", 0))
            clusters.append({
                "master_topic": t["topic"],
                "sources": [t["source"]],
                "combined_score": score,
                "url": t.get("url", "")
            })
        return clusters
