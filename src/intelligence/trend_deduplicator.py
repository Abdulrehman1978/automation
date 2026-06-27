class TrendDeduplicator:
    def cluster(self, trends: list) -> list:
        # MVP: Just return the trends as clusters for now
        clusters = []
        for t in trends:
            clusters.append({
                "master_topic": t["topic"],
                "combined_score": t["score"],
                "keywords": [],
                "sources": [t["source"]]
            })
        return clusters
